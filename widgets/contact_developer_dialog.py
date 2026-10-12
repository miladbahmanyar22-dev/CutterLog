# ==================================================
# FILE: widgets/contact_developer_dialog.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, QUrl, QSize, QRectF
from PySide6.QtGui import QDesktopServices, QPixmap, QPainter, QPainterPath, QColor, QFont, QPen

from config import get_asset_path, get_bundle_dir
from core.icon_provider import IconProvider
from widgets.studio_dialog_base import StudioBaseDialog


def get_circular_avatar_pixmap(size: int = 68) -> QPixmap:
    """برش پرتره با فوکوس دقیق بر چهره و سازگاری کامل با خروجی نصبی PyInstaller"""
    candidate_dirs = [
        get_bundle_dir(),
        get_bundle_dir() / "assets",
        get_bundle_dir() / "assets" / "images",
        Path(__file__).resolve().parent.parent,
        Path(__file__).resolve().parent.parent / "assets",
        Path(__file__).resolve().parent.parent / "assets" / "images",
        Path.cwd(),
        Path.cwd() / "assets",
    ]
    if getattr(sys, "frozen", False):
        candidate_dirs.append(Path(sys.executable).parent)
        candidate_dirs.append(Path(sys.executable).parent / "assets")
        if hasattr(sys, "_MEIPASS"):
            candidate_dirs.append(Path(sys._MEIPASS))
            candidate_dirs.append(Path(sys._MEIPASS) / "assets")

    image_names = [
        "developer.jpg", "developer.png", "developer.jpeg", "developer.webp",
        "dev.jpg", "dev.png", "avatar.jpg", "avatar.png"
    ]

    img_path = None
    for folder in candidate_dirs:
        try:
            if not folder.exists():
                continue
            for name in image_names:
                candidate = folder / name
                if candidate.exists() and candidate.is_file():
                    img_path = candidate
                    break
            if img_path:
                break
        except Exception:
            continue

    target_pixmap = QPixmap(size, size)
    target_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(target_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    inner_margin = 1.0
    draw_rect = QRectF(inner_margin, inner_margin, size - (inner_margin * 2), size - (inner_margin * 2))

    clip_path = QPainterPath()
    clip_path.addEllipse(draw_rect)
    painter.setClipPath(clip_path)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#161F30"))
    painter.drawEllipse(draw_rect)

    if img_path:
        src = QPixmap(str(img_path.resolve()))
        if not src.isNull():
            sw, sh = src.width(), src.height()
            crop_size = int(min(sw, sh) * 0.90)
            center_x = int(sw * 0.48)
            center_y = int(sh * 0.36)

            crop_x = max(0, min(sw - crop_size, center_x - crop_size // 2))
            crop_y = max(0, min(sh - crop_size, center_y - crop_size // 2))

            cropped = src.copy(crop_x, crop_y, crop_size, crop_size)
            scaled = cropped.scaled(
                int(draw_rect.width()), int(draw_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            painter.drawPixmap(int(draw_rect.x()), int(draw_rect.y()), scaled)

            painter.setClipping(False)
            painter.setPen(QPen(QColor(99, 102, 241, 90), 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(draw_rect)
            painter.end()
            return target_pixmap

    painter.setPen(QColor("#818CF8"))
    font = QFont("Segoe UI", int(size * 0.32), QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(draw_rect, Qt.AlignmentFlag.AlignCenter, "MB")
    painter.end()
    return target_pixmap


class ContactActionRow(QFrame):
    def __init__(self, title: str, handle: str, icon_name: str, color_hex: str, url_target: str, parent=None):
        super().__init__(parent)
        self.url_target = url_target
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("ContactActionRowFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap(icon_name, color_hex, size=18))
        layout.addWidget(icon_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
        lbl_handle = QLabel(handle)
        lbl_handle.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC; border: none; background: transparent;")
        info_col.addWidget(lbl_title)
        info_col.addWidget(lbl_handle)
        layout.addLayout(info_col, stretch=1)

        btn_open = QLabel("↗")
        btn_open.setStyleSheet(f"font-family: -apple-system, 'Segoe UI'; font-size: 13px; font-weight: bold; color: {color_hex}; border: none; background: transparent;")
        layout.addWidget(btn_open)

        self.setStyleSheet(f"""
            QFrame#ContactActionRowFrame {{
                background-color: #161F30;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }}
            QFrame#ContactActionRowFrame:hover {{
                background-color: #1A253A;
                border-color: {color_hex}55;
            }}
        """)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            QDesktopServices.openUrl(QUrl(self.url_target))
            return
        super().mouseReleaseEvent(event)


class ContactDeveloperDialog(StudioBaseDialog):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setFixedWidth(440)
        self.init_ui()

    def init_ui(self):
        self.build_header("ارتباط با طراح و توسعه‌دهنده", "CUTTERLOG PRO", icon_name="message", icon_color="#6366F1")

        header_card = QFrame()
        header_card.setStyleSheet("""
            background-color: #121826;
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
        """)
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(14, 14, 14, 14)
        h_layout.setSpacing(6)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(68, 68)
        avatar_lbl.setPixmap(get_circular_avatar_pixmap(size=68))
        avatar_lbl.setStyleSheet("border: none; background: transparent;")
        h_layout.addWidget(avatar_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        lbl_name = QLabel("میلاد بهمنیار")
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 15px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(lbl_name)

        lbl_role = QLabel("طراح و توسعه‌دهنده نرم‌افزار")
        lbl_role.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #818CF8; font-weight: 600; border: none; background: transparent;")
        lbl_role.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h_layout.addWidget(lbl_role)

        self.container_layout.addWidget(header_card)

        self.container_layout.addWidget(ContactActionRow("پیام‌رسان تلگرام", "@MiladBahmanyar", "telegram", "#38BDF8", "https://t.me/MiladBahmanyar"))
        self.container_layout.addWidget(ContactActionRow("صفحه اینستاگرام", "@MiladBahmanyar", "instagram", "#FB923C", "https://instagram.com/MiladBahmanyar"))
        self.container_layout.addWidget(ContactActionRow("پست الکترونیکی", "MiladBahmanyar@hotmail.com", "mail", "#10B981", "mailto:MiladBahmanyar@hotmail.com"))

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(36)
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
                padding: 0 24px;
            }
            QPushButton:hover {
                color: #F8FAFC;
                background-color: #1E283D;
            }
        """)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        self.container_layout.addLayout(btn_box)