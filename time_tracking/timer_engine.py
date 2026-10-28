# ==================================================
# FILE: time_tracking/timer_engine.py
# ==================================================
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
from PySide6.QtCore import QObject, QTimer, Signal
from sqlalchemy import select, func

from database.db_manager import db
from database.models import ProjectClipItem
from time_tracking.models import WorkSession, DailyGoal, ActivityLog, SessionStatusEnum
from time_tracking.system_monitor import SystemActivityMonitorThread
from core.signals import global_signals


class TimeTrackingEngine(QObject):
    _instance = None
    retroactive_prompt_requested = Signal(int, str)

    # بازه تنفس و مهلت عدم حضور: ۵ دقیقه (۳۰۰ ثانیه)
    GRACE_PERIOD_SECONDS = 300

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TimeTrackingEngine()
        return cls._instance

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_session_id: Optional[int] = None
        self.current_project_id: Optional[int] = None
        self.current_clip_id: Optional[int] = None
        
        # شمارنده‌های نشست فعال جاری
        self.active_seconds = 0
        self.render_seconds = 0
        self.paused_seconds = 0
        self.idle_seconds = 0
        
        # شمارنده پایش عدم حضور
        self.away_accumulated_seconds = 0
        
        self.is_paused = False
        self.is_running = False
        self.auto_suspended = False

        self.last_system_metric: Dict[str, Any] = {}
        self._last_logged_state: Optional[str] = None

        # تایمر ۱ ثانیه‌ای محاسبه زمان
        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)

        # ذخیره‌سازی دوره‌ای هر ۳۰ ثانیه
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(30000)
        self.auto_save_timer.timeout.connect(self._persist_active_session)

        # تردهای مانیتورینگ سیستم
        self.monitor_thread = SystemActivityMonitorThread(check_interval_sec=3.0, parent=self)
        self.monitor_thread.metrics_updated.connect(self._on_system_metrics)
        self.monitor_thread.start()

        self._recover_crashed_sessions()

    def _recover_crashed_sessions(self):
        """بستن سشن‌هایی که به دلیل قطعی سیستم active باقی مانده‌اند"""
        try:
            with db.get_session() as session:
                stmt = select(WorkSession).where(
                    WorkSession.status == SessionStatusEnum.ACTIVE
                )
                abandoned_sessions = session.scalars(stmt).all()
                for s in abandoned_sessions:
                    s.status = SessionStatusEnum.PAUSED
                    s.end_time = datetime.now()
                if abandoned_sessions:
                    session.commit()
        except Exception as e:
            print(f"Session recovery notice: {e}")

    def _on_system_metrics(self, data: dict):
        self.last_system_metric = data
        global_signals.system_activity_updated.emit(data)

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)
        is_core_nle = data.get("is_core_nle", False)
        is_supporting = data.get("is_supporting", False)
        idle_seconds = data.get("idle_seconds", 0)

        if not self.is_running:
            return

        # ۱. توقف خودکار با عبور از مهلت ۵ دقیقه و کسر زمان هرز
        if not self.is_paused:
            if (idle_seconds >= self.GRACE_PERIOD_SECONDS or state in ["distraction", "away"]) and not is_rendering:
                self.away_accumulated_seconds += 3
                if self.away_accumulated_seconds >= self.GRACE_PERIOD_SECONDS and not self.auto_suspended:
                    rollback_amount = min(self.active_seconds, self.GRACE_PERIOD_SECONDS)
                    self.active_seconds -= rollback_amount
                    self.auto_suspended = True
                    self.pause_session(auto=True)
                    global_signals.show_toast.emit("به دلیل عدم تحرک ۵ دقیقه‌ای، جلسه موقتاً متوقف و زمان هرز کسر شد.", "warning")
            else:
                self.away_accumulated_seconds = 0

        # ۲. ازسرگیری خودکار به محض بازگشت به نرم‌افزار تدوین
        else:
            if self.auto_suspended and (is_core_nle or is_supporting or is_rendering) and idle_seconds < 15:
                self.auto_suspended = False
                self.away_accumulated_seconds = 0
                self.resume_session()
                global_signals.show_toast.emit("تشخیص بازگشت به تدوین؛ زمان‌سنج خودکار فعال شد.", "success")

    def apply_retroactive_time(self, seconds_to_add: int):
        if self.is_running:
            self.active_seconds += seconds_to_add
            self._persist_active_session()
            global_signals.show_toast.emit(f"مدت زمان {seconds_to_add // 60} دقیقه به پروژه افزوده شد.", "success")
            self._emit_snapshot()

    def _on_tick(self):
        if not self.is_running:
            return

        if self.is_paused:
            self.paused_seconds += 1
        else:
            if self.last_system_metric.get("is_rendering"):
                self.render_seconds += 1
            self.active_seconds += 1

        self._emit_snapshot()

    def _emit_snapshot(self):
        snapshot = {
            "session_id": self.active_session_id,
            "project_id": self.current_project_id,
            "clip_id": self.current_clip_id,
            "active_seconds": self.active_seconds,
            "render_seconds": self.render_seconds,
            "paused_seconds": self.paused_seconds,
            "idle_seconds": self.idle_seconds,
            "total_seconds": self.active_seconds + self.paused_seconds,
            "is_paused": self.is_paused,
            "is_running": self.is_running
        }
        global_signals.timer_tick.emit(snapshot)

    def select_context(self, project_id: int, clip_id: Optional[int] = None):
        """تغییر کانتکست با توقف کامل سشن قبلی و بستن امن در دیتابیس"""
        if self.current_project_id == project_id and self.current_clip_id == clip_id:
            return

        if self.is_running:
            self.end_session(note="تغییر کانتکست به کلیپ دیگر", mark_clip_completed=False)

        self.tick_timer.stop()
        self.current_project_id = project_id
        self.current_clip_id = clip_id
        self.active_session_id = None
        self.active_seconds = 0
        self.paused_seconds = 0
        self.render_seconds = 0
        self.idle_seconds = 0
        self.is_paused = False
        self.is_running = False
        self.auto_suspended = False

        self._emit_snapshot()

    def start_session(self, project_id: int, clip_id: Optional[int] = None, stage_name: str = "Editing") -> int:
        if clip_id:
            with db.get_session() as session:
                clip = session.get(ProjectClipItem, clip_id)
                if clip and clip.is_completed:
                    global_signals.show_toast.emit("این کلیپ تکمیل شده است و امکان ثبت زمان ندارد.", "warning")
                    return 0

        if self.is_running:
            self.end_session(note="شروع سشن جدید روی کلیپ دیگر", mark_clip_completed=False)

        self.current_project_id = project_id
        self.current_clip_id = clip_id
        self.active_seconds = 0
        self.render_seconds = 0
        self.paused_seconds = 0
        self.idle_seconds = 0
        self.away_accumulated_seconds = 0
        self.is_paused = False
        self.auto_suspended = False
        self._last_logged_state = None

        with db.get_session() as session:
            new_sess = WorkSession(
                project_id=project_id,
                clip_id=clip_id,
                start_time=datetime.now(),
                activity_type="editing",
                stage_name=stage_name,
                status=SessionStatusEnum.ACTIVE,
                is_manual=False
            )
            session.add(new_sess)
            session.commit()
            self.active_session_id = new_sess.id

        self.is_running = True
        self.tick_timer.start()
        self.auto_save_timer.start()

        global_signals.session_started.emit(self.active_session_id)
        self._emit_snapshot()
        return self.active_session_id

    def pause_session(self, auto: bool = False):
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.tick_timer.stop()
            self._persist_active_session()

            if self.active_session_id:
                global_signals.session_paused.emit(self.active_session_id)
            self._emit_snapshot()

    def resume_session(self):
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.auto_suspended = False
            self.away_accumulated_seconds = 0
            self.tick_timer.start()
            self._persist_active_session()

            if self.active_session_id:
                global_signals.session_resumed.emit(self.active_session_id)
            self._emit_snapshot()

    def end_session(self, note: str = "", mark_clip_completed: bool = False) -> bool:
        if not self.is_running or not self.active_session_id:
            return False

        self.tick_timer.stop()
        self.auto_save_timer.stop()

        sess_id = self.active_session_id
        total_sec = self.active_seconds + self.paused_seconds

        with db.get_session() as session:
            sess = session.get(WorkSession, sess_id)
            if sess:
                sess.end_time = datetime.now()
                sess.active_duration = self.active_seconds
                sess.paused_duration = self.paused_seconds
                sess.idle_duration = self.idle_seconds
                sess.total_duration = total_sec
                sess.status = SessionStatusEnum.COMPLETED
                if note:
                    sess.note = note
                sess.is_clip_completed = mark_clip_completed

                if mark_clip_completed and sess.clip_id:
                    clip = session.get(ProjectClipItem, sess.clip_id)
                    if clip:
                        clip.is_completed = True
                        clip.completed_at = datetime.now()
                        session.flush()
                        global_signals.clip_status_toggled.emit(clip.project_id, clip.id)

                session.commit()

        self.is_running = False
        self.is_paused = False
        self.auto_suspended = False
        self.active_session_id = None
        self.active_seconds = 0
        self.render_seconds = 0
        self.paused_seconds = 0
        self.idle_seconds = 0

        global_signals.session_ended.emit(sess_id)
        global_signals.project_updated.emit(self.current_project_id or 0)
        self._emit_snapshot()
        return True

    def _persist_active_session(self):
        """به‌روزرسانی سبک سشن فعال بدون تولید لاگ‌های تکراری"""
        if not self.active_session_id:
            return
        try:
            with db.get_session() as session:
                sess = session.get(WorkSession, self.active_session_id)
                if sess and sess.status in [SessionStatusEnum.ACTIVE, SessionStatusEnum.PAUSED]:
                    sess.active_duration = self.active_seconds
                    sess.paused_duration = self.paused_seconds
                    sess.idle_duration = self.idle_seconds
                    sess.total_duration = self.active_seconds + self.paused_seconds
                    sess.status = SessionStatusEnum.PAUSED if self.is_paused else SessionStatusEnum.ACTIVE

                    current_state = self.last_system_metric.get("state")
                    if current_state and current_state != self._last_logged_state:
                        self._last_logged_state = current_state
                        log = ActivityLog(
                            session_id=sess.id,
                            application_name=self.last_system_metric.get("active_app", ""),
                            window_title=self.last_system_metric.get("window_title", "")[:240],
                            state=current_state,
                            cpu_usage=self.last_system_metric.get("cpu_percent", 0.0),
                            gpu_usage=self.last_system_metric.get("gpu_percent", 0.0),
                            ram_usage=self.last_system_metric.get("ram_percent", 0.0),
                            user_idle_seconds=self.last_system_metric.get("idle_seconds", 0),
                            timestamp=datetime.now()
                        )
                        session.add(log)

                    session.commit()
        except Exception as e:
            print(f"Persist session error: {e}")

    def get_today_total_active_seconds(self) -> int:
        """محاسبه دقیق مجموع ثانیه‌های کارکرد امروز بر اساس ساعت محلی"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        with db.get_session() as session:
            stmt = select(func.sum(WorkSession.active_duration)).where(
                WorkSession.start_time >= today_start
            )
            res = session.execute(stmt).scalar() or 0
            if self.is_running and not self.is_paused:
                res += self.active_seconds
            return int(res)

    def get_today_focus_metrics(self) -> Tuple[int, str, str]:
        """محاسبه دقیق درصد تمرکز واقعی، برچسب وضعیت و رنگ متناسب برای جلسات امروز"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        with db.get_session() as session:
            stmt = select(
                func.sum(WorkSession.active_duration),
                func.sum(WorkSession.paused_duration),
                func.sum(WorkSession.idle_duration)
            ).where(WorkSession.start_time >= today_start)
            
            row = session.execute(stmt).first()
            act = (row[0] or 0) if row else 0
            pau = (row[1] or 0) if row else 0
            idl = (row[2] or 0) if row else 0

            # افزودن ثانیه‌های جاری سشن فعال
            if self.is_running and not self.is_paused:
                act += self.active_seconds
            elif self.is_running and self.is_paused:
                pau += self.paused_seconds

            total = act + pau + idl
            if total <= 0:
                return 100, "آماده شروع کار", "#10B981"

            focus_pct = int((act / total) * 100)
            focus_pct = max(0, min(100, focus_pct))

            if focus_pct >= 80:
                return focus_pct, "تمرکز عالی و پایدار", "#10B981"
            elif focus_pct >= 60:
                return focus_pct, "تمرکز مطلوب", "#F59E0B"
            else:
                return focus_pct, "توقف‌های مکرر", "#EF4444"

    def get_daily_goal_minutes(self) -> int:
        today_str = date.today().isoformat()
        with db.get_session() as session:
            goal = session.scalars(select(DailyGoal).where(DailyGoal.date_str == today_str)).first()
            if goal:
                return goal.target_minutes
            return 480

    def set_daily_goal_minutes(self, minutes: int):
        today_str = date.today().isoformat()
        with db.get_session() as session:
            goal = session.scalars(select(DailyGoal).where(DailyGoal.date_str == today_str)).first()
            if not goal:
                goal = DailyGoal(date_str=today_str, target_minutes=minutes)
                session.add(goal)
            else:
                goal.target_minutes = minutes
                goal.updated_at = datetime.now()
            session.commit()