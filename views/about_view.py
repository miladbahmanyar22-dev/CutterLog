# ==================================================
# FILE: views/about_view.py
# ==================================================
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QFont, QPen

from config import get_asset_path, get_bundle_dir
from core.icon_provider import IconProvider
from widgets.contact_developer_dialog import ContactDeveloperDialog


def get_circular_avatar_pixmap(size: int = 56) -> QPixmap:
    """تولید آواتار دایره‌ای با فیت دقیق چهره"""
    candidate_paths = [
        get_asset_path("developer.jpg"),
        get_asset_path("developer.png"),
        get_asset_path("assets/developer.jpg"),
        get_asset_path("assets/developer.png"),
        get_asset_path("assets/images/developer.jpg"),
        get_bundle_dir() / "developer.jpg",
        get_bundle_dir() / "assets" / "developer.jpg",
        Path("developer.jpg"),
        Path("assets/developer.jpg"),
        Path(__file__).resolve().parent.parent / "assets" / "developer.jpg",
    ]
    
    img_path = None
    for p in candidate_paths:
        try:
            if p.exists() and p.is_file():
                img_path = p
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
            painter.setPen(QPen(QColor(99, 102, 241, 80), 1.2))
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


class AboutPillBadge(QFrame):
    def __init__(self, text: str, text_color: str = "#818CF8", bg_color: str = "rgba(99, 102, 241, 0.10)", border_color: str = "rgba(99, 102, 241, 0.22)", parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(24)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            font-family: -apple-system, 'Segoe UI', 'Vazirmatn';
            font-size: 11px;
            font-weight: 600;
            color: {text_color};
            border: none;
            background: transparent;
        """)
        layout.addWidget(lbl)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
            }}
        """)


class PhilosophyCard(QFrame):
    def __init__(self, title: str, description: str, icon_name: str, accent_color: str = "#818CF8", parent=None):
        super().__init__(parent)
        self.setObjectName("PhilosophyCardFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap(icon_name, accent_color, size=16))
        top_row.addWidget(icon_lbl)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 700; color: #F8FAFC; border: none; background: transparent;")
        top_row.addWidget(lbl_title, stretch=1)
        layout.addLayout(top_row)

        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #8F909D; line-height: 1.5; border: none; background: transparent;")
        layout.addWidget(lbl_desc)

        self.setStyleSheet("""
            QFrame#PhilosophyCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QFrame#PhilosophyCardFrame:hover {
                background-color: #161F30;
                border-color: rgba(99, 102, 241, 0.35);
            }
        """)


class TimelineNodeWidget(QFrame):
    def __init__(self, year: str, title: str, description: str, is_latest: bool = False, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Minimum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        indicator_col = QVBoxLayout()
        indicator_col.setSpacing(0)
        indicator_col.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        dot = QFrame()
        dot.setFixedSize(8, 8)
        dot_color = "#10B981" if is_latest else "#818CF8"
        dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 4px; border: none;")
        indicator_col.addWidget(dot)

        line = QFrame()
        line.setFixedWidth(1)
        line.setMinimumHeight(40)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 0.07); border: none;")
        indicator_col.addWidget(line)
        layout.addLayout(indicator_col)

        content_col = QVBoxLayout()
        content_col.setSpacing(3)

        head_row = QHBoxLayout()
        head_row.setSpacing(8)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 700; color: #F8FAFC;")
        head_row.addWidget(lbl_title)

        lbl_year = QLabel(year)
        lbl_year.setStyleSheet("""
            font-family: -apple-system, 'Segoe UI', 'Vazirmatn';
            font-size: 10px;
            font-weight: 600;
            color: #818CF8;
            background-color: #161F30;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            padding: 1px 7px;
        """)
        head_row.addWidget(lbl_year)
        head_row.addStretch()
        content_col.addLayout(head_row)

        lbl_desc = QLabel(description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; line-height: 1.45;")
        content_col.addWidget(lbl_desc)

        layout.addLayout(content_col, stretch=1)
        self.setStyleSheet("background: transparent; border: none;")


class AboutView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.init_ui()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(18, 8, 18, 20)
        self.layout.setSpacing(14)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.layout.addWidget(self._build_hero_section())
        self.layout.addWidget(self._build_origin_story_section())
        self.layout.addWidget(self._build_philosophy_section())
        self.layout.addWidget(self._build_developer_section())
        self.layout.addWidget(self._build_specs_and_timeline_section())
        self.layout.addWidget(self._build_brand_signature_section())

        scroll.setWidget(container)
        root_layout.addWidget(scroll)

    def _build_hero_section(self) -> QWidget:
        hero_card = QFrame()
        hero_card.setObjectName("HeroCardFrame")
        hero_card.setStyleSheet("""
            QFrame#HeroCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(hero_card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setSpacing(14)
        top_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        logo_lbl = QLabel()
        logo_lbl.setPixmap(IconProvider.get_pixmap("clp_brand_mark", "#818CF8", size=44, stroke_width=2.0))
        top_row.addWidget(logo_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        lbl_app_name = QLabel("CUTTERLOG PRO")
        lbl_app_name.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 18px; font-weight: 900; color: #F8FAFC; letter-spacing: 0.5px; border: none; background: transparent;")
        title_col.addWidget(lbl_app_name)

        lbl_tagline = QLabel("سامانه مدیریت پایپ‌لاین، آرشیو هوشمند و حسابداری استودیوهای تدوین")
        lbl_tagline.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 600; color: #818CF8; border: none; background: transparent;")
        title_col.addWidget(lbl_tagline)

        top_row.addLayout(title_col, stretch=1)
        layout.addLayout(top_row)

        lbl_desc = QLabel("CUTTERLOG PRO نرم‌افزاری اختصاصی و تخصصی است که برای یکپارچه‌سازی فرآیندهای کاری تدوین‌گران، مدیریت بی‌نقص دوره‌های اصلاحیه، سازمان‌دهی راش‌ها و تسویه‌حساب‌های مالی با استودیوها و آتلیه‌ها طراحی شده است.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #8F909D; line-height: 1.6; border: none; background: transparent;")
        layout.addWidget(lbl_desc)

        badge_row = QHBoxLayout()
        badge_row.setSpacing(6)
        badge_row.addWidget(AboutPillBadge("نسخه 1.0.1", text_color="#A5B4FC", bg_color="rgba(99, 102, 241, 0.12)", border_color="rgba(99, 102, 241, 0.25)"))
        badge_row.addWidget(AboutPillBadge("وضعیت: در حال توسعه فعال", text_color="#FBBF24", bg_color="rgba(245, 158, 11, 0.10)", border_color="rgba(245, 158, 11, 0.22)"))
        badge_row.addWidget(AboutPillBadge("Windows", text_color="#94A3B8", bg_color="#161F30", border_color="rgba(255, 255, 255, 0.08)"))
        badge_row.addWidget(AboutPillBadge("macOS", text_color="#94A3B8", bg_color="#161F30", border_color="rgba(255, 255, 255, 0.08)"))
        badge_row.addStretch()
        layout.addLayout(badge_row)

        return hero_card

    def _build_origin_story_section(self) -> QWidget:
        card = QFrame()
        card.setObjectName("OriginCardFrame")
        card.setStyleSheet("""
            QFrame#OriginCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(IconProvider.get_pixmap("sparkles", "#818CF8", size=16))
        header_row.addWidget(icon_lbl)

        lbl_title = QLabel("چرا CUTTERLOG PRO ساخته شد؟")
        lbl_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        header_row.addWidget(lbl_title, stretch=1)
        layout.addLayout(header_row)

        story_text = (
            "ایده شکل‌گیری این نرم‌افزار از یک چالش واقعی و روزمره در کار تدوین متولد شد: سردرگمی میان پوشه‌های تو در تو، "
            "فراموش شدن وضعیت کلیپ‌ها، عدم پیگیری دقیق اصلاحیه‌های متعدد کارفرما و محاسبات پراکنده مالی.\n\n"
            "به جای اینکه تدوین‌گر بخش زیادی از انرژی ذهنی و زمان ارزشمند خود را صرف مدیریت کارهای فرعی، حساب‌وکتاب‌ها و هماهنگی‌های تکراری کند، "
            "CUTTERLOG PRO این بخش‌ها را در قالبی دقیق، خودکار و ساختاریافته خلاصه می‌کند تا نهایت تمرکز روی خلق اثر و فرآیند تدوین باقی بماند."
        )
        lbl_story = QLabel(story_text)
        lbl_story.setWordWrap(True)
        lbl_story.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; color: #8F909D; line-height: 1.6; border: none; background: transparent;")
        layout.addWidget(lbl_story)

        return card

    def _build_philosophy_section(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl_sec = QLabel("فلسفه و اصول طراحی محصول")
        lbl_sec.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: #818CF8; border: none; background: transparent;")
        layout.addWidget(lbl_sec)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        grid.addWidget(PhilosophyCard(
            title="نظم ساختاریافته",
            description="تمرکز تمام پروژه‌ها، کلیپ‌ها، اسناد تحویل و دفتر کل مالی در یک پایگاه داده پایدار و بدون اتلاف وقت.",
            icon_name="layers",
            accent_color="#818CF8"
        ), 0, 0)

        grid.addWidget(PhilosophyCard(
            title="تمرکز بر تدوین",
            description="کاهش کارهای دستی، اجرای مستقیم فایل پروژه در پریمیر یا داوینچی و حذف حواس‌پرتی‌های جانبی.",
            icon_name="target",
            accent_color="#10B981"
        ), 0, 1)

        grid.addWidget(PhilosophyCard(
            title="کنترل همه‌جانبه",
            description="دید شفاف به وضعیت لحظه‌ای پروژه‌ها، سررسید ددلاین‌ها، تسویه‌حساب‌های استودیو و تاریخچه دقیق اصلاحیه‌ها.",
            icon_name="shield_check",
            accent_color="#F59E0B"
        ), 0, 2)

        layout.addLayout(grid)
        return container

    def _build_developer_section(self) -> QWidget:
        card = QFrame()
        card.setObjectName("DevCardFrame")
        card.setStyleSheet("""
            QFrame#DevCardFrame {
                background-color: #121826;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        avatar_lbl = QLabel()
        avatar_lbl.setFixedSize(56, 56)
        avatar_lbl.setPixmap(get_circular_avatar_pixmap(size=56))
        avatar_lbl.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(avatar_lbl)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        lbl_name = QLabel("میلاد بهمنیار")
        lbl_name.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13.5px; font-weight: 800; color: #F8FAFC; border: none; background: transparent;")
        info_col.addWidget(lbl_name)

        lbl_role = QLabel("طراح و توسعه‌دهنده نرم‌افزار")
        lbl_role.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; font-weight: 600; color: #818CF8; border: none; background: transparent;")
        info_col.addWidget(lbl_role)

        lbl_bio = QLabel("طراحی‌شده بر پایه تجربه مستقیم در پروژه‌های تدوین و درک عمیق از نیازهای فنی و مالی تدوین‌گران.")
        lbl_bio.setWordWrap(True)
        lbl_bio.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #8F909D; border: none; background: transparent;")
        info_col.addWidget(lbl_bio)

        layout.addLayout(info_col, stretch=1)

        btn_contact = QPushButton("ارتباط با سازنده")
        btn_contact.setIcon(IconProvider.get_icon("message", "#FFFFFF", size=12))
        btn_contact.setIconSize(QSize(12, 12))
        btn_contact.setFixedHeight(34)
        btn_contact.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_contact.setStyleSheet("""
            QPushButton {
                font-family: 'Vazirmatn';
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 0 14px;
                font-weight: 700;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
        """)
        btn_contact.clicked.connect(self._open_contact_dialog)
        layout.addWidget(btn_contact)

        return card

    def _build_specs_and_timeline_section(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # مشخصات فنی
        specs_card = QFrame()
        specs_card.setStyleSheet("""
            background-color: #121826;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
        """)
        s_layout = QVBoxLayout(specs_card)
        s_layout.setContentsMargins(14, 12, 14, 12)
        s_layout.setSpacing(8)

        lbl_s_title = QLabel("مشخصات فنی نرم‌افزار")
        lbl_s_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: #F8FAFC; border: none;")
        s_layout.addWidget(lbl_s_title)

        specs_items = [
            ("نسخه فعلی:", "1.0.2"),
            ("وضعیت محصول:", "در حال توسعه فعال"),
            ("پلتفرم‌های هدف:", "Windows · macOS"),
            ("زبان و جهت رابط:", "فارسی (RTL)"),
            ("فریم‌ورک پایه:", "Python + PySide6"),
            ("شروع توسعه:", "۱۴۰۵")
        ]

        for label, val in specs_items:
            row = QHBoxLayout()
            lbl_k = QLabel(label)
            lbl_k.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11px; color: #64748B; border: none;")
            lbl_v = QLabel(val)
            lbl_v.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: #F8FAFC; border: none;")
            row.addWidget(lbl_k)
            row.addStretch()
            row.addWidget(lbl_v)
            s_layout.addLayout(row)

        layout.addWidget(specs_card, stretch=1)

        # تایم‌لاین
        timeline_card = QFrame()
        timeline_card.setStyleSheet("""
            background-color: #121826;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 8px;
        """)
        t_layout = QVBoxLayout(timeline_card)
        t_layout.setContentsMargins(14, 12, 14, 12)
        t_layout.setSpacing(6)

        lbl_t_title = QLabel("تایم‌لاین شکل‌گیری")
        lbl_t_title.setStyleSheet("font-family: 'Vazirmatn'; font-size: 12.5px; font-weight: 800; color: #F8FAFC; border: none;")
        t_layout.addWidget(lbl_t_title)

        t_layout.addWidget(TimelineNodeWidget(
            year="۱۴۰۵",
            title="آغاز شکل‌گیری ایده",
            description="شکل‌گیری کانسپت اولیه از نیاز واقعی به سامان‌دهی پروژه‌ها، آرشیو و حساب‌وکتاب تدوین‌گر."
        ))

        t_layout.addWidget(TimelineNodeWidget(
            year="۱۴۰۵",
            title="شروع توسعه",
            description="تبدیل ایده به نرم‌افزار دسکتاپ ماژولار برای مدیریت یکپارچه‌تر پایپ‌لاین تدوین."
        ))

        t_layout.addWidget(TimelineNodeWidget(
            year="۱۴۰۵",
            title="نسخه 1.0.1",
            description="نسخه رسمی در حال توسعه پایدار و افزایش قابلیت‌های کاربردی.",
            is_latest=True
        ))

        layout.addWidget(timeline_card, stretch=1)
        return container

    def _build_brand_signature_section(self) -> QWidget:
        container = QFrame()
        container.setStyleSheet("""
            background-color: transparent;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding-top: 6px;
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_signature = QLabel("«طراحی‌شده تا تدوین‌گر کمتر درگیر مدیریت کارهای جانبی شود و با تمام توان روی هنر تدوین تمرکز کند.»")
        lbl_signature.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_signature.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 600; color: #818CF8; border: none;")
        layout.addWidget(lbl_signature)

        lbl_copy = QLabel("© ۱۴۰۵ میلاد بهمنیار — تمامی حقوق محفوظ است")
        lbl_copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_copy.setStyleSheet("font-family: -apple-system, 'Segoe UI', 'Vazirmatn'; font-size: 10px; color: #64748B; border: none;")
        layout.addWidget(lbl_copy)

        return container

    def _open_contact_dialog(self):
        diag = ContactDeveloperDialog(self.window())
        diag.exec()