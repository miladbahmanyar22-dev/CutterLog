# ==================================================
# FILE: core/copilot_engine.py
# ==================================================
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload, selectinload

from database.db_manager import db
from database.models import (
    Project, Client, Transaction, ProjectRevision,
    StageEnum, WorkflowStatusEnum
)
from time_tracking.models import WorkSession
from core.finance_controller import FinanceController
from core.project_controller import ProjectController
from core.settings_manager import SettingsManager
from core.persian_utils import format_toman, to_persian_numbers, gregorian_to_jalali, format_studio_title


class CopilotEngine:
    """
    موتور محاسباتی و هوش تحلیلی CutterLog Copilot
    تحلیل راندمان، سنجش اعتبار استودیوها، رادار ریسک و پیشنهاد اولویت‌بندی
    """

    # =========================================================================
    # ۱. تحلیل راندمان، تمرکز و ساعات طلایی کار (Productivity & Focus Analytics)
    # =========================================================================
    @staticmethod
    def get_productivity_insights(days_back: int = 30) -> Dict[str, Any]:
        """
        محاسبه ساعات طلایی تمرکز، شاخص تمرکز مفید و میانگین سرعت کار
        """
        since_date = datetime.utcnow() - timedelta(days=days_back)

        with db.get_session() as session:
            stmt = select(WorkSession).where(WorkSession.start_time >= since_date)
            sessions = session.scalars(stmt).all()

        if not sessions:
            return {
                "has_data": False,
                "golden_hours_label": "داده کافی نیست",
                "focus_ratio_pct": 0,
                "total_hours_analyzed": 0,
                "efficiency_advice": "با ثبت جلسات تدوین، تحلیل عادات کاری و ساعات طلایی تمرکز شما فعال خواهد شد.",
                "hourly_breakdown": {}
            }

        hourly_active_sec = [0] * 24
        total_active_sec = 0
        total_idle_sec = 0
        total_paused_sec = 0

        for s in sessions:
            act = s.active_duration or 0
            idl = s.idle_duration or 0
            pau = s.paused_duration or 0

            total_active_sec += act
            total_idle_sec += idl
            total_paused_sec += pau

            if s.start_time:
                h = s.start_time.hour
                hourly_active_sec[h] += act

        max_3h_work = 0
        peak_start_h = 16
        for h in range(22):
            w_sum = hourly_active_sec[h] + hourly_active_sec[h + 1] + hourly_active_sec[h + 2]
            if w_sum > max_3h_work:
                max_3h_work = w_sum
                peak_start_h = h

        peak_end_h = (peak_start_h + 3) % 24
        golden_hours_label = f"ساعت {peak_start_h:02d}:00 الی {peak_end_h:02d}:00"

        total_time = total_active_sec + total_idle_sec + total_paused_sec
        focus_pct = int((total_active_sec / total_time) * 100) if total_time > 0 else 85

        if focus_pct >= 80:
            advice = f"بیشترین راندمان کاری شما در بازه {golden_hours_label} ثبت شده است. تمرکز شما روی تایم‌لاین عالی و بالای ۸۰٪ است."
        elif focus_pct >= 60:
            advice = f"ساعات طلایی شما {golden_hours_label} است؛ پیشنهاد می‌شود کات‌های سنگین و اصلاح رنگ را در این ساعات متمرکز کنید."
        else:
            advice = "مدت زمان توقف و حواس‌پرتی در حین جلسات بالاست. پیشنهاد می‌شود از تایمرهای تمرکز پومودورو استفاده کنید."

        return {
            "has_data": True,
            "golden_hours_label": golden_hours_label,
            "focus_ratio_pct": focus_pct,
            "total_active_hours": round(total_active_sec / 3600, 1),
            "efficiency_advice": advice,
            "sessions_count": len(sessions)
        }

    # =========================================================================
    # ۲. ارزیابی خوش‌حسابی و اعتبار استودیوها (Studio Health & Credit Score)
    # =========================================================================
    @staticmethod
    def get_studio_credit_scores() -> List[Dict[str, Any]]:
        studio_insights = []

        with db.get_session() as session:
            clients = session.scalars(
                select(Client).options(
                    selectinload(Client.projects).selectinload(Project.transactions)
                )
            ).all()

        for c in clients:
            summary = FinanceController.get_studio_debt_summary(c.id)
            total_projects = summary.get("all_projects_count", 0)
            if total_projects == 0:
                continue

            total_fee = summary.get("total_fee", 0)
            total_paid = summary.get("total_paid", 0)
            remaining = summary.get("total_remaining", 0)
            unsettled_count = len(summary.get("unsettled_projects", []))

            score = 100

            if total_projects > 0:
                unsettled_ratio = unsettled_count / total_projects
                score -= int(unsettled_ratio * 40)

            if total_fee > 0:
                debt_ratio = remaining / total_fee
                score -= int(debt_ratio * 35)

            score = max(10, min(100, score))

            if score >= 85:
                tag = "خوش‌حساب و مطمئن"
                tag_color = "#10B981"
                action_tip = "در اولویت تحویل قرار دارد؛ تسویه حساب‌ها منظم و مطمئن است."
                grade = "A"
            elif score >= 60:
                tag = "متوسط (نیازمند پیگیری)"
                tag_color = "#F59E0B"
                action_tip = f"دارای {to_persian_numbers(unsettled_count)} پروژه معوق؛ قبل از تحویل کار جدید، مانده‌های قبلی را پیگیری کنید."
                grade = "B"
            else:
                tag = "بدحساب / پرخطر"
                tag_color = "#EF4444"
                action_tip = f"هشدار: مانده حساب بالا ({format_toman(remaining)})؛ از تحویل خروجی نهایی بدون تسویه کامل خودداری شود."
                grade = "C"

            raw_studio_title = c.company or c.full_name
            studio_insights.append({
                "client_id": c.id,
                "studio_name": format_studio_title(raw_studio_title),
                "credit_score": score,
                "grade": grade,
                "tag": tag,
                "tag_color": tag_color,
                "total_fee": total_fee,
                "total_paid": total_paid,
                "remaining": remaining,
                "unsettled_projects_count": unsettled_count,
                "action_tip": action_tip
            })

        studio_insights.sort(key=lambda x: x["credit_score"])
        return studio_insights

    # =========================================================================
    # ۳. رادار ریسک و تحلیل گلوگاه‌های پایپ‌لاین (Pipeline Radar & Bottlenecks)
    # =========================================================================
    @staticmethod
    def get_pipeline_radar() -> Dict[str, Any]:
        urgent_deadlines = []
        pending_review_alerts = []
        heavy_revisions = []

        now = datetime.utcnow()
        settings = SettingsManager.load_settings()
        limit_days = settings.get("auto_archive_delivered_days", 7)

        active_projects = ProjectController.get_active_projects()

        for p in active_projects:
            if p.deadline:
                days_left = (p.deadline.date() - now.date()).days
                c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
                if days_left <= 2 and pct < 100:
                    urgent_deadlines.append({
                        "id": p.id,
                        "title": p.couple_names or p.title,
                        "days_left": days_left,
                        "progress_pct": pct,
                        "remaining_clips": t_cnt - c_cnt,
                        "warning": f"تنها {to_persian_numbers(max(0, days_left))} روز تا موعد تحویل باقی است و {to_persian_numbers(t_cnt - c_cnt)} کلیپ هنوز تدوین نشده است!"
                    })

            if p.workflow_status == WorkflowStatusEnum.UNDER_REVIEW and p.delivered_at and limit_days > 0:
                elapsed = (now - p.delivered_at).days
                days_to_archive = limit_days - elapsed
                if 0 <= days_to_archive <= 3:
                    pending_review_alerts.append({
                        "id": p.id,
                        "title": p.couple_names or p.title,
                        "days_to_archive": days_to_archive,
                        "delivered_date": gregorian_to_jalali(p.delivered_at),
                        "notice": f"تحویل‌شده به آتلیه؛ در صورت عدم ارسال اصلاحیه، تا {to_persian_numbers(days_to_archive)} روز دیگر به صورت خودکار آرشیو می‌شود."
                    })

            if p.revisions and len(p.revisions) >= 2:
                active_rev = ProjectController.get_active_revision(p)
                if active_rev:
                    heavy_revisions.append({
                        "id": p.id,
                        "title": p.couple_names or p.title,
                        "revision_round": len(p.revisions),
                        "extra_fee": sum(r.extra_fee for r in p.revisions),
                        "notice": f"این پروژه در دور {to_persian_numbers(len(p.revisions))} اصلاحیه قرار دارد؛ هزینه مازاد این دوره‌ها را بررسی کنید."
                    })

        return {
            "urgent_deadlines": urgent_deadlines,
            "pending_review_alerts": pending_review_alerts,
            "heavy_revisions": heavy_revisions,
            "total_risks_count": len(urgent_deadlines) + len(pending_review_alerts) + len(heavy_revisions)
        }

    # =========================================================================
    # ۴. پیشنهاد اولویت‌بندی هوشمند میز کار (Smart Project Next Action)
    # =========================================================================
    @staticmethod
    def recommend_next_project() -> Optional[Dict[str, Any]]:
        active_projects = ProjectController.get_active_projects()
        if not active_projects:
            return None

        candidates = []
        now = datetime.utcnow()

        for p in active_projects:
            active_rev = ProjectController.get_active_revision(p)
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)

            if pct == 100 and not active_rev:
                continue

            priority_score = 0
            reasons = []

            if active_rev:
                priority_score += 50
                reasons.append("اصلاحیه فعال در انتظار تدوین")

            if p.deadline:
                days_left = (p.deadline.date() - now.date()).days
                if days_left < 0:
                    priority_score += 60
                    reasons.append("ددلاین گذشته (تأخیر بحرانی)")
                elif days_left <= 2:
                    priority_score += 40
                    reasons.append("ددلاین بسیار نزدیک (کمتر از ۴۸ ساعت)")
                elif days_left <= 5:
                    priority_score += 20
                    reasons.append("سررسید در هفته جاری")

            if 60 <= pct < 100:
                priority_score += 15
                reasons.append("پیشرفت بالای ۶۰٪ (آماده بستن پرونده)")

            candidates.append({
                "project": p,
                "score": priority_score,
                "reason": " • ".join(reasons) or "پروژه در جریان عادی پایپ‌لاین",
                "progress_pct": pct,
                "clips_left": t_cnt - c_cnt if not active_rev else 0
            })

        if not candidates:
            return None

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top = candidates[0]
        p = top["project"]

        raw_studio = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "")
        studio_display = format_studio_title(raw_studio) if raw_studio else "بدون استودیو"

        return {
            "project_id": p.id,
            "title": p.couple_names or p.title,
            "studio_name": studio_display,
            "progress_pct": top["progress_pct"],
            "recommendation_reason": top["reason"],
            "deadline_str": gregorian_to_jalali(p.deadline) if p.deadline else "تعیین نشده"
        }

    # =========================================================================
    # ۵. بریفینگ مدیریتی روزانه (Daily Copilot Executive Summary)
    # =========================================================================
    @staticmethod
    def generate_daily_briefing() -> Dict[str, Any]:
        prod = CopilotEngine.get_productivity_insights(days_back=14)
        radar = CopilotEngine.get_pipeline_radar()
        rec_proj = CopilotEngine.recommend_next_project()
        fin_data = FinanceController.get_financial_dashboard_data(date_range_key="all")

        cards = fin_data.get("summary_cards", {})
        total_remaining = cards.get("total_remaining", 0)

        bullet_points = []

        bullet_points.append({
            "type": "focus",
            "icon": "⚡",
            "text": prod.get("efficiency_advice")
        })

        if rec_proj:
            bullet_points.append({
                "type": "priority",
                "icon": "🎯",
                "text": f"پیشنهاد اولویت اول: تدوین «{rec_proj['title']}» ({rec_proj['recommendation_reason']})."
            })

        if radar["urgent_deadlines"]:
            first_risk = radar["urgent_deadlines"][0]
            bullet_points.append({
                "type": "warning",
                "icon": "⚠️",
                "text": f"ددلاین فوری: {first_risk['title']} ({first_risk['warning']})."
            })
        elif radar["pending_review_alerts"]:
            first_alert = radar["pending_review_alerts"][0]
            bullet_points.append({
                "type": "review",
                "icon": "⏳",
                "text": f"یادآوری بازبینی: {first_alert['title']} ({first_alert['notice']})."
            })

        if total_remaining > 0:
            bullet_points.append({
                "type": "finance",
                "icon": "💰",
                "text": f"کل مطالبات وصول‌نشده از استودیوها: {format_toman(total_remaining)}."
            })
        else:
            bullet_points.append({
                "type": "finance",
                "icon": "✓",
                "text": "حساب تمامی پروژه‌های تحویل‌شده کاملاً تسویه است."
            })

        return {
            "generated_at": datetime.now(),
            "bullet_points": bullet_points,
            "recommended_project": rec_proj,
            "focus_pct": prod.get("focus_ratio_pct", 85),
            "total_receivables": total_remaining,
            "active_risks_count": radar.get("total_risks_count", 0)
        }