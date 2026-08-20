# ==================================================
# FILE: widgets/copilot_insights_dialog.py
# ==================================================
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QGridLayout, QPushButton
)
from PySide6.QtCore import Qt
from widgets.studio_dialog_base import StudioBaseDialog
from core.copilot_engine import CopilotEngine
from core.persian_utils import format_toman, to_persian_numbers


class CopilotInsightsDialog(StudioBaseDialog):
    """دیالوگ تحلیلی جامع دستیار: وضعیت راندمان، خوش‌حسابی استودیوها و رادار ریسک"""
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMinimumSize(780, 620)
        self.resize(840, 680)
        self.init_ui()

    def init_ui(self):
        self.build_header(
            "مرکز هوش تحلیلی و دستیار استودیو (Copilot Insights)",
            "تحلیل عادات کاری، ارزیابی اعتبار مالی استودیوها و هشدارهای ریسک پایپ‌لاین",
            icon_name="sparkles",
            icon_color="#818CF8"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(4, 4, 4, 4)
        c_lay.setSpacing(16)

        prod = CopilotEngine.get_productivity_insights()
        scores = CopilotEngine.get_studio_credit_scores()
        radar = CopilotEngine.get_pipeline_radar()

        # ۱. بخش راندمان و زمان طلایی
        lbl_s1 = QLabel("۱. تحلیل راندمان و ساعات طلایی تمرکز")
        lbl_s1.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;")
        c_lay.addWidget(lbl_s1)

        card_prod = QFrame()
        card_prod.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px;")
        cp_lay = QVBoxLayout(card_prod)
        cp_lay.setSpacing(6)

        lbl_gold = QLabel(f"⏱️ بازه طلایی اوج بازدهی: <b style='color:#10B981;'>{prod.get('golden_hours_label')}</b>")
        lbl_gold.setStyleSheet("font-size: 12px; color: #F8FAFC;")
        cp_lay.addWidget(lbl_gold)

        lbl_foc = QLabel(f"🎯 شاخص تمرکز مفید روی تایم‌لاین: <b style='color:#38BDF8;'>{to_persian_numbers(prod.get('focus_ratio_pct', 0))}٪</b>")
        lbl_foc.setStyleSheet("font-size: 12px; color: #F8FAFC;")
        cp_lay.addWidget(lbl_foc)

        lbl_adv = QLabel(prod.get("efficiency_advice", ""))
        lbl_adv.setWordWrap(True)
        lbl_adv.setStyleSheet("font-size: 11px; color: #94A3B8; margin-top: 4px;")
        cp_lay.addWidget(lbl_adv)

        c_lay.addWidget(card_prod)

        # ۲. ارزیابی خوش‌حسابی استودیوها
        lbl_s2 = QLabel("۲. رتبه‌بندی و اعتبار مالی استودیوها (Studio Credit Score)")
        lbl_s2.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;")
        c_lay.addWidget(lbl_s2)

        if not scores:
            empty_lbl = QLabel("استودیویی با پروژه‌های تحویل‌شده برای ارزیابی یافت نشد.")
            empty_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
            c_lay.addWidget(empty_lbl)
        else:
            for s in scores:
                s_card = QFrame()
                s_card.setStyleSheet("background-color: #121826; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 10px;")
                s_lay = QVBoxLayout(s_card)
                s_lay.setSpacing(4)

                top_s = QHBoxLayout()
                lbl_name = QLabel(f"🏢 <b>{s['studio_name']}</b>")
                lbl_name.setStyleSheet("font-size: 12.5px; color: #F8FAFC;")
                top_s.addWidget(lbl_name, stretch=1)

                badge_score = QLabel(f"نمره {to_persian_numbers(s['credit_score'])}/۱۰۰ ({s['grade']}) - {s['tag']}")
                badge_score.setStyleSheet(f"background-color: {s['tag_color']}18; color: {s['tag_color']}; font-weight: bold; border-radius: 4px; padding: 2px 8px; font-size: 10.5px;")
                top_s.addWidget(badge_score)
                s_lay.addLayout(top_s)

                lbl_tip = QLabel(f"💡 توصیه دستیار: {s['action_tip']}")
                lbl_tip.setStyleSheet("font-size: 11px; color: #94A3B8;")
                s_lay.addWidget(lbl_tip)

                c_lay.addWidget(s_card)

        # ۳. رادار ریسک و ددلاین‌ها
        lbl_s3 = QLabel("۳. رادار ریسک و پروژه‌های نیازمند توجه فوری")
        lbl_s3.setStyleSheet("font-family: 'Vazirmatn'; font-size: 13px; font-weight: 800; color: #6366F1;")
        c_lay.addWidget(lbl_s3)

        if radar["total_risks_count"] == 0:
            no_risk = QLabel("هیچ ریسک، تأخیر یا بحرانی در پایپ‌لاین فعال وجود ندارد ✓")
            no_risk.setStyleSheet("color: #10B981; font-weight: bold; font-size: 11.5px;")
            c_lay.addWidget(no_risk)
        else:
            for r in radar["urgent_deadlines"]:
                r_box = QLabel(f"⚠️ {r['title']}: {r['warning']}")
                r_box.setStyleSheet("background-color: rgba(239, 68, 68, 0.12); color: #EF4444; border-radius: 6px; padding: 8px; font-size: 11.5px;")
                c_lay.addWidget(r_box)

            for a in radar["pending_review_alerts"]:
                a_box = QLabel(f"⏳ {a['title']}: {a['notice']}")
                a_box.setStyleSheet("background-color: rgba(245, 158, 11, 0.12); color: #F59E0B; border-radius: 6px; padding: 8px; font-size: 11.5px;")
                c_lay.addWidget(a_box)

        scroll.setWidget(container)
        self.container_layout.addWidget(scroll, stretch=1)

        # دکمه بستن
        btn_close = QPushButton("بستن")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("background-color: #161F30; color: #94A3B8; border-radius: 6px; font-size: 12px;")
        btn_close.clicked.connect(self.accept)
        self.container_layout.addWidget(btn_close)