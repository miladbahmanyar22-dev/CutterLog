# ==================================================
# FILE: core/project_controller.py
# ==================================================
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from database.db_manager import db
from database.models import (
    Project, Client, DriveLocation, ProjectClipItem, 
    ProjectRevision, ProjectRevisionTask, Transaction, ProjectEventLog,
    StageEnum, WorkflowStatusEnum, RevisionStatusEnum
)
from core.settings_manager import SettingsManager
from core.persian_utils import to_persian_numbers
from core.signals import global_signals
from widgets.status_badge import StatusType


def get_persian_round_title(number: int) -> str:
    ordinals = {
        1: "اول", 2: "دوم", 3: "سوم", 4: "چهارم", 5: "پنجم",
        6: "ششم", 7: "هفتم", 8: "هشتم", 9: "نهم", 10: "دهم"
    }
    suffix = ordinals.get(number, f"{number}م")
    return f"اصلاحیه دور {suffix}"


class ProjectController:
    @staticmethod
    def log_event(session, project_id: int, event_type: str, title: str, description: str = ""):
        try:
            log = ProjectEventLog(
                project_id=project_id,
                event_type=event_type,
                title=title,
                description=description,
                created_at=datetime.utcnow()
            )
            session.add(log)
        except Exception as e:
            print(f"Log Event Error: {e}")

    @staticmethod
    def get_project_financial_summary(project: Project) -> Dict[str, Any]:
        base_fee = int(project.base_fee or 0)
        revisions_fee = sum(int(r.extra_fee or 0) for r in (project.revisions or []))
        
        if base_fee == 0 and int(project.total_fee or 0) > 0:
            base_fee = int(project.total_fee) - revisions_fee
            base_fee = max(0, base_fee)

        total_fee = int(base_fee + revisions_fee)
        total_paid = sum(int(t.amount or 0) for t in (project.transactions or []))
        remaining = int(total_fee - total_paid)

        if total_fee > 0:
            if remaining > 0:
                is_settled = False
                status_color = "#F59E0B"
                status_label = f"مانده بدهی: {remaining:,} تومان"
            elif remaining == 0:
                is_settled = True
                status_color = "#10B981"
                status_label = "تسویه کامل (۰ تومان) ✓"
            else:
                is_settled = True
                status_color = "#38BDF8"
                status_label = f"اضافه پرداخت: {abs(remaining):,} تومان"
        else:
            is_settled = False
            status_color = "#94A3B8"
            status_label = "بدون مبلغ قرارداد"

        return {
            "base_fee": base_fee,
            "revisions_fee": revisions_fee,
            "total_fee": total_fee,
            "total_paid": total_paid,
            "remaining": max(0, remaining),
            "raw_balance": remaining,
            "is_settled": is_settled,
            "status_label": status_label,
            "status_color": status_color
        }

    @staticmethod
    def get_status_info(project: Project) -> Dict[str, Any]:
        now = datetime.utcnow()

        if project.is_archived:
            return {
                "key": WorkflowStatusEnum.ARCHIVED.value,
                "label": "آرشیو شده",
                "type": StatusType.NEUTRAL,
                "symbol": "✓"
            }

        active_rev = ProjectController.get_active_revision(project)
        if active_rev:
            c, t, pct = ProjectController.calculate_revision_progress(active_rev)
            if pct == 100 and t > 0:
                return {
                    "key": WorkflowStatusEnum.REVISION_DONE.value,
                    "label": "اصلاحیه تکمیل شد",
                    "type": StatusType.PENDING,
                    "symbol": "✓"
                }
            return {
                "key": WorkflowStatusEnum.REVISION_IN_PROGRESS.value,
                "label": "در حال اصلاح",
                "type": StatusType.WARNING,
                "symbol": "●"
            }

        c_clips, t_clips, pct_clips = ProjectController.calculate_project_progress(project)
        if t_clips > 0 and c_clips == t_clips:
            if project.workflow_status == WorkflowStatusEnum.UNDER_REVIEW or project.current_stage == StageEnum.DELIVERED:
                settings = SettingsManager.load_settings()
                limit_days = settings.get("auto_archive_delivered_days", 7)
                
                label_text = "تحویل شد / منتظر بازبینی"
                status_symbol = "⏳"
                if limit_days > 0 and project.delivered_at:
                    elapsed_days = (now - project.delivered_at).days
                    days_left = max(0, limit_days - elapsed_days)
                    if days_left > 0:
                        label_text = f"تحویل شد (آرشیو تا {to_persian_numbers(days_left)} روز دیگر ⏳)"
                    else:
                        label_text = "مهلت بازبینی پایان یافت (آماده آرشیو)"
                        status_symbol = "📁"

                return {
                    "key": WorkflowStatusEnum.UNDER_REVIEW.value,
                    "label": label_text,
                    "type": StatusType.PENDING,
                    "symbol": status_symbol
                }
            return {
                "key": WorkflowStatusEnum.READY_FOR_DELIVERY.value,
                "label": "آماده تحویل به آتلیه",
                "type": StatusType.ACTIVE,
                "symbol": "●"
            }

        if project.deadline:
            delta_days = (project.deadline.date() - now.date()).days
            if delta_days < 0:
                return {
                    "key": "overdue",
                    "label": "تأخیر در تحویل",
                    "type": StatusType.DANGER,
                    "symbol": "!"
                }
            elif delta_days <= 2:
                return {
                    "key": "near_deadline",
                    "label": "نزدیک به تحویل",
                    "type": StatusType.WARNING,
                    "symbol": "!"
                }

        stage_val = project.current_stage.value if hasattr(project.current_stage, "value") else str(project.current_stage)
        if stage_val == StageEnum.INGEST.value:
            return {"key": "ingest", "label": "آماده‌سازی راش‌ها", "type": StatusType.NEUTRAL, "symbol": "●"}
        elif stage_val == StageEnum.COLOR_AUDIO.value:
            return {"key": "color_audio", "label": "اصلاح رنگ و صدا", "type": StatusType.ACTIVE, "symbol": "●"}
        elif stage_val == StageEnum.FINAL_RENDER.value:
            return {"key": "final_render", "label": "رندر نهایی", "type": StatusType.ACTIVE, "symbol": "●"}

        return {
            "key": WorkflowStatusEnum.EDITING.value,
            "label": "در حال تدوین",
            "type": StatusType.ACTIVE,
            "symbol": "●"
        }

    @staticmethod
    def mark_as_delivered(project_id: int) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            
            project.workflow_status = WorkflowStatusEnum.UNDER_REVIEW
            project.current_stage = StageEnum.DELIVERED
            project.delivered_at = datetime.utcnow()
            
            ProjectController.log_event(
                session, project_id, "DELIVERED_TO_CLIENT", 
                "تحویل فایل به آتلیه", 
                "فایل‌های تدوین‌شده جهت بررسی برای آتلیه ارسال شد. تایمر بازبینی و آرشیو خودکار آغاز گردید."
            )
            session.commit()

        global_signals.stage_changed.emit(project_id, StageEnum.DELIVERED.value)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def archive_project(project_id: int) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False

            project.is_archived = True
            project.archived_at = datetime.utcnow()
            project.current_stage = StageEnum.DELIVERED
            project.workflow_status = WorkflowStatusEnum.ARCHIVED

            for rev in project.revisions:
                rev.status = RevisionStatusEnum.ARCHIVED

            ProjectController.log_event(
                session, project_id, "ARCHIVED", 
                "انتقال رسمی به آرشیو", 
                "پرونده پروژه با تأیید تدوین‌گر به بخش آرشیو منتقل شد."
            )
            session.commit()

        global_signals.project_archived.emit(project_id)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def unarchive_project(project_id: int) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False

            project.is_archived = False
            project.archived_at = None
            project.workflow_status = WorkflowStatusEnum.EDITING

            ProjectController.log_event(
                session, project_id, "UNARCHIVED", 
                "خروج از آرشیو", 
                "پروژه به لیست پروژه‌های فعال بازگردانده شد."
            )
            session.commit()

        global_signals.project_unarchived.emit(project_id)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def check_and_process_auto_archive_delivered():
        settings = SettingsManager.load_settings()
        limit_days = settings.get("auto_archive_delivered_days", 7)
        if limit_days <= 0:
            return

        archived_ids = []
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(selectinload(Project.revisions))
                .where(
                    Project.is_archived == False,
                    Project.workflow_status == WorkflowStatusEnum.UNDER_REVIEW,
                    Project.delivered_at != None
                )
            )
            projects = session.scalars(stmt).unique().all()
            now = datetime.utcnow()

            for p in projects:
                active_rev = ProjectController.get_active_revision(p)
                if not active_rev and p.delivered_at:
                    if (now - p.delivered_at).days >= limit_days:
                        p.is_archived = True
                        p.archived_at = now
                        p.workflow_status = WorkflowStatusEnum.ARCHIVED
                        for rev in p.revisions:
                            rev.status = RevisionStatusEnum.ARCHIVED
                        
                        ProjectController.log_event(
                            session, p.id, "AUTO_ARCHIVED_SILENT", 
                            f"آرشیو خودکار پس از {limit_days} روز تحویل", 
                            "به دلیل عدم ارسال اصلاحیه توسط آتلیه در مهلت مقرر، پروژه به آرشیو منتقل شد."
                        )
                        archived_ids.append(p.id)

            if archived_ids:
                session.commit()

        for pid in archived_ids:
            global_signals.project_archived.emit(pid)
            global_signals.project_updated.emit(pid)

    @staticmethod
    def get_active_projects() -> List[Project]:
        ProjectController.check_and_process_auto_archive_delivered()
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    joinedload(Project.drive_locations),
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks),
                    joinedload(Project.transactions).joinedload(Transaction.revision)
                )
                .where(Project.is_archived == False)
                .order_by(Project.created_at.desc())
            )
            return session.scalars(stmt).unique().all()

    @staticmethod
    def get_archived_projects() -> List[Project]:
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    joinedload(Project.drive_locations),
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks),
                    joinedload(Project.transactions).joinedload(Transaction.revision)
                )
                .where(Project.is_archived == True)
                .order_by(Project.archived_at.desc())
            )
            return session.scalars(stmt).unique().all()

    @staticmethod
    def get_all_projects() -> List[Project]:
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    joinedload(Project.drive_locations),
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks),
                    joinedload(Project.transactions).joinedload(Transaction.revision)
                )
                .order_by(Project.created_at.desc())
            )
            return session.scalars(stmt).unique().all()

    @staticmethod
    def get_project_by_id(project_id: int) -> Optional[Project]:
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    joinedload(Project.drive_locations),
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks),
                    joinedload(Project.transactions).joinedload(Transaction.revision),
                    selectinload(Project.event_logs)
                )
                .where(Project.id == project_id)
            )
            return session.scalars(stmt).unique().first()

    @staticmethod
    def calculate_project_progress(project: Project) -> Tuple[int, int, int]:
        if not project or not project.clips:
            return 0, 0, 0
        total = len(project.clips)
        completed = sum(1 for c in project.clips if c.is_completed)
        percentage = int((completed / total) * 100) if total > 0 else 0
        return completed, total, percentage

    @staticmethod
    def calculate_revision_progress(revision: Optional[ProjectRevision]) -> Tuple[int, int, int]:
        if not revision or not revision.tasks:
            return 0, 0, 0
        total = len(revision.tasks)
        completed = sum(1 for t in revision.tasks if t.is_completed)
        percentage = int((completed / total) * 100) if total > 0 else 0
        return completed, total, percentage

    @staticmethod
    def get_active_revision(project: Project) -> Optional[ProjectRevision]:
        if not project or not project.revisions:
            return None
        last_rev = project.revisions[-1]
        if last_rev.status != RevisionStatusEnum.ARCHIVED and last_rev.status != RevisionStatusEnum.COMPLETED:
            return last_rev
        return None

    @staticmethod
    def toggle_clip_status(clip_id: int) -> Optional[bool]:
        project_id = None
        new_status = None
        with db.get_session() as session:
            clip = session.get(ProjectClipItem, clip_id)
            if not clip:
                return None
            
            clip.is_completed = not clip.is_completed
            clip.completed_at = datetime.utcnow() if clip.is_completed else None
            project_id = clip.project_id
            new_status = clip.is_completed
            session.flush()

            project = session.get(Project, project_id)
            total = len(project.clips)
            completed = sum(1 for c in project.clips if c.is_completed)
            active_rev = ProjectController.get_active_revision(project)

            if total > 0 and completed == total:
                if not active_rev:
                    project.workflow_status = WorkflowStatusEnum.READY_FOR_DELIVERY
                if not project.completed_at:
                    project.completed_at = datetime.utcnow()
                ProjectController.log_event(session, project_id, "CLIPS_100", "تکمیل ۱۰۰٪ کلیپ‌های اولیه", f"کلیپ {clip.clip_name} آماده تحویل شد.")
            else:
                if not active_rev:
                    project.workflow_status = WorkflowStatusEnum.EDITING
                project.completed_at = None
                ProjectController.log_event(session, project_id, "CLIP_TOGGLE", f"تغییر وضعیت کلیپ {clip.clip_name}", "تکمیل شد" if clip.is_completed else "به باقی‌مانده بازگشت")

            session.commit()

        global_signals.clip_status_toggled.emit(project_id, clip_id)
        global_signals.project_updated.emit(project_id)
        return new_status

    @staticmethod
    def toggle_revision_task(task_id: int) -> Optional[bool]:
        project_id = None
        revision_id = None
        new_status = None
        with db.get_session() as session:
            task = session.get(ProjectRevisionTask, task_id)
            if not task:
                return None
            
            task.is_completed = not task.is_completed
            task.completed_at = datetime.utcnow() if task.is_completed else None
            new_status = task.is_completed
            session.flush()

            rev = session.get(ProjectRevision, task.revision_id)
            revision_id = rev.id
            project_id = rev.project_id
            
            total_tasks = len(rev.tasks)
            completed_tasks = sum(1 for t in rev.tasks if t.is_completed)
            
            if total_tasks > 0 and completed_tasks == total_tasks:
                rev.status = RevisionStatusEnum.COMPLETED
                rev.completed_at = datetime.utcnow()
                rev.project.workflow_status = WorkflowStatusEnum.REVISION_DONE
                ProjectController.log_event(session, project_id, "REVISION_DONE", f"تکمیل تسک‌های {rev.title}", "تمام موارد اصلاحیه انجام شد.")
            elif completed_tasks > 0:
                rev.status = RevisionStatusEnum.IN_PROGRESS
                rev.completed_at = None
                rev.project.workflow_status = WorkflowStatusEnum.REVISION_IN_PROGRESS
            else:
                rev.status = RevisionStatusEnum.NEW_REQUEST
                rev.completed_at = None
                rev.project.workflow_status = WorkflowStatusEnum.REVISION_IN_PROGRESS

            session.commit()

        global_signals.revision_task_toggled.emit(project_id, revision_id, task_id)
        global_signals.revision_updated.emit(project_id, revision_id)
        global_signals.project_updated.emit(project_id)
        return new_status

    @staticmethod
    def create_revision_round(project_id: int, description: str, tasks: List[str], extra_fee: int = 0) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False

            active_rev = ProjectController.get_active_revision(project)
            if active_rev:
                return False

            rev_num = len(project.revisions) + 1
            round_title = get_persian_round_title(rev_num)

            rev = ProjectRevision(
                project_id=project.id,
                revision_number=rev_num,
                title=round_title,
                description=description.strip(),
                extra_fee=extra_fee,
                status=RevisionStatusEnum.NEW_REQUEST,
                requested_at=datetime.utcnow()
            )
            session.add(rev)
            session.flush()

            for task_str in tasks:
                t_text = task_str.strip()
                if t_text:
                    session.add(ProjectRevisionTask(
                        revision_id=rev.id,
                        task_text=t_text,
                        is_completed=False
                    ))

            revisions_sum = sum(r.extra_fee for r in project.revisions)
            if (project.base_fee or 0) == 0 and project.total_fee > 0:
                project.base_fee = project.total_fee
            project.total_fee = (project.base_fee or 0) + revisions_sum

            project.is_archived = False
            project.archived_at = None
            project.delivered_at = None
            project.current_stage = StageEnum.CLIENT_REVIEW
            project.workflow_status = WorkflowStatusEnum.REVISION_IN_PROGRESS

            ProjectController.log_event(session, project_id, "REVISION_CREATED", f"ثبت {round_title}", f"{len(tasks)} تغییر درخواستی استودیو ثبت شد.")
            session.commit()

        global_signals.revision_added.emit(project_id)
        global_signals.project_unarchived.emit(project_id)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def add_task_to_revision(revision_id: int, task_text: str) -> bool:
        if not task_text.strip():
            return False
        project_id = None
        with db.get_session() as session:
            rev = session.get(ProjectRevision, revision_id)
            if not rev:
                return False
            project_id = rev.project_id
            
            session.add(ProjectRevisionTask(
                revision_id=rev.id,
                task_text=task_text.strip(),
                is_completed=False
            ))
            session.flush()

            rev.status = RevisionStatusEnum.IN_PROGRESS
            rev.completed_at = None

            project = rev.project
            project.is_archived = False
            project.archived_at = None
            project.workflow_status = WorkflowStatusEnum.REVISION_IN_PROGRESS
            session.commit()

        global_signals.revision_updated.emit(project_id, revision_id)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def delete_revision_task(task_id: int) -> bool:
        project_id = None
        revision_id = None
        with db.get_session() as session:
            task = session.get(ProjectRevisionTask, task_id)
            if not task:
                return False
            rev = task.revision
            revision_id = rev.id
            project_id = rev.project_id

            session.delete(task)
            session.flush()

            total_tasks = len(rev.tasks)
            completed_tasks = sum(1 for t in rev.tasks if t.is_completed)
            if total_tasks > 0 and completed_tasks == total_tasks:
                rev.status = RevisionStatusEnum.COMPLETED
                rev.completed_at = datetime.utcnow()
                rev.project.workflow_status = WorkflowStatusEnum.REVISION_DONE

            session.commit()

        global_signals.revision_updated.emit(project_id, revision_id)
        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def update_project(project_id: int, data: Dict[str, Any]) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False

            project.title = data.get("title", project.title)
            project.couple_names = data.get("couple_names", project.couple_names)
            project.client_id = data.get("client_id", project.client_id)
            
            if "base_fee" in data:
                project.base_fee = data["base_fee"]
                revisions_sum = sum(r.extra_fee for r in project.revisions)
                project.total_fee = project.base_fee + revisions_sum
            elif "total_fee" in data:
                project.base_fee = data["total_fee"]
                revisions_sum = sum(r.extra_fee for r in project.revisions)
                project.total_fee = project.base_fee + revisions_sum

            project.event_date = data.get("event_date", project.event_date)
            project.deadline = data.get("deadline", project.deadline)
            
            if "nle_project_path" in data:
                project.nle_project_path = data["nle_project_path"]

            if "clips" in data:
                existing_clips_map = {c.clip_name: (c.is_completed, c.completed_at) for c in project.clips}
                for c in list(project.clips):
                    session.delete(c)
                session.flush()
                for clip_name in data["clips"]:
                    prev_status, prev_dt = existing_clips_map.get(clip_name, (False, None))
                    session.add(ProjectClipItem(
                        project_id=project.id,
                        clip_name=clip_name,
                        is_completed=prev_status,
                        completed_at=prev_dt
                    ))

            if "primary_path" in data and data["primary_path"]:
                if project.drive_locations:
                    project.drive_locations[0].absolute_path = data["primary_path"]
                else:
                    session.add(DriveLocation(
                        project_id=project.id,
                        drive_label="هارد اصلی پروژه",
                        absolute_path=data["primary_path"],
                        is_primary=True
                    ))

            session.commit()

        global_signals.project_updated.emit(project_id)
        return True

    @staticmethod
    def delete_project(project_id: int) -> bool:
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                return False
            session.delete(project)
            session.commit()

        global_signals.project_deleted.emit(project_id)
        return True