# ==================================================
# FILE: tests/test_projects.py
# ==================================================
from database.models import Client, Project, ProjectClipItem
from core.project_controller import ProjectController


def test_project_progress_calculation(test_db_session):
    client = Client(full_name="استودیو آوا", company="آوا")
    test_db_session.add(client)
    test_db_session.commit()

    project = Project(
        project_number=2,
        title="پروژه مریم و رضا",
        couple_names="مریم و رضا",
        client_id=client.id,
        base_fee=12000000,
        total_fee=12000000
    )
    test_db_session.add(project)
    test_db_session.flush()

    clip1 = ProjectClipItem(project_id=project.id, clip_name="Long Cut", is_completed=True)
    clip2 = ProjectClipItem(project_id=project.id, clip_name="Teaser", is_completed=False)
    test_db_session.add_all([clip1, clip2])
    test_db_session.commit()
    test_db_session.refresh(project)

    completed, total, pct = ProjectController.calculate_project_progress(project)
    assert completed == 1
    assert total == 2
    assert pct == 50