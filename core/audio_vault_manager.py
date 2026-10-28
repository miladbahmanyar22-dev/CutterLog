# ==================================================
# FILE: core/audio_vault_manager.py
# ==================================================
import os
import json
import stat
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import APP_DATA_DIR
from core.settings_manager import SettingsManager

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, APIC
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    HAS_MUTAGEN = True
except ImportError:
    HAS_MUTAGEN = False

SUPPORTED_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".wma", ".aiff"}
VIRTUAL_INDEX_FILE = APP_DATA_DIR / "music_vault_refs.json"


def get_vault_root_dir() -> Path:
    settings = SettingsManager.load_settings()
    custom_path = settings.get("music_vault_path")
    
    if custom_path and os.path.exists(custom_path):
        root = Path(custom_path)
    else:
        docs = Path.home() / "Documents" / "CutterLog_Music_Vault"
        docs.mkdir(parents=True, exist_ok=True)
        root = docs
        
    return root


def is_copy_mode_enabled() -> bool:
    settings = SettingsManager.load_settings()
    return settings.get("copy_audio_to_vault", True)


def _load_virtual_index() -> Dict[str, List[str]]:
    """خواندن لیست دسته‌بندی‌های مجازی و آدرس فایل‌های متصل به آن"""
    if not VIRTUAL_INDEX_FILE.exists():
        return {}
    try:
        with open(VIRTUAL_INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_virtual_index(data: Dict[str, List[str]]) -> bool:
    try:
        with open(VIRTUAL_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception:
        return False


def _remove_readonly(func, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def extract_audio_cover(file_path: str) -> Optional[bytes]:
    """استخراج امن و استاندارد تصویر کاور تعبیه‌شده در فایل صوتی بدون ایجاد خطای کنسول"""
    if not HAS_MUTAGEN or not file_path or not os.path.exists(file_path):
        return None

    try:
        ext = Path(file_path).suffix.lower()

        if ext == ".mp3":
            audio = MP3(file_path, ID3=ID3)
            if audio.tags:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        return bytes(tag.data)

        elif ext == ".flac":
            audio = FLAC(file_path)
            if audio.pictures:
                return bytes(audio.pictures[0].data)

        elif ext in {".m4a", ".mp4", ".aac"}:
            audio = MP4(file_path)
            covs = audio.tags.get("covr") if audio.tags else None
            if covs:
                return bytes(covs[0])

    except Exception:
        pass

    return None


class AudioVaultManager:
    @staticmethod
    def get_categories() -> List[Dict[str, Any]]:
        categories = []
        copy_mode = is_copy_mode_enabled()

        if copy_mode:
            root = get_vault_root_dir()
            try:
                if root.exists():
                    for entry in sorted(root.iterdir()):
                        if entry.is_dir() and not entry.name.startswith("."):
                            count = sum(1 for f in entry.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_AUDIO_EXTS)
                            categories.append({
                                "name": entry.name,
                                "path": str(entry.resolve()),
                                "count": count,
                                "is_virtual": False
                            })
            except Exception as e:
                print(f"Error scanning physical categories: {e}")
        else:
            v_index = _load_virtual_index()
            for cat_name, file_list in sorted(v_index.items()):
                valid_files = [fp for fp in file_list if os.path.exists(fp) and Path(fp).suffix.lower() in SUPPORTED_AUDIO_EXTS]
                categories.append({
                    "name": cat_name,
                    "path": f"virtual://{cat_name}",
                    "count": len(valid_files),
                    "is_virtual": True
                })
        return categories

    @staticmethod
    def create_category(name: str) -> bool:
        clean_name = "".join(c for c in name if c not in r'\/:*?"<>|').strip()
        if not clean_name:
            return False

        if is_copy_mode_enabled():
            root = get_vault_root_dir()
            target = root / clean_name
            if target.exists():
                return False
            try:
                target.mkdir(parents=True, exist_ok=True)
                return True
            except Exception:
                return False
        else:
            v_index = _load_virtual_index()
            if clean_name in v_index:
                return False
            v_index[clean_name] = []
            return _save_virtual_index(v_index)

    @staticmethod
    def rename_category(old_name: str, new_name: str) -> bool:
        clean_new = "".join(c for c in new_name if c not in r'\/:*?"<>|').strip()
        if not clean_new or old_name == clean_new:
            return False

        if is_copy_mode_enabled():
            root = get_vault_root_dir()
            src = root / old_name
            dest = root / clean_new
            if not src.exists() or dest.exists():
                return False
            try:
                src.rename(dest)
                return True
            except Exception:
                return False
        else:
            v_index = _load_virtual_index()
            if old_name not in v_index or clean_new in v_index:
                return False
            v_index[clean_new] = v_index.pop(old_name)
            return _save_virtual_index(v_index)

    @staticmethod
    def delete_category(folder_name: str) -> bool:
        if is_copy_mode_enabled():
            root = get_vault_root_dir()
            target = root / folder_name
            if target.exists() and target.is_dir():
                try:
                    shutil.rmtree(str(target), onerror=_remove_readonly)
                    return not target.exists()
                except Exception:
                    return False
            return False
        else:
            v_index = _load_virtual_index()
            if folder_name in v_index:
                del v_index[folder_name]
                return _save_virtual_index(v_index)
            return False

    @staticmethod
    def get_tracks_in_category(folder_identifier: str, search_query: str = "") -> List[Dict[str, Any]]:
        tracks = []
        query = search_query.strip().lower()

        if folder_identifier.startswith("virtual://"):
            cat_name = folder_identifier.replace("virtual://", "")
            v_index = _load_virtual_index()
            file_paths = v_index.get(cat_name, [])

            for f_path_str in file_paths:
                file = Path(f_path_str)
                if file.is_file() and file.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                    if query and query not in file.name.lower():
                        continue
                    try:
                        size_bytes = file.stat().st_size
                        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.1f} MB"
                        cover_bytes = extract_audio_cover(str(file.resolve()))
                        tracks.append({
                            "name": file.stem,
                            "full_name": file.name,
                            "file_path": str(file.resolve()),
                            "ext": file.suffix.replace(".", "").upper(),
                            "size_str": size_str,
                            "cover_bytes": cover_bytes
                        })
                    except Exception:
                        continue
        else:
            path = Path(folder_identifier)
            if not path.exists() or not path.is_dir():
                return tracks

            try:
                for file in sorted(path.iterdir()):
                    if file.is_file() and file.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                        if query and query not in file.name.lower():
                            continue
                        size_bytes = file.stat().st_size
                        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.1f} MB"
                        cover_bytes = extract_audio_cover(str(file.resolve()))

                        tracks.append({
                            "name": file.stem,
                            "full_name": file.name,
                            "file_path": str(file.resolve()),
                            "ext": file.suffix.replace(".", "").upper(),
                            "size_str": size_str,
                            "cover_bytes": cover_bytes
                        })
            except Exception as e:
                print(f"Error scanning tracks: {e}")

        return tracks

    @staticmethod
    def ingest_files_to_category(target_folder_identifier: str, source_file_paths: List[str]) -> int:
        success_count = 0
        copy_mode = is_copy_mode_enabled()

        if not copy_mode or target_folder_identifier.startswith("virtual://"):
            cat_name = target_folder_identifier.replace("virtual://", "") if target_folder_identifier.startswith("virtual://") else Path(target_folder_identifier).name
            v_index = _load_virtual_index()
            if cat_name not in v_index:
                v_index[cat_name] = []

            existing_set = set(v_index[cat_name])

            for src in source_file_paths:
                src_path = Path(src)
                if src_path.is_file() and src_path.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                    full_p = str(src_path.resolve())
                    if full_p not in existing_set:
                        v_index[cat_name].append(full_p)
                        existing_set.add(full_p)
                        success_count += 1
                elif src_path.is_dir():
                    for sub_file in src_path.rglob("*"):
                        if sub_file.is_file() and sub_file.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                            full_p = str(sub_file.resolve())
                            if full_p not in existing_set:
                                v_index[cat_name].append(full_p)
                                existing_set.add(full_p)
                                success_count += 1

            _save_virtual_index(v_index)
            return success_count

        target_dir = Path(target_folder_identifier)
        if not target_dir.exists() or not target_dir.is_dir():
            return 0

        for src in source_file_paths:
            src_path = Path(src)
            if src_path.is_file() and src_path.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                dest_file = target_dir / src_path.name
                if dest_file.exists():
                    stem, ext = src_path.stem, src_path.suffix
                    counter = 1
                    while (target_dir / f"{stem}_{counter}{ext}").exists():
                        counter += 1
                    dest_file = target_dir / f"{stem}_{counter}{ext}"
                try:
                    shutil.copy2(src_path, dest_file)
                    success_count += 1
                except Exception:
                    pass
            elif src_path.is_dir():
                for sub_file in src_path.rglob("*"):
                    if sub_file.is_file() and sub_file.suffix.lower() in SUPPORTED_AUDIO_EXTS:
                        dest_file = target_dir / sub_file.name
                        if dest_file.exists():
                            stem, ext = sub_file.stem, sub_file.suffix
                            counter = 1
                            while (target_dir / f"{stem}_{counter}{ext}").exists():
                                counter += 1
                            dest_file = target_dir / f"{stem}_{counter}{ext}"
                        try:
                            shutil.copy2(sub_file, dest_file)
                            success_count += 1
                        except Exception:
                            pass

        return success_count

    @staticmethod
    def set_custom_vault_path(new_path: str) -> bool:
        if not new_path or not os.path.exists(new_path):
            return False
        settings = SettingsManager.load_settings()
        settings["music_vault_path"] = str(Path(new_path).resolve())
        SettingsManager.save_settings(settings)
        return True