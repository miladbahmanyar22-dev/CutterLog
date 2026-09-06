# ==================================================
# FILE: core/media_scanner.py
# ==================================================
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from PySide6.QtCore import Qt, QObject, Signal, QRunnable
from PySide6.QtGui import QImage, QPixmap

try:
    import cv2
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

MEDIA_EXTENSIONS = {
    "project": {".prproj", ".drp", ".aep", ".fcpxml", ".edl", ".xml"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".mxf", ".braw", ".r3d", ".crm", ".prores"},
    "audio": {".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg"},
    "image": {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tga", ".dng", ".arw", ".cr2"},
    "document": {".pdf", ".docx", ".xlsx", ".txt"}
}

THUMBNAIL_CACHE: Dict[str, QPixmap] = {}
METADATA_CACHE: Dict[str, dict] = {}


def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    total_sec = int(seconds)
    hours = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def scan_directory_fast(dir_path: str) -> Dict[str, Any]:
    path = Path(dir_path)
    if not path.exists() or not path.is_dir():
        return {
            "exists": False,
            "path": dir_path,
            "folders": [],
            "files": [],
            "total_items": 0,
            "total_size_str": "۰ B"
        }

    folders = []
    files = []
    total_size = 0

    try:
        with os.scandir(path) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        try:
                            sub_count = len(os.listdir(entry.path))
                        except Exception:
                            sub_count = 0

                        folders.append({
                            "name": entry.name,
                            "path": str(Path(entry.path).resolve()),
                            "sub_items_count": sub_count,
                            "is_dir": True
                        })
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        total_size += size
                        ext = Path(entry.name).suffix.lower()

                        cat = "other"
                        for c_name, ext_set in MEDIA_EXTENSIONS.items():
                            if ext in ext_set:
                                cat = c_name
                                break

                        f_path = str(Path(entry.path).resolve())
                        cached_meta = METADATA_CACHE.get(f_path, {})

                        files.append({
                            "name": entry.name,
                            "path": f_path,
                            "ext": ext.replace(".", "").upper(),
                            "size": size,
                            "size_str": format_file_size(size),
                            "category": cat,
                            "resolution": cached_meta.get("resolution", "—"),
                            "duration_str": cached_meta.get("duration_str", "--:--"),
                            "fps": cached_meta.get("fps", "—"),
                            "thumbnail_pixmap": THUMBNAIL_CACHE.get(f_path),
                            "is_dir": False
                        })
                except Exception:
                    continue
    except Exception:
        pass

    folders.sort(key=lambda x: x["name"].lower())
    sort_order = {"video": 0, "project": 1, "audio": 2, "image": 3, "document": 4, "other": 5}
    files.sort(key=lambda x: (sort_order.get(x["category"], 6), x["name"].lower()))

    return {
        "exists": True,
        "path": str(path.resolve()),
        "parent_path": str(path.parent.resolve()) if path.parent != path else None,
        "folders": folders,
        "files": files,
        "total_items": len(folders) + len(files),
        "total_size_str": format_file_size(total_size)
    }


class ThumbnailWorkerSignals(QObject):
    loaded = Signal(str, dict, object)


class ThumbnailWorker(QRunnable):
    def __init__(self, file_path: str, category: str, generation_id: int):
        super().__init__()
        self.file_path = file_path
        self.category = category
        self.generation_id = generation_id
        self.is_cancelled = False
        self.signals = ThumbnailWorkerSignals()
        self.setAutoDelete(True)

    def cancel(self):
        self.is_cancelled = True

    def run(self):
        if self.is_cancelled:
            return

        meta = {
            "resolution": "—",
            "duration_str": "--:--",
            "fps": "—"
        }
        pixmap = None
        path_obj = Path(self.file_path)

        if not path_obj.exists():
            return

        if self.file_path in THUMBNAIL_CACHE:
            cached_pix = THUMBNAIL_CACHE[self.file_path]
            cached_meta = METADATA_CACHE.get(self.file_path, meta)
            self.signals.loaded.emit(self.file_path, cached_meta, cached_pix)
            return

        if self.category == "image":
            try:
                img = QImage(str(path_obj.resolve()))
                if not img.isNull() and not self.is_cancelled:
                    meta["resolution"] = f"{img.width()} × {img.height()}"
                    pixmap = QPixmap.fromImage(img).scaled(
                        180, 95, 
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
                        Qt.TransformationMode.FastTransformation
                    )
            except Exception:
                pass

        elif self.category == "video" and HAS_OPENCV:
            cap = None
            try:
                cap = cv2.VideoCapture(str(path_obj.resolve()))
                if cap.isOpened() and not self.is_cancelled:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

                    if w >= 3840:
                        meta["resolution"] = f"4K ({w}×{h})"
                    elif w >= 1920:
                        meta["resolution"] = f"FHD ({w}×{h})"
                    elif w > 0:
                        meta["resolution"] = f"{w}×{h}"

                    if fps and fps > 0:
                        meta["fps"] = f"{fps:.2f} fps".rstrip('0').rstrip('.')
                        if frame_count and frame_count > 0:
                            meta["duration_str"] = format_duration(frame_count / fps)

                    ret, frame = cap.read()
                    if ret and frame is not None and not self.is_cancelled:
                        small_frame = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_NEAREST)
                        frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                        fh, fw, ch = frame_rgb.shape
                        qimg = QImage(frame_rgb.data, fw, fh, ch * fw, QImage.Format.Format_RGB888).copy()
                        pixmap = QPixmap.fromImage(qimg)
            except Exception:
                pass
            finally:
                if cap is not None:
                    try:
                        cap.release()
                    except Exception:
                        pass

        if not self.is_cancelled:
            if pixmap:
                THUMBNAIL_CACHE[self.file_path] = pixmap
            METADATA_CACHE[self.file_path] = meta
            self.signals.loaded.emit(self.file_path, meta, pixmap)