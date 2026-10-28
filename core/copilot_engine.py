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
    تحلیل راندمان زمانی، ماتریس اولویت وزنی چندعامله، اعتبارسنجی مالی استودیوها،
    رادار گلوگاه‌های پایپ‌لاین و اتصال به وضعیت مانیتورینگ سیستم
    """

    # =========================================================================
    # ۱. ماتریس وزنی هوشمند اولویت‌بندی پروژه‌ها (Multi-Factor Scoring Matrix)
    # =========================================================================
    @staticmethod
    def calculate_project_priority_matrix(project: Project, current_active_title: str = "") -> Dict[str, Any]:
        """
        محاسبه وزن جامع اولویت پروژه بر مبنای:
        ۱. ددلاین و حجم راش‌های باقیمانده (Deadline Burn-down Ratio)
        ۲. وضعیت اصلاحیه فعال و معطل
        ۳. فاکتور ریسک مالی و بدهی آتلیه (Studio Credit Factor)
        ۴. نرخ اتمام پرونده (Completion Closure Incentive)
        ۵. همگام‌سازی زنده با پروژه باز در پریمیر/داوینچی
        """
        now = datetime.utcnow()
        score = 0.0
        factors = []
        c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(project)
        active_rev = ProjectController.get_active_revision(project)
        status_info = ProjectController.get_status_info(project)
        status_key = status_info.get("key", "")

        # اگر پروژه تحویل شده یا کامل بدون اصلاحیه باشد، اولویت پایینی برای تدوین دارد
        if (pct >= 100 or status_key in ["under_review", "ready_for_delivery"]) and not active_rev:
            return {
                "score": 5.0,
                "reasons": ["آماده تحویل یا در انتظار بازبینی"],
                "is_urgent": False,
                "is_nle_focused": False,
                "progress_pct": pct,
                "remaining_clips": 0
            }

        # فاکتور ۱: تشخیص زنده باز بودن در NLE (Premiere / DaVinci Window Hook)
        is_nle_focused = False
        if current_active_title:
            proj_title_clean = (project.couple_names or project.title or "").strip().lower()
            if proj_title_clean and proj_title_clean in current_active_title.lower():
                score += 45.0
                is_nle_focused = True
                factors.append("پروژه جاری روی تایم‌لاین نرم‌افزار تدوین")

        # فاکتور ۲: اصلاحیه فعال
        if active_rev:
            score += 40.0
            rev_c, rev_t, rev_pct = ProjectController.calculate_revision_progress(active_rev)
            factors.append(f"اصلاحیه فعال ({rev_t - rev_c} تسک مانده)")

        # فاکتور ۳: موعد تحویل (ددلاین) و شتاب زمانی
        rem_clips = max(1, t_cnt - c_cnt) if not active_rev else 1
        is_urgent = False
        if project.deadline:
            days_left = (project.deadline.date() - now.date()).days
            if days_left < 0:
                is_urgent = True
                # جریمه تأخیر نمایی بر اساس تعداد کلیپ‌های مانده
                score += 55.0 + min(30.0, abs(days_left) * 4.0)
                factors.append(f"{to_persian_numbers(abs(days_left))} روز تأخیر از ددلاین")
            elif days_left == 0:
                is_urgent = True
                score += 45.0
                factors.append("موعد تحویل امروز است")
            elif days_left <= 2:
                is_urgent = True
                score += 35.0 + (10.0 if rem_clips > 1 else 0.0)
                factors.append(f"کمتر از ۴۸ ساعت تا تحویل ({to_persian_numbers(days_left)} روز)")
            elif days_left <= 5:
                score += 20.0
                factors.append(f"سررسید در هفته جاری ({to_persian_numbers(days_left)} روز)")
        else:
            score += 10.0

        # فاکتور ۴: ریسک مالی و خوش‌حسابی آتلیه
        if project.client_id:
            summary = FinanceController.get_studio_debt_summary(project.client_id)
            client_rem = summary.get("total_remaining", 0)
            if client_rem > 15_000_000:
                score += 15.0
                factors.append("بدهی انباشته بالای استودیو")
            elif client_rem > 5_000_000:
                score += 8.0

        # فاکتور ۵: تشویق به بستن پرونده‌های بالای ۶۵٪ (Closing Loop Incentive)
        if 65 <= pct < 100 and not active_rev:
            score += 12.0
            factors.append(f"پیشرفت {to_persian_numbers(pct)}٪ (آستانه بستن پرونده)")

        return {
            "score": round(score, 1),
            "reasons": factors if factors else ["جریان عادی کات راش‌ها"],
            "is_urgent": is_urgent,
            "is_nle_focused": is_nle_focused,
            "progress_pct": pct,
            "remaining_clips": max(0, t_cnt - c_cnt) if not active_rev else 0
        }

    # =========================================================================
    # ۲. تحلیل راندمان، تمرکز و ساعات طلایی کار (Productivity & Focus Analytics)
    # =========================================================================
    @staticmethod
    def get_productivity_insights(days_back: int = 30) -> Dict[str, Any]:
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

            cur_time = s.start_time
            rem_act = float(act)
            while rem_act > 0:
                h = cur_time.hour
                sec_to_next_hour = 3600 - (cur_time.minute * 60 + cur_time.second)
                slice_sec = min(rem_act, float(sec_to_next_hour))
                hourly_active_sec[h] += slice_sec
                rem_act -= slice_sec
                cur_time = (cur_time + timedelta(seconds=slice_sec)).replace(minute=0, second=0)

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
            advice = "مدت زمان توقف و انحراف تمرکز بالاست؛ پیشنهاد می‌شود جلسات تدوین را به بازه‌های متمرکز تقسیم کنید."

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
    # ۳. عملکرد و تجمیع واقعی پایپ‌لاین هفتگی (Weekly Velocity)
    # =========================================================================
    @staticmethod
    def get_weekly_performance_summary() -> Dict[str, Any]:
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
    # ۴. ارزیابی اعتبار استودیوها (Studio Health Model)
    # =========================================================================
    @staticmethod
    def get_studio_credit_scores() -> List[Dict[str, Any]]:
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
            if total_fee > 0:
                debt_ratio = remaining / total_fee
                score -= int(debt_ratio * 35)

            if total_projects > 0:
                unsettled_ratio = unsettled_count / total_projects
                score -= int(unsettled_ratio * 25)

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
    # ۵. رادار ریسک و گلوگاه‌های پایپ‌لاین (Radar & Deadlines)
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
            matrix = CopilotEngine.calculate_project_priority_matrix(p)
            c_cnt, t_cnt, pct = ProjectController.calculate_project_progress(p)

            if p.deadline and pct < 100:
                days_left = (p.deadline.date() - now.date()).days
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

        urgent_deadlines.sort(key=lambda x: x["days_left"])

        return {
            "urgent_deadlines": urgent_deadlines,
            "pending_review_alerts": pending_review_alerts,
            "heavy_revisions": heavy_revisions,
            "total_risks_count": len(urgent_deadlines) + len(pending_review_alerts) + len(heavy_revisions)
        }

    # =========================================================================
    # ۶. پیشنهاد هوشمند اولویت بعدی بر مبنای ماتریس وزنی
    # =========================================================================
    @staticmethod
    def recommend_next_project(current_active_title: str = "") -> Optional[Dict[str, Any]]:
        active_projects = ProjectController.get_active_projects()
        if not active_projects:
            return None

        candidates = []
        for p in active_projects:
            matrix = CopilotEngine.calculate_project_priority_matrix(p, current_active_title=current_active_title)
            if matrix["score"] <= 5.0 and matrix["progress_pct"] == 100:
                continue

            candidates.append({
                "project": p,
                "score": matrix["score"],
                "reason": " • ".join(matrix["reasons"]),
                "progress_pct": matrix["progress_pct"],
                "clips_left": matrix["remaining_clips"]
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
    # ۷. تولید گزارش اجرایی روزانه (Unified Daily Briefing)
    # =========================================================================
    @staticmethod
    def generate_daily_briefing(current_active_title: str = "") -> Dict[str, Any]:
        prod = CopilotEngine.get_productivity_insights(days_back=14)
        radar = CopilotEngine.get_pipeline_radar()
        rec_proj = CopilotEngine.recommend_next_project(current_active_title=current_active_title)
        fin_data = FinanceController.get_financial_dashboard_data(date_range_key="all")
        weekly = CopilotEngine.get_weekly_performance_summary()

        cards = fin_data.get("summary_cards", {})
        total_remaining = cards.get("total_remaining", 0)
        unsettled_count = cards.get("unsettled_count", 0)

        if rec_proj:
            line_action = f"پیشنهاد تدوین «{rec_proj['title']}» ({rec_proj['recommendation_reason']})"
        else:
            line_action = "تمام پروژه‌های فعال تکمیل شده‌اند و پایپ‌لاین آزاد است."

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