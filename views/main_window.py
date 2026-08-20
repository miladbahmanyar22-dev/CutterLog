# ==================================================
# FILE: views/main_window.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget, QFrame, QLabel
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QCloseEvent

from config import APP_NAME
from core.signals import global_signals
from core.settings_manager import SettingsManager
from widgets.capsule_navbar import CapsuleNavBar
from widgets.welcome_setup_dialog import WelcomeSetupDialog

# ویوهای اصلی
from views.dashboard_view import DashboardView
from views.projects_view import ProjectsView
from views.archive_view import ArchiveView
from views.financials_view import FinancialsView
from views.audio_vault_view import AudioVaultView
from views.settings_view import SettingsView
from views.copilot_view import CopilotView
from time_tracking.widgets.time_tracking_view import TimeTrackingView


class HeaderActiveSessionIndicator(QFrame):
    """نشانگر وضعیت سشن زنده در نوار بالای برنامه"""
    def __init__(self, on_click_callback, parent=None):
        super().__init__(parent)
        self.on_click_callback = on_click_callback
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dot_rec = QLabel("●")
        self.dot_rec.setStyleSheet("color: #10B981; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(self.dot_rec)

        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("""
            font-family: 'Segoe UI', monospace;
            font-size: 11.5px;
            font-weight: 800;
            color: #F8FAFC;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.lbl_time)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(16, 185, 129, 0.12);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 6px;
            }
            QFrame:hover {
                background-color: rgba(16, 185, 129, 0.22);
                border-color: #10B981;
            }
        """)

        global_signals.timer_tick.connect(self._on_tick)
        global_signals.session_started.connect(lambda _: self._set_active(True))
        global_signals.session_ended.connect(lambda _: self._set_active(False))
        global_signals.session_paused.connect(self._on_pause)
        global_signals.session_resumed.connect(self._on_resume)

    def _set_active(self, active: bool):
        self.setVisible(active)
        if active:
            self.dot_rec.setStyleSheet("color: #10B981; font-size: 10px; background: transparent; border: none;")
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(16, 185, 129, 0.12);
                    border: 1px solid rgba(16, 185, 129, 0.35);
                    border-radius: 6px;
                }
                QFrame:hover {
                    background-color: rgba(16, 185, 129, 0.22);
                    border-color: #10B981;
                }
            """)

    def _on_pause(self, _):
        self.dot_rec.setStyleSheet("color: #F59E0B; font-size: 10px; background: transparent; border: none;")
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(245, 158, 11, 0.12);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 6px;
            }
        """)

    def _on_resume(self, _):
        self._set_active(True)

    def _on_tick(self, snap: dict):
        if not self.isVisible():
            self.setVisible(True)
        sec = snap.get("active_seconds", 0)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            self.on_click_callback()
            return
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        
        self.update_window_title(is_active=False, is_paused=False)

        screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None
        
        if screen_geo:
            target_w = min(1400, int(screen_geo.width() * 0.95))
            target_h = min(900, int(screen_geo.height() * 0.92))
            self.resize(target_w, target_h)
        else:
            self.resize(1280, 800)
            
        self.setMinimumSize(860, 580)
        self.init_ui()
        self._connect_title_signals()
        QTimer.singleShot(250, self._check_first_run)

    def update_window_title(self, is_active: bool = False, is_paused: bool = False):
        base = f"{APP_NAME} Pro"
        if is_active and not is_paused:
            self.setWindowTitle(f"{base} - Active")
        elif is_paused:
            self.setWindowTitle(f"{base} - Paused")
        else:
            self.setWindowTitle(f"{base} - Standby")

    def _connect_title_signals(self):
        global_signals.session_started.connect(lambda _: self.update_window_title(is_active=True, is_paused=False))
        global_signals.session_resumed.connect(lambda _: self.update_window_title(is_active=True, is_paused=False))
        global_signals.session_paused.connect(lambda _: self.update_window_title(is_active=True, is_paused=True))
        global_signals.session_ended.connect(lambda _: self.update_window_title(is_active=False, is_paused=False))

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # نوار بالای برنامه
        top_header = self._build_top_header()
        main_layout.addWidget(top_header)

        # کانتینر پشته‌ای صفحات ۸ گانه
        self.pages_stack = QStackedWidget()
        self.pages_stack.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.dashboard_view = DashboardView()
        self.projects_view = ProjectsView()
        self.archive_view = ArchiveView()
        self.financials_view = FinancialsView()
        self.audio_vault_view = AudioVaultView()
        self.settings_view = SettingsView()
        self.time_tracking_view = TimeTrackingView()
        self.copilot_view = CopilotView()

        self.pages_stack.addWidget(self.dashboard_view)        # 0
        self.pages_stack.addWidget(self.projects_view)         # 1
        self.pages_stack.addWidget(self.archive_view)          # 2
        self.pages_stack.addWidget(self.financials_view)       # 3
        self.pages_stack.addWidget(self.audio_vault_view)      # 4
        self.pages_stack.addWidget(self.settings_view)         # 5
        self.pages_stack.addWidget(self.time_tracking_view)    # 6
        self.pages_stack.addWidget(self.copilot_view)          # 7

        main_layout.addWidget(self.pages_stack, stretch=1)

        # اتصالات ناوبری
        global_signals.navigate_to_page.connect(self._switch_page)
        global_signals.navigate_and_focus_project.connect(self._go_to_projects_tab)

        self.capsule_nav.update_responsive_layout(self.width())

    def _check_first_run(self):
        settings = SettingsManager.load_settings()
        if settings.get("is_first_run", True):
            wizard = WelcomeSetupDialog(self)
            wizard.exec()

    def _build_top_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("TopHeaderFrame")
        header.setFixedHeight(50)
        header.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        header.setStyleSheet("""
            QFrame#TopHeaderFrame {
                background-color: #0B0F17;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(10)

        # نشانگر زمان جلسه فعال
        self.header_timer_badge = HeaderActiveSessionIndicator(
            on_click_callback=lambda: self._switch_page(6), 
            parent=self
        )
        layout.addWidget(self.header_timer_badge)

        layout.addStretch(1)

        # نوار ناوبری کپسولی
        self.capsule_nav = CapsuleNavBar(parent=self)
        self.capsule_nav.page_selected.connect(self._switch_page)
        layout.addWidget(self.capsule_nav)

        layout.addStretch(1)
        return header

    def _switch_page(self, index: int):
        if 0 <= index < self.pages_stack.count():
            if hasattr(self, "audio_vault_view") and self.pages_stack.currentWidget() == self.audio_vault_view and index != 4:
                if hasattr(self.audio_vault_view, "player"):
                    self.audio_vault_view.player.stop()

            self.pages_stack.setCurrentIndex(index)
            self.capsule_nav.select_index(index, emit_signal=False)

            current_widget = self.pages_stack.currentWidget()
            if hasattr(current_widget, "refresh_dashboard"):
                current_widget.refresh_dashboard()
            elif hasattr(current_widget, "refresh_data"):
                current_widget.refresh_data()
            elif hasattr(current_widget, "refresh_projects"):
                current_widget.refresh_projects()
            elif hasattr(current_widget, "refresh_archive"):
                current_widget.refresh_archive()

    def _go_to_projects_tab(self, project_id: int):
        self._switch_page(1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "capsule_nav"):
            self.capsule_nav.update_responsive_layout(self.width())

    def closeEvent(self, event: QCloseEvent):
        try:
            from time_tracking.timer_engine import TimeTrackingEngine
            engine = TimeTrackingEngine.instance()
            if engine.is_running:
                engine._persist_active_session()
            if hasattr(engine, "monitor_thread") and engine.monitor_thread.isRunning():
                engine.monitor_thread.stop()
        except Exception as e:
            print(f"Close cleanup notice: {e}")

        super().closeEvent(event)