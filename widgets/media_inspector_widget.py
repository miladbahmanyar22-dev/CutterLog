# ==================================================
# FILE: widgets/media_inspector_widget.py
# ==================================================
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFileDialog, QSizePolicy, QApplication,
    QGridLayout
)
from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QPixmap, QImage,
    QPainter, QColor, QLinearGradient, QPen, QPainterPath
)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from core.icon_provider import IconProvider
from core.persian_utils import to_persian_numbers
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog


def format_file_size_bytes(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a if a > 0 else 1


def analyze_video_file(file_path: str) -> Optional[Dict[str, Any]]:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return None

    size_bytes = path.stat().st_size
    ext = path.suffix.replace(".", "").upper()

    info = {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "ext": ext,
        "size_str": format_file_size_bytes(size_bytes),
        "resolution": "نامشخص",
        "width": 1920,
        "height": 1080,
        "fps": 25.0,
        "fps_str": "25 fps",
        "duration_sec": 0.0,
        "duration_str": "--:--",
        "total_frames": 0,
        "aspect_ratio": "16:9",
        "bitrate_mbps": 0.0,
        "timeline_match_warning": None,
        "slow_mo_info": None,
        "thumbnail_pixmap": None,
    }

    if not HAS_CV2:
        return info

    cap = None
    try:
        cap = cv2.VideoCapture(str(path.resolve()))
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            info["width"] = w if w > 0 else 1920
            info["height"] = h if h > 0 else 1080
            info["total_frames"] = total_frames

            if w > 0 and h > 0:
                if w >= 3840 and h >= 2160:
                    info["resolution"] = f"4K UHD ({w} × {h})"
                elif w >= 1920 and h >= 1080:
                    info["resolution"] = f"Full HD ({w} × {h})"
                elif w >= 1280 and h >= 720:
                    info["resolution"] = f"HD ({w} × {h})"
                else:
                    info["resolution"] = f"{w} × {h}"

                gcd_val = _gcd(w, h)
                ar_w, ar_h = w // gcd_val, h // gcd_val
                if (ar_w, ar_h) in [(16, 9), (9, 16), (4, 3), (1, 1), (21, 9)]:
                    info["aspect_ratio"] = f"{ar_w}:{ar_h}"
                else:
                    info["aspect_ratio"] = f"{w/h:.2f}:1"

            if fps and fps > 0:
                info["fps"] = fps
                info["fps_str"] = f"{fps:.3f}".rstrip('0').rstrip('.') + " fps"

                rounded_fps = round(fps, 2)
                if rounded_fps in [29.97, 30.0, 59.94, 60.0]:
                    info["timeline_match_warning"] = "⚠️ فریم‌ریت NTSC (احتمال عدم تطابق با تایم‌لاین ۲۵/۵۰ فریم)"
                elif rounded_fps in [23.976, 24.0]:
                    info["timeline_match_warning"] = "🎬 فریم‌ریت سینمایی ۲۴ فریم"

                if rounded_fps >= 100:
                    speed_pct = int((25.0 / rounded_fps) * 100)
                    info["slow_mo_info"] = f"⚡ پتانسیل اسلوموشن {int(rounded_fps // 25)}X (سرعت {to_persian_numbers(speed_pct)}٪ در تایم‌لاین ۲۵ فریم)"
                elif rounded_fps >= 50:
                    speed_pct = int((25.0 / rounded_fps) * 100)
                    info["slow_mo_info"] = f"⚡ پتانسیل اسلوموشن ۲X (سرعت {to_persian_numbers(speed_pct)}٪ در تایم‌لاین ۲۵ فریم)"

                if total_frames > 0:
                    dur_sec = total_frames / fps
                    info["duration_sec"] = dur_sec
                    m = int(dur_sec // 60)
                    s = int(dur_sec % 60)
                    info["duration_str"] = f"{m:02d}:{s:02d}"

                    if dur_sec > 0:
                        mbps = (size_bytes * 8) / (dur_sec * 1_000_000)
                        info["bitrate_mbps"] = round(mbps, 1)

            ret, frame = cap.read()
            if ret and frame is not None:
                small = cv2.resize(frame, (180, 100), interpolation=cv2.INTER_AREA)
                rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
                fh, fw, ch = rgb.shape
                qimg = QImage(rgb.data, fw, fh, ch * fw, QImage.Format.Format_RGB888).copy()
                info["thumbnail_pixmap"] = QPixmap.fromImage(qimg)

    except Exception:
        pass
    finally:
        if cap:
            cap.release()

    return info


class MediaInspectorDialog(StudioBaseDialog):
    """دیالوگ نمایش مشخصات فنی و تحلیل هوشمند فوتج با ساختار تایل‌های شیشه‌ای مدرن"""
    def __init__(self, data: Dict[str, Any], parent=None):
        super().__init__(parent=parent)
        self.data = data
        self.setFixedWidth(540)
        self.init_ui()

    def _make_clean_label(self, text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background: transparent !important; border: none !important; outline: none !important; {style}")
        return lbl

    def init_ui(self):
        self.build_header(
            "تحلیل فنی فوتج (Media Inspector)",
            "بررسی مشخصات رزولوشن، فریم‌ریت و بیت‌ریت ویدیو",
            icon_name="nle_launch",
            icon_color="#38BDF8"
        )

        # ۱. هدر نام فایل و مسیر
        top_card = QFrame()
        top_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px;")
        t_lay = QHBoxLayout(top_card)
        t_lay.setContentsMargins(12, 10, 12, 10)
        t_lay.setSpacing(12)

        if self.data.get("thumbnail_pixmap"):
            thumb_lbl = QLabel()
            thumb_lbl.setFixedSize(92, 54)
            thumb_lbl.setScaledContents(True)
            thumb_lbl.setPixmap(self.data["thumbnail_pixmap"])
            thumb_lbl.setStyleSheet("border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.3); background: transparent;")
            t_lay.addWidget(thumb_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        lbl_name = self._make_clean_label(self.data.get("file_name", "فایل ویدیو"), "font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC;")
        name_col.addWidget(lbl_name)

        lbl_path = self._make_clean_label(self.data.get("file_path", ""), "font-family: 'Segoe UI'; font-size: 10px; color: #64748B;")
        lbl_path.setWordWrap(True)
        name_col.addWidget(lbl_path)
        t_lay.addLayout(name_col, stretch=1)

        self.container_layout.addWidget(top_card)

        # ۲. هشدارهای هوشمند فریم‌ریت و اسلوموشن
        if self.data.get("timeline_match_warning"):
            warn_box = QFrame()
            warn_box.setStyleSheet("background-color: rgba(245, 158, 11, 0.12); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 8px;")
            w_lay = QHBoxLayout(warn_box)
            w_lay.setContentsMargins(12, 8, 12, 8)
            lbl_w = self._make_clean_label(self.data["timeline_match_warning"], "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 600; color: #FBBF24;")
            w_lay.addWidget(lbl_w)
            self.container_layout.addWidget(warn_box)

        if self.data.get("slow_mo_info"):
            slow_box = QFrame()
            slow_box.setStyleSheet("background-color: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px;")
            s_lay = QHBoxLayout(slow_box)
            s_lay.setContentsMargins(12, 8, 12, 8)
            lbl_s = self._make_clean_label(self.data["slow_mo_info"], "font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #34D399;")
            s_lay.addWidget(lbl_s)
            self.container_layout.addWidget(slow_box)

        # ۳. کارت مشخصات فنی
        specs_card = QFrame()
        specs_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px;")
        s_grid = QVBoxLayout(specs_card)
        s_grid.setContentsMargins(16, 14, 16, 14)
        s_grid.setSpacing(9)

        items = [
            ("کیفیت و رزولوشن:", self.data.get("resolution", "—"), "#38BDF8"),
            ("فریم‌ریت دقیق (FPS):", to_persian_numbers(self.data.get("fps_str", "—")), "#818CF8"),
            ("نسبت تصویر (Aspect Ratio):", self.data.get("aspect_ratio", "—"), "#F8FAFC"),
            ("مدت زمان ویدیو:", to_persian_numbers(self.data.get("duration_str", "--:--")), "#FBBF24"),
            ("تعداد کل فریم‌ها:", to_persian_numbers(f"{self.data.get('total_frames', 0):,} فریم"), "#94A3B8"),
            ("بیت‌ریت ویدیو:", to_persian_numbers(f"{self.data.get('bitrate_mbps', 0)} Mbps") if self.data.get("bitrate_mbps") else "—", "#10B981"),
            ("فرمت و کانتینر:", self.data.get("ext", "RAW"), "#C084FC"),
            ("حجم فایل روی دیسک:", to_persian_numbers(self.data.get("size_str", "—")), "#F8FAFC"),
        ]

        for k, v, col in items:
            row = QHBoxLayout()
            lbl_k = self._make_clean_label(k, "font-family: 'Vazirmatn'; font-size: 12px; color: #8F909D;")
            lbl_v = self._make_clean_label(str(v), f"font-family: 'Segoe UI', 'Vazirmatn'; font-size: 12px; font-weight: 700; color: {col};")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            s_grid.addLayout(row)

        self.container_layout.addWidget(specs_card)

        # ۴. دکمه‌ها
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_copy = QPushButton("کپی مشخصات فوتج")
        btn_copy.setFixedHeight(38)
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 700;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        btn_copy.clicked.connect(self._copy_specs)
        btn_box.addWidget(btn_copy, stretch=2)

        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(38)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                color: #F8FAFC;
                border-color: #6366F1;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _copy_specs(self):
        text = (
            f"🎬 فایل: {self.data.get('file_name')}\n"
            f"📐 رزولوشن: {self.data.get('resolution')}\n"
            f"⏱️ فریم‌ریت: {self.data.get('fps_str')}\n"
            f"⏳ زمان: {self.data.get('duration_str')}\n"
            f"💾 حجم: {self.data.get('size_str')}\n"
            f"📊 بیت‌ریت: {self.data.get('bitrate_mbps')} Mbps"
        )
        QApplication.clipboard().setText(text)
        global_signals.show_toast.emit("مشخصات فنی فوتج در کلیپ‌بورد کپی شد.", "success")


class MediaInspectorDropZone(QFrame):
    """
    کارت مدرن، شیشه‌ای و چشم‌نواز آنالیزور فوتج در پیشخوان (Drag & Drop Studio Inspector)
    """
    file_inspected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MediaDropZoneFrame")
        self.setAcceptDrops(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._is_drag_active = False
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # ۱. آیکون کپسولی مانیتورینگ
        icon_frame = QFrame()
        icon_frame.setFixedSize(44, 44)
        icon_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.28);
                border-radius: 10px;
            }
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("nle_launch", "#818CF8", size=20))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        icon_layout.addWidget(icon_lbl)
        layout.addWidget(icon_frame)

        # ۲. متن‌های عنوان و زیرعنوان همراه با تگ‌های پسوند
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lbl_title = QLabel("آنالیزور هوشمند فوتج و راش‌ها (Media Inspector)")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        title_row.addWidget(lbl_title)

        live_tag = QLabel("⚡ تشخیص آنی")
        live_tag.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 9.5px;
                font-weight: 700;
                color: #38BDF8;
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 4px;
                padding: 1px 5px;
            }
        """)
        title_row.addWidget(live_tag)
        title_row.addStretch()
        info_col.addLayout(title_row)

        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        sub_row.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        lbl_sub = QLabel("ویدیو را به این کادر بکشید (Drag & Drop) یا برای تحلیل مشخصات کلیک کنید")
        lbl_sub.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #94A3B8; border: none; background: transparent;")
        sub_row.addWidget(lbl_sub)

        # تگ‌های فرمت پشتیبانی‌شده
        formats = ["MP4", "MOV", "ProRes", "BRAW", "MXF", "4K"]
        for fmt in formats:
            f_lbl = QLabel(fmt)
            f_lbl.setStyleSheet("""
                font-family: -apple-system, 'Segoe UI', sans-serif;
                font-size: 9px;
                font-weight: 700;
                color: #64748B;
                background-color: rgba(255, 255, 255, 0.04);
                border-radius: 3px;
                padding: 1px 4px;
                border: none;
            """)
            sub_row.addWidget(f_lbl)

        sub_row.addStretch()
        info_col.addLayout(sub_row)
        layout.addLayout(info_col, stretch=1)

        # ۳. دکمه انتخاب فایل
        btn_select = QPushButton("انتخاب فوتج...")
        btn_select.setFixedHeight(34)
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setIcon(IconProvider.get_icon("search", "#FFFFFF", size=12))
        btn_select.setIconSize(QSize(12, 12))
        btn_select.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                padding: 0 16px;
                font-size: 11.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        btn_select.clicked.connect(self._select_file_dialog)
        layout.addWidget(btn_select)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        painter.setClipPath(path)

        if self._is_drag_active:
            # حالت درگ اکتیو با پس‌زمینه زمردی و حاشیه روشن
            painter.fillRect(rect, QColor("#14232C"))
            pen = QPen(QColor("#10B981"), 1.8, Qt.PenStyle.DashLine)
        else:
            # حالت عادی استودیویی
            grad = QLinearGradient(0, 0, self.width(), self.height())
            grad.setColorAt(0.0, QColor("#121826"))
            grad.setColorAt(1.0, QColor("#0E131F"))
            painter.fillRect(rect, grad)
            pen = QPen(QColor(255, 255, 255, 14), 1.0)

        painter.setClipping(False)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0), 10, 10)
        painter.end()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._is_drag_active = True
            self.update()

    def dragLeaveEvent(self, event):
        self._is_drag_active = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self._is_drag_active = False
        self.update()
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self._process_file(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._select_file_dialog()
        super().mousePressEvent(event)

    def _select_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب فایل ویدیو جهت آنالیز فنی", "",
            "Video Files (*.mp4 *.mov *.mkv *.avi *.mxf *.braw *.r3d *.prores);;All Files (*.*)"
        )
        if file_path:
            self._process_file(file_path)

    def _process_file(self, file_path: str):
        data = analyze_video_file(file_path)
        if data:
            self.file_inspected.emit(data)
            diag = MediaInspectorDialog(data, self.window())
            diag.exec()