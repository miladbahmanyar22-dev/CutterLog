# ==================================================
# FILE: core/copilot_engine.py
# ==================================================
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

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
    موتور محاسباتی و هوش تحلیلی استودیویی CutterLog Copilot
    تحلیل راندمان زمانی، چرخه ۲۴ ساعته، اعتبارسنجی مالی استودیوها،
    رادار گلوگاه‌های پایپ‌لاین و پیشنهاد هوشمند اولویت کاری
    """

    # =========================================================================
    # ۱. تحلیل راندمان، تمرکز و ساعات طلایی کار (Productivity & Focus Analytics)
    # =========================================================================
    @staticmethod
    def get_productivity_insights(days_back: int = 30) -> Dict[str, Any]:
        """
        محاسبه ساعات طلایی تمرکز با مدل مدور ۲۴ ساعته، تفکیک زمان در طول ساعات
        و تشخیص فعال بودن یا نبودن ساعت طلایی در زمان جاری سیستم
        """
        since_date = datetime.utcnow() - timedelta(days=days_back)

        with db.get_session() as session:
            stmt = select(WorkSession).where(
                WorkSession.start_time >= since_date,
                WorkSession.active_duration > 0
            )
            sessions = session.scalars(stmt).all()

        if len(sessions) < 2:
            return {
                "has_data": False,
                "golden_hours_label": "نیازمند ثبت جلسات بیشتر",
                "focus_ratio_pct": 0,
                "total_active_hours": 0.0,
                "is_currently_golden": False,
                "efficiency_advice": "با ثبت حداقل ۲ جلسه تدوین، تحلیل عادات کاری و ساعات طلایی تمرکز شما فعال خواهد شد.",
                "hourly_breakdown": [0] * 24
            }

        hourly_active_sec = [0.0] * 24
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

            if not s.start_time:
                continue

            # تسهیم دقیق مدت زمان در طول ساعات روز
            cur_time = s.start_time
            rem_act = float(act)
            while rem_act > 0:
                h = cur_time.hour
                sec_to_next_hour = 3600 - (cur_time.minute * 60 + cur_time.second)
                slice_sec = min(rem_act, float(sec_to_next_hour))
                hourly_active_sec[h] += slice_sec
                rem_act -= slice_sec
                cur_time = (cur_time + timedelta(seconds=slice_sec)).replace(minute=0, second=0)

        # پنجره مدور ۳ ساعته در طول ۲۴ ساعت شبانه‌روز
        max_3h_work = 0.0
        peak_start_h = 16
        for h in range(24):
            w_sum = (
                hourly_active_sec[h] +
                hourly_active_sec[(h + 1) % 24] +
                hourly_active_sec[(h + 2) % 24]
            )
            if w_sum > max_3h_work:
                max_3h_work = w_sum
                peak_start_h = h

        peak_end_h = (peak_start_h + 3) % 24
        golden_hours_label = f"ساعت {peak_start_h:02d}:00 الی {peak_end_h:02d}:00"

        # بررسی اینکه آیا ساعت جاری سیستم در بازه طلایی قرار دارد یا خیر
        now_hour = datetime.now().hour
        if peak_start_h < peak_end_h:
            is_currently_golden = (peak_start_h <= now_hour < peak_end_h)
        else:
            is_currently_golden = (now_hour >= peak_start_h or now_hour < peak_end_h)

        total_track_time = total_active_sec + total_idle_sec + total_paused_sec
        focus_pct = int((total_active_sec / total_track_time) * 100) if total_track_time > 0 else 0

        if focus_pct >= 80:
            advice = f"بیشترین راندمان کاری شما در بازه {golden_hours_label} ثبت شده است. تمرکز شما روی تایم‌لاین پایدار و بالای ۸۰٪ است."
        elif focus_pct >= 60:
            advice = f"ساعات طلایی شما {golden_hours_label} است؛ پیشنهاد می‌شود کات‌های حساس و اصلاح رنگ را در این بازه متمرکز کنید."
        else:
            advice = "مدت زمان توقف و انحراف تمرکز بالاست؛ پیشنهاد می‌شود جلسات تدوین را به بازه‌های ۳۰ دقیقه‌ای متمرکز تقسیم کنید."

        return {
            "has_data": True,
            "golden_hours_label": golden_hours_label,
            "peak_start_hour": peak_start_h,
            "peak_end_hour": peak_end_h,
            "is_currently_golden": is_currently_golden,
            "focus_ratio_pct": focus_pct,
            "total_active_hours": round(total_active_sec / 3600.0, 1),
            "efficiency_advice": advice,
            "sessions_count": len(sessions),
            "hourly_breakdown": [int(sec // 60) for sec in hourly_active_sec]
        }

    # =========================================================================
    # ۲. عملکرد و تجمیع واقعی پایپ‌لاین هفتگی (Weekly Velocity)
    # =========================================================================
    @staticmethod
    def get_weekly_performance_summary() -> Dict[str, Any]:
        """
        محاسبه کارکرد واقعی تدوین در ۷ روز گذشته و مقایسه با تارگت پیش‌فرض هفتگی
        """
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        with db.get_session() as session:
            stmt = select(func.sum(WorkSession.active_duration)).where(
                WorkSession.start_time >= seven_days_ago
            )
            weekly_active_sec = session.execute(stmt).scalar() or 0

        weekly_hours = round(weekly_active_sec / 3600.0, 1)
        target_hours = 36.0
        pct = int(min(100.0, (weekly_hours / target_hours) * 100)) if target_hours > 0 else 0

        return {
            "weekly_active_hours": weekly_hours,
            "target_hours": target_hours,
            "completion_pct": pct,
            "summary_text": f"{weekly_hours} از {target_hours} ساعت هفتگی"
        }

    # =========================================================================
    # ۳. ارزیابی خوش‌حسابی و اعتبار استودیوها (Studio Health & Aging Model)
    # =========================================================================
    @staticmethod
    def get_studio_credit_scores() -> List[Dict[str, Any]]:
        """
        محاسبه اعتبار استودیوها با مدل وزنی مانده معوق، تاریخچه پرداخت و سن بدهی
        """
        studio_insights = []
        now = datetime.utcnow()

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
            unsettled_projects = summary.get("unsettled_projects", [])
            unsettled_count = len(unsettled_projects)

            score = 100

            # ۱. کسر امتیاز بر مبنای نسبت مالی باقیمانده
            if total_fee > 0:
                debt_ratio = remaining / total_fee
                score -= int(debt_ratio * 35)

            # ۲. کسر امتیاز بر مبنای پروژه‌های تسویه‌نشده
            if total_projects > 0:
                unsettled_ratio = unsettled_count / total_projects
                score -= int(unsettled_ratio * 25)

            # ۳. سن بدهی (Aging Factor): کسر امتیاز در صورت تاخیر بیش از ۱۵ روز
            oldest_debt_days = 0
            for up in unsettled_projects:
                p_date = up.get("created_at")
                if p_date:
                    days_passed = (now - p_date).days
                    if days_passed > oldest_debt_days:
                        oldest_debt_days = days_passed

            if oldest_debt_days > 45:
                score -= 20
            elif oldest_debt_days > 20:
                score -= 10

            score = max(10, min(100, score))

            if score >= 85:
                tag = "خوش‌حساب و مطمئن"
                tag_color = "#10B981"
                action_tip = "در اولویت تحویل قرار دارد؛ تسویه حساب‌ها منظم و بدون معوقه است."
                grade = "A"
            elif score >= 60:
                tag = "متوسط (نیازمند پیگیری)"
                tag_color = "#F59E0B"
                action_tip = f"دارای {to_persian_numbers(unsettled_count)} پروژه معوق؛ قبل از تحویل کار جدید، تسویه را پیگیری کنید."
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
                "oldest_debt_days": oldest_debt_days,
                "action_tip": action_tip
            })

        studio_insights.sort(key=lambda x: x["credit_score"])
        return studio_insights

    # =========================================================================
    # ۴. رادار ریسک و تحلیل گلوگاه‌های پایپ‌لاین (Pipeline Radar & Deadlines)
    # =========================================================================
    @staticmethod
    def get_pipeline_radar() -> Dict[str, Any]:
        """
        رصد گلوگاه‌ها با تفکیک دقیق پروژه‌های گذشته از موعد (Overdue) و سررسیدهای نزدیک
        """
        urgent_deadlines = []
        pending_review_alerts = []
        heavy_revisions = []

        now = datetime.utcnow()
        settings = SettingsManager.load_settings()
        limit_days = settings.get("auto_archive_delivered_days", 7)

        active_projects = ProjectController.get_active_projects()

        for p in active_projects:
            # ۱. رصد ددلاین
            if p.deadline:
                days_left = (p.deadline.date() - now.date()).days
                c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)
                if pct < 100:
                    if days_left < 0:
                        passed_days = abs(days_left)
                        urgent_deadlines.append({
                            "id": p.id,
                            "title": p.couple_names or p.title,
                            "days_left": days_left,
                            "progress_pct": pct,
                            "remaining_clips": t_cnt - c_cnt,
                            "warning": f"{to_persian_numbers(passed_days)} روز از سررسید تحویل گذشته و {to_persian_numbers(t_cnt - c_cnt)} کلیپ باقیمانده است!"
                        })
                    elif days_left <= 2:
                        urgent_deadlines.append({
                            "id": p.id,
                            "title": p.couple_names or p.title,
                            "days_left": days_left,
                            "progress_pct": pct,
                            "remaining_clips": t_cnt - c_cnt,
                            "warning": f"تنها {to_persian_numbers(days_left)} روز تا سررسید تحویل باقی است و {to_persian_numbers(t_cnt - c_cnt)} کلیپ باقیمانده است."
                        })

            # ۲. رصد پروژه‌های منتظر بازبینی و نزدیک به مهلت آرشیو
            if p.workflow_status == WorkflowStatusEnum.UNDER_REVIEW and p.delivered_at and limit_days > 0:
                elapsed = (now - p.delivered_at).days
                days_to_archive = limit_days - elapsed
                if 0 <= days_to_archive <= 3:
                    pending_review_alerts.append({
                        "id": p.id,
                        "title": p.couple_names or p.title,
                        "days_to_archive": days_to_archive,
                        "delivered_date": gregorian_to_jalali(p.delivered_at),
                        "notice": f"تحویل‌شده به آتلیه؛ در صورت عدم ارسال اصلاحیه، تا {to_persian_numbers(max(0, days_to_archive))} روز دیگر خودکار آرشیو می‌شود."
                    })

            # ۳. رصد اصلاحیه‌های سنگین
            if p.revisions and len(p.revisions) >= 2:
                active_rev = ProjectController.get_active_revision(p)
                if active_rev:
                    heavy_revisions.append({
                        "id": p.id,
                        "title": p.couple_names or p.title,
                        "revision_round": len(p.revisions),
                        "extra_fee": sum(r.extra_fee for r in p.revisions),
                        "notice": f"این پروژه در دور {to_persian_numbers(len(p.revisions))} اصلاحیه قرار دارد؛ تسک‌های باقیمانده را نهایی کنید."
                    })

        # مرتب‌سازی ریسک‌های سررسید (بحرانی‌ترین تاخیرها در ابتدا)
        urgent_deadlines.sort(key=lambda x: x["days_left"])

        return {
            "urgent_deadlines": urgent_deadlines,
            "pending_review_alerts": pending_review_alerts,
            "heavy_revisions": heavy_revisions,
            "total_risks_count": len(urgent_deadlines) + len(pending_review_alerts) + len(heavy_revisions)
        }

    # =========================================================================
    # ۵. پیشنهاد هوشمند اولویت بعدی (Smart Weighted Action Recommender)
    # =========================================================================
    @staticmethod
    def recommend_next_project() -> Optional[Dict[str, Any]]:
        """
        الگوریتم رتبه‌بندی وزنی برای تعیین اولویت بعدی تدوینگر
        """
        active_projects = ProjectController.get_active_projects()
        if not active_projects:
            return None

        candidates = []
        now = datetime.utcnow()

        for p in active_projects:
            active_rev = ProjectController.get_active_revision(p)
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)

            # اگر کار ۱۰۰٪ شده و اصلاحیه بازی هم ندارد، نیازی به تدوین ندارد
            if pct == 100 and not active_rev:
                continue

            priority_score = 0
            reasons = []

            # اولویت بالای اصلاحیه فعال
            if active_rev:
                priority_score += 55
                reasons.append("اصلاحیه فعال در انتظار خروجی")

            # اولویت ددلاین
            if p.deadline:
                days_left = (p.deadline.date() - now.date()).days
                if days_left < 0:
                    priority_score += 70
                    reasons.append(f"تأخیر از ددلاین ({to_persian_numbers(abs(days_left))} روز)")
                elif days_left == 0:
                    priority_score += 50
                    reasons.append("موعد تحویل امروز است")
                elif days_left <= 2:
                    priority_score += 40
                    reasons.append("کمتر از ۴۸ ساعت تا موعد تحویل")
                elif days_left <= 5:
                    priority_score += 20
                    reasons.append("سررسید در هفته جاری")

            # اولویت پروژه‌های در آستانه اتمام (بستن پرونده‌های بالای ۶۵٪)
            if 65 <= pct < 100:
                priority_score += 15
                reasons.append(f"پیشرفت {to_persian_numbers(pct)}٪ (نزدیک به خروجی نهایی)")

            candidates.append({
                "project": p,
                "score": priority_score,
                "reason": " • ".join(reasons) if reasons else "ادامه راش‌های پروژه در جریان عادی پایپ‌لاین",
                "progress_pct": pct,
                "clips_left": max(0, t_cnt - c_cnt) if not active_rev else 0
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
            "deadline_str": gregorian_to_jalali(p.deadline) if p.deadline else "ثبت‌نشده"
        }

    # =========================================================================
    # ۶. تولید گزارش اجرایی روزانه (Unified Daily Briefing)
    # =========================================================================
    @staticmethod
    def generate_daily_briefing() -> Dict[str, Any]:
        """
        منبع واحد و هماهنگ داده برای ویجت پیشخوان و صفحه کوپایلوت
        """
        prod = CopilotEngine.get_productivity_insights(days_back=14)
        radar = CopilotEngine.get_pipeline_radar()
        rec_proj = CopilotEngine.recommend_next_project()
        fin_data = FinanceController.get_financial_dashboard_data(date_range_key="all")
        weekly = CopilotEngine.get_weekly_performance_summary()

        cards = fin_data.get("summary_cards", {})
        total_remaining = cards.get("total_remaining", 0)
        unsettled_count = cards.get("unsettled_count", 0)

        # متن اولویت تدوین
        if rec_proj:
            line_action = f"پیشنهاد تدوین «{rec_proj['title']}» ({rec_proj['recommendation_reason']})"
        else:
            line_action = "تمام پروژه‌های فعال تکمیل شده‌اند و پایپ‌لاین آزاد است."

        # متن وضعیت زمان‌بندی و ریسک‌ها
        if radar["urgent_deadlines"]:
            first_risk = radar["urgent_deadlines"][0]
            line_timeline = f"ددلاین فوری «{first_risk['title']}» ({first_risk['warning']})"
            timeline_color = "#EF4444" if first_risk.get("days_left", 0) < 0 else "#38BDF8"
        elif radar["pending_review_alerts"]:
            first_alert = radar["pending_review_alerts"][0]
            line_timeline = f"یادآوری بازبینی «{first_alert['title']}» ({first_alert['notice']})"
            timeline_color = "#38BDF8"
        elif radar["heavy_revisions"]:
            first_rev = radar["heavy_revisions"][0]
            line_timeline = f"اصلاحیه فعال «{first_rev['title']}» ({first_rev['notice']})"
            timeline_color = "#38BDF8"
        else:
            line_timeline = "زمان‌بندی پروژه‌ها پایدار است و هیچ سررسید بحرانی ثبت نشده است."
            timeline_color = "#38BDF8"

        # متن وضعیت مطالبات مالی
        if total_remaining > 0:
            line_finance = f"مطالبات وصول‌نشده {format_toman(total_remaining)} ({to_persian_numbers(unsettled_count)} پروژه)"
            finance_color = "#F59E0B"
        else:
            line_finance = "حساب تمامی پروژه‌های تحویل‌شده کاملاً تسویه است."
            finance_color = "#34D399"

        return {
            "generated_at": datetime.now(),
            "line_action": line_action,
            "line_timeline": line_timeline,
            "timeline_color": timeline_color,
            "line_finance": line_finance,
            "finance_color": finance_color,
            "recommended_project": rec_proj,
            "productivity": prod,
            "weekly_summary": weekly["summary_text"],
            "total_receivables": total_remaining,
            "active_risks_count": radar["total_risks_count"]
        }