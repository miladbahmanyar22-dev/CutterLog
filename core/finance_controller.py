# ==================================================
# FILE: core/finance_controller.py
# ==================================================
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import jdatetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from database.db_manager import db
from database.models import Project, Transaction, Client, StageEnum, ProjectRevision, PaymentTypeEnum, WorkflowStatusEnum
from core.project_controller import ProjectController


class FinanceController:
    @staticmethod
    def is_project_eligible_for_finance(project: Project) -> bool:
        if project.is_archived:
            return True
        if project.delivered_at is not None:
            return True
        if project.current_stage == StageEnum.DELIVERED:
            return True
        if project.workflow_status in [
            WorkflowStatusEnum.UNDER_REVIEW, 
            WorkflowStatusEnum.REVISION_IN_PROGRESS, 
            WorkflowStatusEnum.REVISION_DONE, 
            WorkflowStatusEnum.ARCHIVED
        ]:
            return True
        return False

    @staticmethod
    def get_date_range_bounds(range_key: str, custom_start: Optional[datetime] = None, custom_end: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        now_j = jdatetime.datetime.now()
        
        if range_key == "today":
            start_j = now_j.replace(hour=0, minute=0, second=0, microsecond=0)
            end_j = now_j.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "this_week":
            start_j = (now_j - timedelta(days=now_j.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            end_j = now_j.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "this_month":
            start_j = jdatetime.datetime(now_j.year, now_j.month, 1, 0, 0, 0)
            end_j = now_j.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "last_month":
            if now_j.month == 1:
                prev_year = now_j.year - 1
                prev_month = 12
            else:
                prev_year = now_j.year
                prev_month = now_j.month - 1
            
            start_j = jdatetime.datetime(prev_year, prev_month, 1, 0, 0, 0)
            days_in_month = 29 if (prev_month == 12 and not jdatetime.date(prev_year, 1, 1).isleap()) else (30 if prev_month > 6 else 31)
            end_j = jdatetime.datetime(prev_year, prev_month, days_in_month, 23, 59, 59)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "this_year":
            start_j = jdatetime.datetime(now_j.year, 1, 1, 0, 0, 0)
            end_j = now_j.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "last_year":
            prev_year = now_j.year - 1
            start_j = jdatetime.datetime(prev_year, 1, 1, 0, 0, 0)
            days_in_12 = 30 if jdatetime.date(prev_year, 1, 1).isleap() else 29
            end_j = jdatetime.datetime(prev_year, 12, days_in_12, 23, 59, 59)
            return start_j.togregorian(), end_j.togregorian()
            
        elif range_key == "custom":
            return custom_start, custom_end
            
        return None, None

    @staticmethod
    def get_studio_debt_summary(client_id: int) -> Dict[str, Any]:
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    selectinload(Project.revisions),
                    joinedload(Project.transactions)
                )
                .where(Project.client_id == client_id)
                .order_by(Project.created_at.asc())
            )
            all_projects = session.scalars(stmt).unique().all()

        eligible_projects = [p for p in all_projects if FinanceController.is_project_eligible_for_finance(p)]

        total_fee = 0
        total_paid = 0
        unsettled_projects = []
        settled_projects = []

        for p in eligible_projects:
            fin = ProjectController.get_project_financial_summary(p)
            total_fee += fin["total_fee"]
            total_paid += fin["total_paid"]

            p_summary = {
                "id": p.id,
                "project_number": p.project_number or p.id,
                "title": p.couple_names or p.title,
                "total_fee": fin["total_fee"],
                "total_paid": fin["total_paid"],
                "remaining": fin["remaining"],
                "is_settled": fin["is_settled"],
                "created_at": p.created_at
            }

            if fin["remaining"] > 0:
                unsettled_projects.append(p_summary)
            else:
                settled_projects.append(p_summary)

        return {
            "total_fee": total_fee,
            "total_paid": total_paid,
            "total_remaining": max(0, total_fee - total_paid),
            "unsettled_projects": unsettled_projects,
            "settled_projects": settled_projects,
            "all_projects_count": len(eligible_projects)
        }

    @staticmethod
    def allocate_client_payment(
        client_id: int,
        total_amount: int,
        payment_type: PaymentTypeEnum = PaymentTypeEnum.STAGE_PAYMENT,
        notes: str = "",
        tracking_code: str = "",
        paid_at: Optional[datetime] = None
    ) -> List[int]:
        if total_amount <= 0:
            return []

        paid_at = paid_at or datetime.utcnow()
        created_transaction_ids = []

        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    selectinload(Project.revisions),
                    joinedload(Project.transactions)
                )
                .where(Project.client_id == client_id)
                .order_by(Project.created_at.asc())
            )
            all_projects = session.scalars(stmt).unique().all()
            eligible_projects = [p for p in all_projects if FinanceController.is_project_eligible_for_finance(p)]

            remaining_to_allocate = total_amount

            for p in eligible_projects:
                if remaining_to_allocate <= 0:
                    break

                fin = ProjectController.get_project_financial_summary(p)
                proj_remaining = fin["remaining"]

                if proj_remaining > 0:
                    allocated_for_this = min(proj_remaining, remaining_to_allocate)
                    combined_note = f"{notes.strip()} [تخصیص از واریزی استودیو: {allocated_for_this:,} تومان]".strip()

                    trx = Transaction(
                        project_id=p.id,
                        client_id=client_id,
                        amount=allocated_for_this,
                        payment_type=payment_type,
                        notes=combined_note,
                        tracking_code=tracking_code.strip() or None,
                        paid_at=paid_at
                    )
                    session.add(trx)
                    session.flush()
                    created_transaction_ids.append(trx.id)

                    ProjectController.log_event(
                        session, p.id, "TRANSACTION_ADDED",
                        f"دریافت مبلغ {allocated_for_this:,} تومان (تسویه خودکار)",
                        combined_note
                    )

                    remaining_to_allocate -= allocated_for_this

            if remaining_to_allocate > 0:
                last_project = eligible_projects[-1] if eligible_projects else None
                trx = Transaction(
                    project_id=last_project.id if last_project else None,
                    client_id=client_id,
                    amount=remaining_to_allocate,
                    payment_type=payment_type,
                    notes=f"{notes.strip()} [مانده بستانکار استودیو]".strip(),
                    tracking_code=tracking_code.strip() or None,
                    paid_at=paid_at
                )
                session.add(trx)
                session.flush()
                created_transaction_ids.append(trx.id)

            session.commit()

        return created_transaction_ids

    @staticmethod
    def delete_transaction(transaction_id: int) -> bool:
        with db.get_session() as session:
            trx = session.get(Transaction, transaction_id)
            if not trx:
                return False
            
            project_id = trx.project_id
            amount_val = trx.amount

            if project_id:
                ProjectController.log_event(
                    session, project_id, "TRANSACTION_DELETED",
                    f"حذف تراکنش دریافت مبلغ {amount_val:,} تومان",
                    f"تراکنش با کد پیگیری {trx.tracking_code or '-'} حذف شد."
                )

            session.delete(trx)
            session.commit()

        return True

    @staticmethod
    def get_financial_dashboard_data(
        client_id: Optional[int] = None,
        date_range_key: str = "all",
        status_filter: str = "all",
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None
    ) -> Dict[str, Any]:
        start_dt, end_dt = FinanceController.get_date_range_bounds(date_range_key, custom_start, custom_end)

        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    joinedload(Project.client),
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks),
                    joinedload(Project.transactions).joinedload(Transaction.revision)
                )
                .order_by(Project.created_at.desc())
            )
            if client_id is not None and client_id > 0:
                stmt = stmt.where(Project.client_id == client_id)

            all_projects = session.scalars(stmt).unique().all()

        filtered_projects = []
        for p in all_projects:
            if not FinanceController.is_project_eligible_for_finance(p):
                continue

            p_date = p.delivered_at or p.created_at
            if start_dt and p_date and p_date < start_dt:
                continue
            if end_dt and p_date and p_date > end_dt:
                continue

            fin = ProjectController.get_project_financial_summary(p)
            
            if status_filter == "unsettled" and fin["remaining"] <= 0:
                continue
            elif status_filter == "settled" and not fin["is_settled"]:
                continue
            elif status_filter == "overpaid" and fin["raw_balance"] >= 0:
                continue

            filtered_projects.append((p, fin))

        total_contracts_value = sum(fin["total_fee"] for _, fin in filtered_projects)
        total_received_amount = sum(fin["total_paid"] for _, fin in filtered_projects)
        total_remaining_amount = sum(fin["remaining"] for _, fin in filtered_projects)
        unsettled_projects_count = sum(1 for _, fin in filtered_projects if fin["remaining"] > 0)
        total_projects_count = len(filtered_projects)

        all_transactions = []
        for p, fin in filtered_projects:
            for t in p.transactions:
                t_date = t.paid_at or p.created_at
                if start_dt and t_date and t_date < start_dt:
                    continue
                if end_dt and t_date and t_date > end_dt:
                    continue

                all_transactions.append({
                    "id": t.id,
                    "project_id": p.id,
                    "project_title": p.couple_names or p.title,
                    "client_name": p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو"),
                    "amount": int(t.amount or 0),
                    "tracking_code": t.tracking_code or "",
                    "payment_type": t.payment_type.value if hasattr(t.payment_type, "value") else str(t.payment_type),
                    "notes": t.notes or "-",
                    "paid_at": t.paid_at,
                    "target_name": f"({t.revision.title})" if t.revision else "(پروژه اصلی)"
                })

        all_transactions.sort(key=lambda x: x["paid_at"] or datetime.min, reverse=True)

        receivables_list = []
        for p, fin in filtered_projects:
            if fin["remaining"] > 0:
                last_trx = p.transactions[0] if p.transactions else None
                receivables_list.append({
                    "project_id": p.id,
                    "project_number": p.project_number or p.id,
                    "couple_names": p.couple_names or p.title,
                    "client_name": p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "بدون استودیو"),
                    "total_fee": fin["total_fee"],
                    "total_paid": fin["total_paid"],
                    "remaining": fin["remaining"],
                    "last_paid_at": last_trx.paid_at if last_trx else None,
                    "workflow_status_info": ProjectController.get_status_info(p),
                    "is_archived": p.is_archived
                })

        receivables_list.sort(key=lambda x: x["remaining"], reverse=True)

        studio_stats = {}
        for p, fin in filtered_projects:
            c_name = p.client.company if (p.client and p.client.company) else (p.client.full_name if p.client else "سایر / بدون استودیو")
            c_id = p.client_id or 0
            if c_id not in studio_stats:
                studio_stats[c_id] = {
                    "client_id": c_id,
                    "studio_name": c_name,
                    "projects_count": 0,
                    "total_fee": 0,
                    "total_paid": 0,
                    "remaining": 0
                }
            studio_stats[c_id]["projects_count"] += 1
            studio_stats[c_id]["total_fee"] += fin["total_fee"]
            studio_stats[c_id]["total_paid"] += fin["total_paid"]
            studio_stats[c_id]["remaining"] += fin["remaining"]

        studio_matrix = list(studio_stats.values())
        studio_matrix.sort(key=lambda x: x["remaining"], reverse=True)

        current_j_year = jdatetime.datetime.now().year
        month_names = [
            "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
            "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
        ]
        monthly_income = [{"month": name, "month_idx": i+1, "amount": 0, "count": 0} for i, name in enumerate(month_names)]
        
        for t in all_transactions:
            t_dt = t.get("paid_at")
            if t_dt:
                try:
                    j_dt = jdatetime.datetime.fromgregorian(datetime=t_dt)
                    if j_dt.year == current_j_year:
                        m_idx = j_dt.month - 1
                        if 0 <= m_idx < 12:
                            monthly_income[m_idx]["amount"] += t["amount"]
                            monthly_income[m_idx]["count"] += 1
                except Exception:
                    pass

        return {
            "summary_cards": {
                "total_contracts": total_contracts_value,
                "total_received": total_received_amount,
                "total_remaining": total_remaining_amount,
                "unsettled_count": unsettled_projects_count,
                "total_projects": total_projects_count
            },
            "transactions": all_transactions,
            "receivables": receivables_list,
            "studio_matrix": studio_matrix,
            "monthly_income": monthly_income
        }

    @staticmethod
    def get_dashboard_metrics() -> Dict[str, Any]:
        data = FinanceController.get_financial_dashboard_data()
        with db.get_session() as session:
            stmt = (
                select(Project)
                .options(
                    selectinload(Project.clips),
                    selectinload(Project.revisions).selectinload(ProjectRevision.tasks)
                )
                .where(Project.is_archived == False)
            )
            active_projects = session.scalars(stmt).unique().all()

            in_editing_projects = [
                p for p in active_projects 
                if not FinanceController.is_project_eligible_for_finance(p)
            ]

            review_count = len([
                p for p in active_projects
                if ProjectController.get_status_info(p).get("key") in ["under_review", "revision_done"]
            ])

        return {
            "total_revenue": data["summary_cards"]["total_received"],
            "active_pipeline_value": data["summary_cards"]["total_contracts"],
            "active_projects_count": len(in_editing_projects),
            "review_count": review_count,
        }