# ==================================================
# FILE: tests/test_finance.py
# ==================================================
from datetime import datetime, timezone
from database.models import Client, Project, Transaction, PaymentTypeEnum, WorkflowStatusEnum
from core.project_controller import ProjectController


def test_project_financial_summary(test_db_session):
    client = Client(full_name="استودیو دیاکو", company="دیاکو")
    test_db_session.add(client)
    test_db_session.commit()

    project = Project(
        project_number=1,
        title="پروژه سارا و علی",
        couple_names="سارا و علی",
        client_id=client.id,
        base_fee=10000000,
        total_fee=10000000,
        delivered_at=datetime.now(timezone.utc),
        workflow_status=WorkflowStatusEnum.UNDER_REVIEW
    )
    test_db_session.add(project)
    test_db_session.commit()

    # بدون واریزی
    fin = ProjectController.get_project_financial_summary(project)
    assert fin["total_fee"] == 10000000
    assert fin["total_paid"] == 0
    assert fin["remaining"] == 10000000
    assert not fin["is_settled"]

    # ثبت واریزی
    trx = Transaction(
        project_id=project.id,
        client_id=client.id,
        amount=6000000,
        payment_type=PaymentTypeEnum.STAGE_PAYMENT
    )
    test_db_session.add(trx)
    test_db_session.commit()
    test_db_session.refresh(project)

    fin_updated = ProjectController.get_project_financial_summary(project)
    assert fin_updated["total_paid"] == 6000000
    assert fin_updated["remaining"] == 4000000
    assert not fin_updated["is_settled"]