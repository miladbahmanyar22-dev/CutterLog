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
        
        self.active_seconds = 0
        self.render_seconds = 0
        self.paused_seconds = 0
        self.idle_seconds = 0
        self.away_accumulated_seconds = 0
        
        self.is_paused = False
        self.is_running = False
        self.auto_suspended = False

        # حافظه ایزوله برای نگهداری وضعیت تایمر هر کلیپ به تفکیک (project_id, clip_id)
        self.sessions_memory: Dict[Tuple[int, Optional[int]], Dict[str, Any]] = {}
        self.last_system_metric: Dict[str, Any] = {}

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(1000)
        self.tick_timer.timeout.connect(self._on_tick)

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(30000)
        self.auto_save_timer.timeout.connect(self._persist_active_session)

        # ترد پایش فعالیت سیستم
        self.monitor_thread = SystemActivityMonitorThread(check_interval_sec=2.0, parent=self)
        self.monitor_thread.metrics_updated.connect(self._on_system_metrics)
        self.monitor_thread.start()

        self._load_persisted_paused_sessions()

    def _load_persisted_paused_sessions(self):
        try:
            with db.get_session() as session:
                stmt = select(WorkSession).where(
                    WorkSession.status == SessionStatusEnum.PAUSED
                ).order_by(WorkSession.start_time.desc())
                paused_sessions = session.scalars(stmt).all()

                for s in paused_sessions:
                    key = (s.project_id, s.clip_id)
                    self.sessions_memory[key] = {
                        "session_id": s.id,
                        "active_seconds": s.active_duration or 0,
                        "paused_seconds": s.paused_duration or 0,
                        "idle_seconds": s.idle_duration or 0,
                        "is_paused": True,
                        "is_running": True
                    }

                if paused_sessions:
                    latest = paused_sessions[0]
                    self.select_context(latest.project_id, latest.clip_id)
        except Exception:
            pass

    def _on_system_metrics(self, data: dict):
        self.last_system_metric = data
        global_signals.system_activity_updated.emit(data)

        state = data.get("state", "idle")
        is_rendering = data.get("is_rendering", False)
        is_core_nle = data.get("is_core_nle", False)
        is_supporting = data.get("is_supporting", False)

        if not self.is_running or self.is_paused:
            return

        # پایش هوشمند خروج از محیط تدوین
        if state in ["distraction", "away"] and not is_rendering:
            self.away_accumulated_seconds += 2  # متناسب با Interval جدید ۲ ثانیه‌ای
            if self.away_accumulated_seconds >= 60 and not self.auto_suspended:
                self.auto_suspended = True
                self.pause_session(auto=True)
                global_signals.show_toast.emit("خروج از محیط تدوین؛ جلسه کاری به صورت خودکار متوقف شد.", "info")
        else:
            if self.auto_suspended and (is_core_nle or is_supporting or is_rendering):
                away_sec = self.away_accumulated_seconds
                self.auto_suspended = False
                self.away_accumulated_seconds = 0
                self.resume_session()

                if away_sec >= 90:
                    self.retroactive_prompt_requested.emit(away_sec, data.get("active_app", "سایر برنامه‌ها"))
            else:
                self.away_accumulated_seconds = 0

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
        total_sec = self.active_seconds + self.paused_seconds
        snapshot = {
            "session_id": self.active_session_id,
            "project_id": self.current_project_id,
            "clip_id": self.current_clip_id,
            "active_seconds": self.active_seconds,
            "render_seconds": self.render_seconds,
            "paused_seconds": self.paused_seconds,
            "idle_seconds": self.idle_seconds,
            "total_seconds": total_sec,
            "is_paused": self.is_paused,
            "is_running": self.is_running
        }
        global_signals.timer_tick.emit(snapshot)

    def select_context(self, project_id: int, clip_id: Optional[int] = None):
        """تغییر ایزوله کانتکست کاری بین پروژه‌ها و کلیپ‌ها بدون تداخل زمانی"""
        # ۱. ذخیره وضعیت جلسه فعلی در حافظه سشن‌ها
        if self.current_project_id is not None:
            old_key = (self.current_project_id, self.current_clip_id)
            if self.is_running:
                self.sessions_memory[old_key] = {
                    "session_id": self.active_session_id,
                    "active_seconds": self.active_seconds,
                    "paused_seconds": self.paused_seconds,
                    "idle_seconds": self.idle_seconds,
                    "is_paused": self.is_paused,
                    "is_running": self.is_running
                }
                self.tick_timer.stop()

        # ۲. مقداردهی هویت کانتکست جدید
        self.current_project_id = project_id
        self.current_clip_id = clip_id
        new_key = (project_id, clip_id)

        # ۳. بازیابی وضعیت کانتکست جدید در صورت وجود سابقه فعال
        if new_key in self.sessions_memory:
            state = self.sessions_memory[new_key]
            self.active_session_id = state["session_id"]
            self.active_seconds = state["active_seconds"]
            self.paused_seconds = state["paused_seconds"]
            self.idle_seconds = state["idle_seconds"]
            self.is_paused = state["is_paused"]
            self.is_running = state["is_running"]
            self.auto_suspended = False

            if self.is_running and not self.is_paused:
                self.tick_timer.start()
        else:
            self.active_session_id = None
            self.active_seconds = 0
            self.paused_seconds = 0
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

        self.current_project_id = project_id
        self.current_clip_id = clip_id
        self.active_seconds = 0
        self.render_seconds = 0
        self.paused_seconds = 0
        self.idle_seconds = 0
        self.away_accumulated_seconds = 0
        self.is_paused = False
        self.auto_suspended = False

        with db.get_session() as session:
            new_sess = WorkSession(
                project_id=project_id,
                clip_id=clip_id,
                start_time=datetime.utcnow(),
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

        key = (project_id, clip_id)
        self.sessions_memory[key] = {
            "session_id": self.active_session_id,
            "active_seconds": self.active_seconds,
            "paused_seconds": self.paused_seconds,
            "idle_seconds": self.idle_seconds,
            "is_paused": False,
            "is_running": True
        }

        global_signals.session_started.emit(self.active_session_id)
        self._emit_snapshot()
        return self.active_session_id

    def pause_session(self, auto: bool = False):
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.tick_timer.stop()
            self._persist_active_session()
            
            key = (self.current_project_id, self.current_clip_id)
            if key in self.sessions_memory:
                self.sessions_memory[key]["is_paused"] = True
                self.sessions_memory[key]["active_seconds"] = self.active_seconds

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

            key = (self.current_project_id, self.current_clip_id)
            if key in self.sessions_memory:
                self.sessions_memory[key]["is_paused"] = False

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
                sess.end_time = datetime.utcnow()
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
                        clip.completed_at = datetime.utcnow()
                        session.flush()
                        global_signals.clip_status_toggled.emit(clip.project_id, clip.id)

                session.commit()

        key = (self.current_project_id, self.current_clip_id)
        if key in self.sessions_memory:
            del self.sessions_memory[key]

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

                    if self.last_system_metric:
                        log = ActivityLog(
                            session_id=sess.id,
                            application_name=self.last_system_metric.get("active_app", ""),
                            window_title=self.last_system_metric.get("window_title", "")[:240],
                            state=self.last_system_metric.get("state", "editing"),
                            cpu_usage=self.last_system_metric.get("cpu_percent", 0.0),
                            gpu_usage=0.0,
                            ram_usage=self.last_system_metric.get("ram_percent", 0.0),
                            user_idle_seconds=self.last_system_metric.get("idle_seconds", 0)
                        )
                        session.add(log)

                    session.commit()
        except Exception:
            pass

    def get_today_total_active_seconds(self) -> int:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with db.get_session() as session:
            stmt = select(func.sum(WorkSession.active_duration)).where(
                WorkSession.start_time >= today_start
            )
            res = session.execute(stmt).scalar() or 0
            if self.is_running and not self.is_paused:
                res += self.active_seconds
            return int(res)

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
                goal.updated_at = datetime.utcnow()
            session.commit()