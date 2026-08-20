# ==================================================
# FILE: database/db_manager.py
# ==================================================
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base
from config import DB_PATH


class DatabaseManager:
    def __init__(self):
        self.db_file = Path(DB_PATH)
        self.db_file.parent.mkdir(parents=True, exist_ok=True)
        self.database_url = f"sqlite:///{self.db_file.absolute()}"
        
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            echo=False
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        self.init_db()

    def init_db(self):
        try:
            import time_tracking.models  # noqa: F401
        except Exception:
            pass

        Base.metadata.create_all(bind=self.engine)
        self._run_auto_migrations()

    def _run_auto_migrations(self):
        with self.engine.begin() as conn:
            # ---------------- جدول projects ----------------
            try:
                result = conn.execute(text("PRAGMA table_info(projects)")).fetchall()
                columns = [row[1] for row in result]
                
                if "project_number" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN project_number INTEGER"))
                
                unassigned = conn.execute(
                    text("SELECT id FROM projects WHERE project_number IS NULL OR project_number = 0 ORDER BY created_at ASC, id ASC")
                ).fetchall()

                if unassigned:
                    max_num_res = conn.execute(text("SELECT MAX(project_number) FROM projects")).scalar()
                    current_seq = max_num_res if (max_num_res and max_num_res > 0) else 0

                    for row in unassigned:
                        current_seq += 1
                        conn.execute(
                            text("UPDATE projects SET project_number = :p_num WHERE id = :p_id"),
                            {"p_num": current_seq, "p_id": row[0]}
                        )

                if "base_fee" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN base_fee BIGINT DEFAULT 0"))
                if "total_fee" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN total_fee BIGINT DEFAULT 0"))
                if "is_archived" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN is_archived BOOLEAN DEFAULT 0"))
                if "workflow_status" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN workflow_status VARCHAR(50) DEFAULT 'editing'"))
                if "delivered_at" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN delivered_at DATETIME"))
                if "nle_project_path" not in columns:
                    conn.execute(text("ALTER TABLE projects ADD COLUMN nle_project_path VARCHAR(500)"))

                conn.execute(text("UPDATE projects SET base_fee = total_fee WHERE (base_fee IS NULL OR base_fee = 0) AND total_fee > 0"))
                conn.execute(text("UPDATE projects SET workflow_status = 'editing' WHERE workflow_status IS NULL OR workflow_status = ''"))
            except Exception as e:
                print(f"Migration Notice (projects): {e}")

            # ---------------- جدول clients ----------------
            try:
                result = conn.execute(text("PRAGMA table_info(clients)")).fetchall()
                columns = [row[1] for row in result]
                if "instagram" not in columns:
                    conn.execute(text("ALTER TABLE clients ADD COLUMN instagram VARCHAR(100)"))
                if "notes" not in columns:
                    conn.execute(text("ALTER TABLE clients ADD COLUMN notes TEXT"))
                if "company" not in columns:
                    conn.execute(text("ALTER TABLE clients ADD COLUMN company VARCHAR(150)"))
                if "phone" not in columns:
                    conn.execute(text("ALTER TABLE clients ADD COLUMN phone VARCHAR(50)"))
            except Exception as e:
                print(f"Migration Notice (clients): {e}")

            # ---------------- جدول transactions ----------------
            try:
                result = conn.execute(text("PRAGMA table_info(transactions)")).fetchall()
                columns = [row[1] for row in result]
                if "revision_id" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN revision_id INTEGER REFERENCES project_revisions(id)"))
                if "payment_type" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN payment_type VARCHAR(50) DEFAULT 'stage_payment'"))
            except Exception as e:
                print(f"Migration Notice (transactions): {e}")

            # ---------------- جدول project_revisions ----------------
            try:
                result = conn.execute(text("PRAGMA table_info(project_revisions)")).fetchall()
                columns = [row[1] for row in result]
                if "extra_fee" not in columns:
                    conn.execute(text("ALTER TABLE project_revisions ADD COLUMN extra_fee BIGINT DEFAULT 0"))
            except Exception as e:
                print(f"Migration Notice (project_revisions): {e}")

            # ---------------- جدول work_sessions ----------------
            try:
                result = conn.execute(text("PRAGMA table_info(work_sessions)")).fetchall()
                if result:
                    columns = [row[1] for row in result]
                    if "active_duration" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN active_duration INTEGER DEFAULT 0"))
                    if "paused_duration" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN paused_duration INTEGER DEFAULT 0"))
                    if "idle_duration" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN idle_duration INTEGER DEFAULT 0"))
                    if "total_duration" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN total_duration INTEGER DEFAULT 0"))
                    if "stage_name" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN stage_name VARCHAR(50) DEFAULT 'Editing'"))
                    if "status" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
                    if "note" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN note TEXT"))
                    if "is_manual" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN is_manual BOOLEAN DEFAULT 0"))
                    if "is_clip_completed" not in columns:
                        conn.execute(text("ALTER TABLE work_sessions ADD COLUMN is_clip_completed BOOLEAN DEFAULT 0"))
            except Exception as e:
                print(f"Migration Notice (work_sessions): {e}")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        session: Session = self.SessionLocal()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_next_project_number(self, session: Session) -> int:
        max_num = session.execute(text("SELECT MAX(project_number) FROM projects")).scalar()
        if max_num is None or max_num <= 0:
            return 1
        return int(max_num) + 1


db = DatabaseManager()