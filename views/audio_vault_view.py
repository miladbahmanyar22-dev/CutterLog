# ==================================================
# FILE: views/audio_vault_view.py
# ==================================================
import os
import math
from pathlib import Path
from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QFrame, QFileDialog, 
    QApplication, QMenu, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QUrl, Signal, QMimeData, QPoint, QPointF, QRectF
from PySide6.QtGui import (
    QDrag, QDragEnterEvent, QDropEvent, QMouseEvent, 
    QAction, QPainter, QColor, QPen, QPixmap, QLinearGradient, QRadialGradient,
    QFont, QFontMetrics, QPainterPath
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from config import open_path_in_os
from core.audio_vault_manager import AudioVaultManager, get_vault_root_dir
from core.icon_provider import IconProvider
from core.persian_utils import to_persian_numbers
from core.signals import global_signals
from widgets.studio_dialog_base import StudioBaseDialog, StudioConfirmDialog


class AudioCategoryDialog(StudioBaseDialog):
    """دیالوگ ایجاد و تغییر نام پوشه‌های صوتی"""
    def __init__(self, initial_name: str = "", is_rename: bool = False, parent=None):
        super().__init__(parent=parent)
        self.is_rename = is_rename
        self.setFixedWidth(420)
        
        title = "تغییر نام پوشه صوتی" if is_rename else "ایجاد پوشه صوتی جدید"
        subtitle = "نام دسته‌بندی جدید موزیک یا افکت صوتی را وارد کنید"
        icon_name = "edit" if is_rename else "folder_add"
        
        self.build_header(title, subtitle, icon_name=icon_name, icon_color="#818CF8")
        
        self.container_layout.addWidget(QLabel("نام پوشه دسته‌بندی:"))
        
        self.input_name = QLineEdit(initial_name)
        self.input_name.setFixedHeight(36)
        self.input_name.setPlaceholderText("مثال: رقص تکی، ورود عروس و داماد، تیزر...")
        self.input_name.setStyleSheet("""
            QLineEdit {
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                padding: 0 12px;
                font-family: 'Vazirmatn';
                font-size: 12px;
                color: #F8FAFC;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #1A2438;
            }
        """)
        self.input_name.returnPressed.connect(self._submit)
        self.container_layout.addWidget(self.input_name)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        btn_submit_text = "ذخیره تغییرات" if is_rename else "ایجاد پوشه"
        self.btn_submit = QPushButton(btn_submit_text)
        self.btn_submit.setFixedHeight(36)
        self.btn_submit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_submit.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover { background-color: #4F46E5; }
        """)
        self.btn_submit.clicked.connect(self._submit)
        btn_box.addWidget(self.btn_submit, stretch=2)

        btn_cancel = QPushButton("انصراف")
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #161F30;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-size: 12px;
            }
            QPushButton:hover { color: #F8FAFC; background-color: #1E283D; }
        """)
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel, stretch=1)

        self.container_layout.addLayout(btn_box)

    def _submit(self):
        if self.input_name.text().strip():
            self.accept()

    def get_category_name(self) -> str:
        return self.input_name.text().strip()


class ModernFolderCapsule(QFrame):
    """کپسول یکپارچه، شیک و محصور با چینش کاملاً وسط‌چین متون"""
    selected = Signal(str, str)
    rename_requested = Signal(str)
    delete_requested = Signal(str)

    PALETTES = [
        ("#6366F1", "#818CF8", "#A5B4FC"),
        ("#10B981", "#34D399", "#6EE7B7"),
        ("#F59E0B", "#FBBF24", "#FDE68A"),
        ("#EC4899", "#F472B6", "#FBCFE8"),
        ("#8B5CF6", "#A78BFA", "#DDD6FE"),
        ("#06B6D4", "#22D3EE", "#A5F3FC"),
    ]

    def __init__(self, folder_data: Dict[str, Any], index: int = 0, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.folder_data = folder_data
        self.index = index
        self.is_active = is_active

        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(168, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.palette = self.PALETTES[self.index % len(self.PALETTES)]
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.icon_badge = QFrame()
        self.icon_badge.setFixedSize(28, 28)
        ib_lay = QVBoxLayout(self.icon_badge)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        ib_lay.addWidget(self.lbl_icon)
        layout.addWidget(self.icon_badge)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_name = QLabel(self.folder_data.get("name", "پوشه"))
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; background: transparent; border: none;")
        text_col.addWidget(self.lbl_name)

        cnt = self.folder_data.get("count", 0)
        self.lbl_count = QLabel(f"{to_persian_numbers(cnt)} فایل")
        self.lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_count.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; font-weight: 600; background: transparent; border: none;")
        text_col.addWidget(self.lbl_count)

        layout.addLayout(text_col, stretch=1)

        self.btn_opt = QPushButton("⋮")
        self.btn_opt.setFixedSize(18, 22)
        self.btn_opt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_opt.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #64748B;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #FFFFFF;
                background-color: rgba(255, 255, 255, 0.12);
            }
        """)
        self.btn_opt.clicked.connect(self._show_options_menu)
        layout.addWidget(self.btn_opt)

        self._apply_capsule_style()

    def _apply_capsule_style(self):
        c_main, c_light, c_dim = self.palette

        if self.is_active:
            self.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(99, 102, 241, 0.40), stop:1 rgba(22, 31, 54, 0.98));
                    border: 1.5px solid {c_light};
                    border-radius: 22px;
                }}
            """)
            self.icon_badge.setStyleSheet(f"""
                QFrame {{
                    background-color: rgba(99, 102, 241, 0.35);
                    border: 1px solid {c_light};
                    border-radius: 14px;
                }}
            """)
            self.lbl_icon.setPixmap(IconProvider.get_pixmap("folder", "#FFFFFF", size=14))
            self.lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #FFFFFF; background: transparent; border: none;")
            self.lbl_count.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 9.5px; font-weight: 700; color: {c_dim}; background: transparent; border: none;")
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #121828;
                    border: 1px solid rgba(255, 255, 255, 0.10);
                    border-radius: 22px;
                }}
                QFrame:hover {{
                    background-color: #162035;
                    border-color: {c_main}99;
                }}
            """)
            self.icon_badge.setStyleSheet("""
                QFrame {{
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 14px;
                }}
            """)
            self.lbl_icon.setPixmap(IconProvider.get_pixmap("folder", "#64748B", size=14))
            self.lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 700; color: #CBD5E1; background: transparent; border: none;")
            self.lbl_count.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; font-weight: 500; color: #64748B; background: transparent; border: none;")

    def set_active_state(self, active: bool):
        if self.is_active != active:
            self.is_active = active
            self._apply_capsule_style()

    def _show_options_menu(self):
        menu = QMenu(self)
        menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        act_ren = QAction(IconProvider.get_icon("edit", "#818CF8", size=13), "تغییر نام پوشه", self)
        act_ren.triggered.connect(lambda: self.rename_requested.emit(self.folder_data["name"]))
        menu.addAction(act_ren)

        act_del = QAction(IconProvider.get_icon("trash", "#EF4444", size=13), "حذف پوشه", self)
        act_del.triggered.connect(lambda: self.delete_requested.emit(self.folder_data["name"]))
        menu.addAction(act_del)

        btn_pos = self.btn_opt.mapToGlobal(QPoint(0, self.btn_opt.height() + 2))
        menu.exec(btn_pos)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.folder_data["path"], self.folder_data["name"])
            event.accept()
            return
        super().mousePressEvent(event)


class ModernAddFolderButton(QFrame):
    """دکمه کپسولی هم‌اندازه برای افزودن پوشه جدید"""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedSize(124, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(99, 102, 241, 0.12);
                border: 1.5px dashed rgba(99, 102, 241, 0.45);
                border-radius: 22px;
            }
            QFrame:hover {
                background-color: rgba(99, 102, 241, 0.22);
                border-color: #818CF8;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("folder_add", "#818CF8", size=14))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_lbl)

        lbl = QLabel("پوشه جدید")
        lbl.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #818CF8; background: transparent; border: none;")
        layout.addWidget(lbl)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class CenterRadialPlayBtn(QWidget):
    """دکمه مدور پخش روی پوستر با قابلیت درگ برای Seek کردن"""
    toggle_play_requested = Signal()
    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.is_playing = False
        self.progress = 0.0
        self.is_dragging = False

    def set_playing_state(self, playing: bool):
        self.is_playing = playing
        self.update()

    def set_progress(self, current_ms: int, total_ms: int):
        if not self.is_dragging:
            self.progress = min(max(current_ms / total_ms, 0.0), 1.0) if total_ms > 0 else 0.0
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            center_x, center_y = self.width() / 2, self.height() / 2
            dx, dy = event.pos().x() - center_x, event.pos().y() - center_y
            if math.hypot(dx, dy) < 18:
                self.toggle_play_requested.emit()
            else:
                self.is_dragging = True
                self._update_seek(dx, dy)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_dragging:
            dx = event.pos().x() - (self.width() / 2)
            dy = event.pos().y() - (self.height() / 2)
            self._update_seek(dx, dy)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False
            dx = event.pos().x() - (self.width() / 2)
            dy = event.pos().y() - (self.height() / 2)
            self._update_seek(dx, dy)

    def _update_seek(self, dx: float, dy: float):
        angle = math.degrees(math.atan2(dx, -dy))
        if angle < 0:
            angle += 360
        ratio = min(max(angle / 360.0, 0.0), 1.0)
        self.progress = ratio
        self.update()
        self.seek_requested.emit(ratio)

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            w, h = self.width(), self.height()
            outer_rect = QRectF(2.5, 2.5, w - 5, h - 5)
            inner_rect = QRectF(6.5, 6.5, w - 13, h - 13)

            bg_pen = QPen(QColor(255, 255, 255, 40), 2.2)
            painter.setPen(bg_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(outer_rect)

            if self.progress > 0:
                prog_pen = QPen(QColor("#818CF8"), 2.8)
                prog_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(prog_pen)
                painter.drawArc(outer_rect, 90 * 16, -int(self.progress * 360 * 16))

            painter.setPen(Qt.PenStyle.NoPen)
            center_color = QColor("#6366F1") if self.is_playing else QColor(10, 15, 26, 235)
            painter.setBrush(center_color)
            painter.drawEllipse(inner_rect)

            icon_key = "pause" if self.is_playing else "play"
            icon_pix = IconProvider.get_pixmap(icon_key, "#FFFFFF", size=15)
            ix = int((w - 15) / 2) + (1 if not self.is_playing else 0)
            iy = int((h - 15) / 2)
            painter.drawPixmap(ix, iy, icon_pix)
        finally:
            painter.end()


class PosterArtworkWidget(QFrame):
    """پوستر هنری استودیو با ارتفاع کاملاً ثابت و رندر برندینگ CutterLog"""
    def __init__(self, track_data: dict, parent=None):
        super().__init__(parent)
        self.track_data = track_data
        self.setFixedHeight(134)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.pixmap: Optional[QPixmap] = None
        self._load_cover()

    def _load_cover(self):
        cover_bytes = self.track_data.get("cover_bytes")
        if cover_bytes:
            pix = QPixmap()
            if pix.loadFromData(cover_bytes):
                self.pixmap = pix
                return

        for ext in [".png", ".jpg", ".webp", ".jpeg"]:
            p = Path("images") / f"default_music_banner{ext}"
            if p.exists():
                self.pixmap = QPixmap(str(p))
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

            w = float(self.width())
            h = float(self.height())

            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, w, h), 8, 8)
            painter.setClipPath(path)

            if self.pixmap and not self.pixmap.isNull():
                scaled = self.pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                sx = int((scaled.width() - self.width()) / 2)
                sy = int((scaled.height() - self.height()) / 2)
                painter.drawPixmap(0, 0, scaled, sx, sy, int(w), int(h))
                painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
            else:
                grad = QLinearGradient(0, 0, w, h)
                grad.setColorAt(0.0, QColor("#090E1A"))
                grad.setColorAt(0.5, QColor("#121A2E"))
                grad.setColorAt(1.0, QColor("#070B14"))
                painter.fillRect(self.rect(), grad)

                radial = QRadialGradient(QPointF(w * 0.5, h * 0.5), w * 0.55)
                radial.setColorAt(0.0, QColor(99, 102, 241, 40))
                radial.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.fillRect(self.rect(), radial)

                watermark = IconProvider.get_pixmap("clp_brand_mark", "rgba(129, 140, 248, 0.08)", size=56)
                painter.drawPixmap(int((w - 56) / 2), int((h - 56) / 2) - 10, watermark)

                font_brand = QFont("Segoe UI", 8.5, QFont.Weight.Black)
                painter.setFont(font_brand)
                painter.setPen(QColor(165, 180, 252, 90))
                brand_rect = QRectF(0, h - 26, w, 18)
                painter.drawText(brand_rect, Qt.AlignmentFlag.AlignCenter, "C U T T E R L O G")
        finally:
            painter.end()


class VerticalMusicCard(QFrame):
    """کارت موزیک با ابعاد کاملاً قفل‌شده و یک‌اندازه در کل گرید"""
    play_action_triggered = Signal(str, str)
    seek_action_triggered = Signal(float)

    def __init__(self, track_data: dict, parent=None):
        super().__init__(parent)
        self.track_data = track_data
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.setFixedHeight(210)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        self.poster = PosterArtworkWidget(self.track_data, self)
        poster_lay = QVBoxLayout(self.poster)
        poster_lay.setContentsMargins(6, 6, 6, 6)

        top_row = QHBoxLayout()
        top_row.addStretch()
        lbl_badge = QLabel(self.track_data["ext"])
        lbl_badge.setStyleSheet("""
            background-color: rgba(9, 14, 24, 0.88);
            color: #818CF8;
            font-family: 'Segoe UI', sans-serif;
            font-size: 8.5px;
            font-weight: 800;
            padding: 2px 6px;
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.14);
        """)
        top_row.addWidget(lbl_badge)
        poster_lay.addLayout(top_row)

        poster_lay.addStretch()

        center_row = QHBoxLayout()
        center_row.addStretch()
        self.btn_play = CenterRadialPlayBtn(self.poster)
        self.btn_play.toggle_play_requested.connect(lambda: self.play_action_triggered.emit(self.track_data["file_path"], self.track_data["name"]))
        self.btn_play.seek_requested.connect(self.seek_action_triggered.emit)
        center_row.addWidget(self.btn_play)
        center_row.addStretch()
        poster_lay.addLayout(center_row)

        poster_lay.addStretch()
        root_layout.addWidget(self.poster)

        raw_name = self.track_data["name"]
        if " - " in raw_name:
            parts = raw_name.split(" - ", 1)
            title_text = parts[1].strip()
            artist_text = parts[0].strip()
        else:
            title_text = raw_name
            artist_text = ""

        self.lbl_title = QLabel(title_text)
        self.lbl_title.setFixedHeight(20)
        self.lbl_title.setToolTip(raw_name)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_title.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11px;
                font-weight: 800;
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
        """)
        root_layout.addWidget(self.lbl_title)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(4)

        self.lbl_artist = QLabel(artist_text if artist_text else "بدون هنرمند")
        self.lbl_artist.setFixedHeight(18)
        self.lbl_artist.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_artist.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9.5px; color: #64748B; background: transparent; border: none;")
        meta_row.addWidget(self.lbl_artist, stretch=1)

        lbl_size = QLabel(to_persian_numbers(self.track_data.get("size_str", "")))
        lbl_size.setFixedHeight(18)
        lbl_size.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl_size.setStyleSheet("font-family: 'Vazirmatn'; font-size: 9px; color: #818CF8; font-weight: bold; background: transparent; border: none;")
        meta_row.addWidget(lbl_size)

        root_layout.addLayout(meta_row)
        self.set_active_state(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        fm_title = QFontMetrics(self.lbl_title.font())
        raw_name = self.track_data["name"]
        clean_title = raw_name.split(" - ", 1)[1].strip() if " - " in raw_name else raw_name
        elided = fm_title.elidedText(clean_title, Qt.TextElideMode.ElideLeft, max(10, self.lbl_title.width() - 4))
        self.lbl_title.setText(elided)

        if hasattr(self, "lbl_artist"):
            fm_art = QFontMetrics(self.lbl_artist.font())
            art_raw = self.lbl_artist.toolTip() or self.lbl_artist.text()
            elided_art = fm_art.elidedText(art_raw, Qt.TextElideMode.ElideLeft, max(10, self.lbl_artist.width() - 2))
            self.lbl_artist.setText(elided_art)

    def set_active_state(self, is_active: bool):
        if is_active:
            self.setStyleSheet("""
                QFrame {
                    background-color: #172138;
                    border: 1.5px solid #6366F1;
                    border-radius: 9px;
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #A5B4FC; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #101625;
                    border: 1px solid rgba(255, 255, 255, 0.06);
                    border-radius: 9px;
                }
                QFrame:hover {
                    background-color: #141D30;
                    border-color: rgba(99, 102, 241, 0.40);
                }
            """)
            self.lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 800; color: #F8FAFC; background: transparent; border: none;")
            try:
                self.btn_play.set_progress(0, 1)
            except RuntimeError:
                pass

    def update_playback_progress(self, current_ms: int, total_ms: int):
        try:
            self.btn_play.set_progress(current_ms, total_ms)
        except RuntimeError:
            pass

    def set_playback_state(self, is_playing: bool):
        try:
            self.btn_play.set_playing_state(is_playing)
            self.set_active_state(is_playing)
        except RuntimeError:
            pass

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, "_drag_start_pos"):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        file_path = self.track_data.get("file_path")
        if file_path and os.path.exists(file_path):
            drag = QDrag(self)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(file_path)])
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.CopyAction)


class MinimalDropZone(QFrame):
    """دراپ‌زون شیک و مینیمال برای کشیدن و رها کردن فایل‌های صوتی"""
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(38)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("music", "#818CF8", size=15))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(icon_lbl)

        lbl_t = QLabel("فایل‌های صوتی را به اینجا بکشید یا دکمه افزودن را بزنید")
        lbl_t.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #8F98A8; border: none; background: transparent;")
        layout.addWidget(lbl_t, stretch=1)

        btn_add = QPushButton("+ افزودن فایل...")
        btn_add.setFixedHeight(26)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: rgba(99, 102, 241, 0.15);
                color: #818CF8;
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 5px;
                padding: 0 10px;
                font-size: 10.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: #FFFFFF;
            }
        """)
        btn_add.clicked.connect(self._browse_files)
        layout.addWidget(btn_add)

        self._set_normal_style()

    def _set_normal_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #101625;
                border: 1px dashed rgba(255, 255, 255, 0.08);
                border-radius: 7px;
            }
            QFrame:hover {
                border-color: rgba(99, 102, 241, 0.45);
                background-color: #141C2E;
            }
        """)

    def _set_active_style(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #162432;
                border: 1.5px dashed #10B981;
                border-radius: 7px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active_style()

    def dragLeaveEvent(self, event):
        self._set_normal_style()

    def dropEvent(self, event: QDropEvent):
        self._set_normal_style()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)

    def _browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "انتخاب موزیک برای آرشیو", "",
            "Audio Files (*.mp3 *.wav *.flac *.aac *.m4a *.ogg);;All Files (*.*)"
        )
        if files:
            self.files_dropped.emit(files)


class AudioVaultView(QWidget):
    """نمای بازطراحی‌شده و چشم‌نواز آرشیو صوتی با به‌روزرسانی زنده"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.current_folder_path: Optional[str] = None
        self.current_folder_name: Optional[str] = None
        self.current_playing_file: Optional[str] = None
        self.active_card: Optional[VerticalMusicCard] = None
        self.folder_capsules: List[ModernFolderCapsule] = []
        self._current_cols = 4

        self._init_player()
        self.init_ui()
        self.refresh_categories()

    def _init_player(self):
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 14, 22, 14)
        root_layout.setSpacing(10)

        # ۱. بنر استودیویی بالای صفحه
        banner_frame = QFrame()
        banner_frame.setFixedHeight(66)
        banner_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0B101C, stop:0.55 #111A2D, stop:1 #0B101C);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 9px;
            }
            QLabel { background: transparent; border: none; font-family: 'Vazirmatn'; }
        """)
        b_lay = QHBoxLayout(banner_frame)
        b_lay.setContentsMargins(16, 0, 16, 0)
        b_lay.setSpacing(12)
        b_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_frame = QFrame()
        icon_frame.setFixedSize(36, 36)
        icon_frame.setStyleSheet("background-color: rgba(99, 102, 241, 0.16); border: 1px solid rgba(99, 102, 241, 0.32); border-radius: 7px;")
        if_lay = QVBoxLayout(icon_frame)
        if_lay.setContentsMargins(0, 0, 0, 0)
        if_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        b_icon = QLabel()
        b_icon.setPixmap(IconProvider.get_pixmap("music", "#818CF8", size=17))
        if_lay.addWidget(b_icon)
        b_lay.addWidget(icon_frame)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        info_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_b_title = QLabel("آرشیو هوشمند موسیقی و افکت‌های صوتی تدوین")
        lbl_b_title.setStyleSheet("font-size: 12.5px; font-weight: 800; color: #F8FAFC;")
        info_col.addWidget(lbl_b_title)

        lbl_b_sub = QLabel("پخش مستقیم روی پوسترها، دسته‌بندی موضوعی مراسم و قابلیت کشیدن (Drag) به تایم‌لاین پریمیر و داوینچی")
        lbl_b_sub.setStyleSheet("font-size: 10px; color: #94A3B8;")
        info_col.addWidget(lbl_b_sub)
        b_lay.addLayout(info_col, stretch=1)

        self.lbl_stat_badge = QLabel("● سیستم صوتی آماده")
        self.lbl_stat_badge.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #818CF8;
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 5px;
                padding: 4px 10px;
            }
        """)
        b_lay.addWidget(self.lbl_stat_badge)
        root_layout.addWidget(banner_frame)

        # ۲. شلف دسته‌بندی‌ها
        self.folder_box_frame = QFrame()
        self.folder_box_frame.setStyleSheet("""
            QFrame#FolderBoxFrame {
                background-color: #101625;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 10px;
            }
        """)
        self.folder_box_frame.setObjectName("FolderBoxFrame")
        folder_box_layout = QVBoxLayout(self.folder_box_frame)
        folder_box_layout.setContentsMargins(14, 10, 14, 10)
        folder_box_layout.setSpacing(8)

        shelf_top_row = QHBoxLayout()
        shelf_top_row.setSpacing(8)
        shelf_top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_f_title = QLabel("دسته‌بندی‌های موضوعی آرشیو:")
        lbl_f_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 800; color: #F8FAFC; background: transparent; border: none;")
        shelf_top_row.addWidget(lbl_f_title)

        shelf_top_row.addStretch()

        self.lbl_total_tracks = QLabel("مجموع: ۰ فایل")
        self.lbl_total_tracks.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #10B981;
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.25);
                border-radius: 5px;
                padding: 2px 8px;
            }
        """)
        shelf_top_row.addWidget(self.lbl_total_tracks)

        self.lbl_folder_count = QLabel("۰ دسته فعال")
        self.lbl_folder_count.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 10px;
                font-weight: 700;
                color: #818CF8;
                background-color: rgba(99, 102, 241, 0.12);
                border: 1px solid rgba(99, 102, 241, 0.25);
                border-radius: 5px;
                padding: 2px 8px;
            }
        """)
        shelf_top_row.addWidget(self.lbl_folder_count)

        folder_box_layout.addLayout(shelf_top_row)

        self.scroll_stories = QScrollArea()
        self.scroll_stories.setFixedHeight(54)
        self.scroll_stories.setWidgetResizable(True)
        self.scroll_stories.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_stories.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.stories_container = QWidget()
        self.stories_container.setStyleSheet("background: transparent;")
        self.stories_layout = QHBoxLayout(self.stories_container)
        self.stories_layout.setContentsMargins(0, 0, 0, 0)
        self.stories_layout.setSpacing(8)
        self.stories_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.scroll_stories.setWidget(self.stories_container)
        folder_box_layout.addWidget(self.scroll_stories)

        root_layout.addWidget(self.folder_box_frame)

        # ۳. نوار ابزار
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)
        action_bar.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.folder_badge_frame = QFrame()
        self.folder_badge_frame.setFixedHeight(38)
        self.folder_badge_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #121828, stop:1 #172138);
                border: 1.5px solid rgba(99, 102, 241, 0.40);
                border-radius: 8px;
            }
        """)
        fbf_lay = QHBoxLayout(self.folder_badge_frame)
        fbf_lay.setContentsMargins(12, 0, 14, 0)
        fbf_lay.setSpacing(8)
        fbf_lay.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        lbl_f_icon = QLabel()
        lbl_f_icon.setPixmap(IconProvider.get_pixmap("folder", "#818CF8", size=15))
        lbl_f_icon.setStyleSheet("background: transparent; border: none;")
        fbf_lay.addWidget(lbl_f_icon)

        self.lbl_folder_display = QLabel("پوشه: انتخاب نشده")
        self.lbl_folder_display.setStyleSheet("""
            QLabel {
                font-family: 'Vazirmatn';
                font-size: 11.5px;
                font-weight: 800;
                color: #F8FAFC;
                background: transparent;
                border: none;
            }
        """)
        fbf_lay.addWidget(self.lbl_folder_display)
        action_bar.addWidget(self.folder_badge_frame)

        self.drop_zone = MinimalDropZone(self)
        self.drop_zone.files_dropped.connect(self._handle_files_ingest)
        action_bar.addWidget(self.drop_zone, stretch=1)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 جستجو در این پوشه...")
        self.txt_search.setFixedWidth(210)
        self.txt_search.setFixedHeight(38)
        self.txt_search.setStyleSheet("""
            QLineEdit {
                font-family: 'Vazirmatn';
                background-color: #101625;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 0 10px;
                color: #F8FAFC;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #141C2E;
            }
        """)
        self.txt_search.textChanged.connect(self.refresh_tracks)
        action_bar.addWidget(self.txt_search)

        self.btn_open_win = QPushButton("نمایش در سیستم‌عامل ↗")
        self.btn_open_win.setFixedHeight(38)
        self.btn_open_win.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_win.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #101625;
                color: #94A3B8;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 0 12px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #141C2E;
                color: #F8FAFC;
                border-color: #818CF8;
            }
        """)
        self.btn_open_win.clicked.connect(self._open_in_windows_explorer)
        action_bar.addWidget(self.btn_open_win)

        root_layout.addLayout(action_bar)

        # ۴. گرید پوسترها
        self.scroll_tracks = QScrollArea()
        self.scroll_tracks.setWidgetResizable(True)
        self.scroll_tracks.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll_tracks.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.tracks_container = QWidget()
        self.tracks_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.tracks_container)
        self.grid_layout.setContentsMargins(0, 4, 0, 4)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_tracks.setWidget(self.tracks_container)
        root_layout.addWidget(self.scroll_tracks, stretch=1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.scroll_tracks.width()
        if w < 760:
            cols = 2
        elif w < 1080:
            cols = 3
        else:
            cols = 4

        if hasattr(self, "_current_cols") and self._current_cols == cols:
            return
        self._current_cols = cols

        for i in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(i, 0)
        for col_idx in range(cols):
            self.grid_layout.setColumnStretch(col_idx, 1)

        self.refresh_tracks()

    def refresh_categories(self, force_refresh_tracks: bool = False):
        prev_name = self.current_folder_name
        self.folder_capsules.clear()

        while self.stories_layout.count():
            item = self.stories_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        add_btn = ModernAddFolderButton(self)
        add_btn.clicked.connect(self._add_category_dialog)
        self.stories_layout.addWidget(add_btn)

        categories = AudioVaultManager.get_categories()
        target_folder = None
        total_audio_files = 0

        for idx, cat in enumerate(categories):
            count = cat.get("count", 0)
            total_audio_files += count

            is_active = (prev_name and cat["name"] == prev_name) or (not prev_name and idx == 0)
            capsule = ModernFolderCapsule(cat, index=idx, is_active=is_active, parent=self)
            capsule.selected.connect(self._on_story_folder_selected)
            capsule.rename_requested.connect(self._rename_category)
            capsule.delete_requested.connect(self._delete_category)

            self.stories_layout.addWidget(capsule)
            self.folder_capsules.append(capsule)

            if is_active:
                target_folder = cat

        self.stories_layout.addStretch(1)

        cnt = len(categories)
        self.lbl_folder_count.setText(f"{to_persian_numbers(cnt)} دسته فعال")
        self.lbl_total_tracks.setText(f"مجموع: {to_persian_numbers(total_audio_files)} فایل")

        if target_folder:
            self._on_story_folder_selected(target_folder["path"], target_folder["name"], force_reload=force_refresh_tracks)
        elif categories:
            self._on_story_folder_selected(categories[0]["path"], categories[0]["name"], force_reload=True)
        else:
            self.current_folder_path = None
            self.current_folder_name = None
            self.lbl_folder_display.setText("پوشه: انتخاب نشده")
            self.refresh_tracks()

    def _on_story_folder_selected(self, folder_path: str, folder_name: str, force_reload: bool = False):
        if not force_reload and self.current_folder_path == folder_path and self.current_folder_name == folder_name:
            return

        self.current_folder_path = folder_path
        self.current_folder_name = folder_name
        self.lbl_folder_display.setText(f"پوشه: <span style='color:#818CF8;'>{folder_name}</span>")

        for cap in self.folder_capsules:
            cap.set_active_state(cap.folder_data["name"] == folder_name)

        self.refresh_tracks()

    def refresh_tracks(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()

        while self.grid_layout.count():
            w = self.grid_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        cols = getattr(self, "_current_cols", 4)

        if not self.current_folder_path:
            lbl_empty = QLabel("هنوز پوشه‌ای ساخته نشده است. با کلیک روی «پوشه جدید» اولین دسته خود را ایجاد کنید.")
            lbl_empty.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #64748B; margin-top: 50px; border: none;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0, 1, cols)
            return

        tracks = AudioVaultManager.get_tracks_in_category(self.current_folder_path, self.txt_search.text())

        if not tracks:
            lbl_empty = QLabel(f"پوشه «{self.current_folder_name}» خالی است. فایل‌های صوتی را به این بخش بکشید و رها کنید.")
            lbl_empty.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12px; color: #64748B; margin-top: 50px; border: none;")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(lbl_empty, 0, 0, 1, cols)
            return

        for idx, trk in enumerate(tracks):
            card = VerticalMusicCard(trk, parent=self)
            card.play_action_triggered.connect(self._handle_track_toggle)
            card.seek_action_triggered.connect(self._handle_seek)
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(card, row, col)

    def _handle_track_toggle(self, file_path: str, track_name: str):
        sender_card = self.sender().parent().parent() if isinstance(self.sender(), CenterRadialPlayBtn) else self.sender()
        if not isinstance(sender_card, VerticalMusicCard):
            return

        if self.current_playing_file == file_path:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
            return

        if self.active_card:
            try:
                self.active_card.set_playback_state(False)
            except RuntimeError:
                pass

        self.active_card = sender_card
        self.current_playing_file = file_path
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()

    def _handle_seek(self, ratio: float):
        if self.player.duration() > 0:
            self.player.setPosition(int(self.player.duration() * ratio))

    def _on_playback_state_changed(self, state):
        if not self.active_card:
            return
        try:
            self.active_card.set_playback_state(state == QMediaPlayer.PlaybackState.PlayingState)
        except RuntimeError:
            pass

    def _on_player_position_changed(self, pos_ms: int):
        if not self.active_card:
            return
        try:
            self.active_card.update_playback_progress(pos_ms, self.player.duration())
        except RuntimeError:
            pass

    def _on_player_duration_changed(self, dur_ms: int):
        if not self.active_card:
            return
        try:
            self.active_card.update_playback_progress(self.player.position(), dur_ms)
        except RuntimeError:
            pass

    def _handle_files_ingest(self, file_paths: list):
        if not self.current_folder_path:
            global_signals.show_toast.emit("لطفاً ابتدا یک پوشه ایجاد یا انتخاب کنید.", "warning")
            return
        
        copied_cnt = AudioVaultManager.ingest_files_to_category(self.current_folder_path, file_paths)
        if copied_cnt > 0:
            global_signals.show_toast.emit(f"{to_persian_numbers(copied_cnt)} فایل با موفقیت اضافه شد.", "success")
            # بازخوانی فوری کپسول‌ها و گرید ترک‌ها بدون نیاز به ری‌استارت
            self.refresh_categories(force_refresh_tracks=True)
        else:
            global_signals.show_toast.emit("فایل صوتی معتبری برای افزودن یافت نشد.", "warning")

    def _add_category_dialog(self):
        diag = AudioCategoryDialog(initial_name="", is_rename=False, parent=self.window())
        if diag.exec():
            name = diag.get_category_name()
            if name and AudioVaultManager.create_category(name):
                global_signals.show_toast.emit("پوشه جدید با موفقیت ساخته شد.", "success")
                self.current_folder_name = name
                self.refresh_categories(force_refresh_tracks=True)
            else:
                global_signals.show_toast.emit("خطا در ایجاد پوشه یا نام تکراری است.", "error")

    def _rename_category(self, old_name: str):
        diag = AudioCategoryDialog(initial_name=old_name, is_rename=True, parent=self.window())
        if diag.exec():
            new_name = diag.get_category_name()
            if new_name and new_name != old_name:
                if AudioVaultManager.rename_category(old_name, new_name):
                    global_signals.show_toast.emit("نام پوشه با موفقیت تغییر کرد.", "success")
                    self.current_folder_name = new_name
                    self.refresh_categories(force_refresh_tracks=True)
                else:
                    global_signals.show_toast.emit("خطا در تغییر نام یا پوشه هم‌نام موجود است.", "error")

    def _delete_category(self, folder_name: str):
        if StudioConfirmDialog.ask(
            self.window(),
            title="تأیید حذف پوشه",
            message=f"آیا از حذف کامل پوشه صوتی «{folder_name}» اطمینان دارید؟",
            details="در صورت فعال بودن حالت کپی، تمامی فایل‌های فیزیکی این پوشه نیز پاک خواهند شد.",
            confirm_text="حذف پوشه",
            is_danger=True,
            icon_name="trash"
        ):
            if AudioVaultManager.delete_category(folder_name):
                global_signals.show_toast.emit("پوشه مورد نظر حذف شد.", "success")
                self.current_folder_name = None
                self.refresh_categories(force_refresh_tracks=True)
            else:
                global_signals.show_toast.emit("خطا در حذف پوشه.", "error")

    def _open_in_windows_explorer(self):
        target = self.current_folder_path if (self.current_folder_path and not self.current_folder_path.startswith("virtual://")) else str(get_vault_root_dir().resolve())
        open_path_in_os(target)

    def hideEvent(self, event):
        self.player.stop()
        if self.active_card:
            try:
                self.active_card.set_playback_state(False)
            except RuntimeError:
                pass
        super().hideEvent(event)