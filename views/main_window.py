# ==================================================
# FILE: views/main_window.py
# ==================================================
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QStackedWidget, QFrame, QLabel, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QSize
)
from PySide6.QtGui import QGuiApplication, QCloseEvent, QIcon

from config import APP_NAME, get_asset_path
from core.signals import global_signals
from core.icon_provider import IconProvider
from widgets.capsule_navbar import CapsuleNavBar

# ویوهای اصلی
from views.dashboard_view import DashboardView
from views.projects_view import ProjectsView
from views.archive_view import ArchiveView
from views.financials_view import FinancialsView
from views.audio_vault_view import AudioVaultView
from views.settings_view import SettingsView
from views.copilot_view import CopilotView
from time_tracking.widgets.time_tracking_view import TimeTrackingView


class StudioToastNotification(QFrame):
    """ویجت اعلان شناور مدرن (Toast) با انیمیشن Fade-In و تایمر محو شدن خودکار"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StudioToastFrame")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setFixedHeight(40)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setVisible(False)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(14, 0, 14, 0)
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_icon = QLabel()
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self.layout.addWidget(self.lbl_icon)

        self.lbl_text = QLabel()
        self.lbl_text.setStyleSheet("font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; background: transparent; border: none;")
        self.layout.addWidget(self.lbl_text)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(220)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)

    def show_message(self, message: str, toast_type: str = "info"):
        self.lbl_text.setText(message)

        if toast_type == "success":
            bg_color = "rgba(16, 185, 129, 0.95)"
            border_color = "#34D399"
            text_color = "#FFFFFF"
            icon_pix = IconProvider.get_pixmap("check", "#FFFFFF", size=13, stroke_width=2.5)
        elif toast_type == "warning":
            bg_color = "rgba(245, 158, 11, 0.95)"
            border_color = "#FBBF24"
            text_color = "#000000"
            icon_pix = IconProvider.get_pixmap("alert", "#000000", size=13, stroke_width=2.5)
        elif toast_type == "error":
            bg_color = "rgba(239, 68, 68, 0.95)"
            border_color = "#F87171"
            text_color = "#FFFFFF"
            icon_pix = IconProvider.get_pixmap("close", "#FFFFFF", size=13, stroke_width=2.5)
        else:  # info
            bg_color = "rgba(99, 102, 241, 0.95)"
            border_color = "#818CF8"
            text_color = "#FFFFFF"
            icon_pix = IconProvider.get_pixmap("info", "#FFFFFF", size=13, stroke_width=2.5)

        self.lbl_icon.setPixmap(icon_pix)
        self.lbl_text.setStyleSheet(f"font-family: 'Vazirmatn'; font-size: 11.5px; font-weight: 700; color: {text_color}; background: transparent; border: none;")
        self.setStyleSheet(f"""
            QFrame#StudioToastFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 20px;
            }}
        """)

        self.adjustSize()
        parent_w = self.parentWidget().width() if self.parentWidget() else 1200
        parent_h = self.parentWidget().height() if self.parentWidget() else 800
        self.move(int((parent_w - self.width()) / 2), parent_h - 75)
        self.raise_()

        self.setVisible(True)
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

        self.hide_timer.start(3200)

    def _fade_out(self):
        self.anim.stop()
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.finished.connect(self._on_fade_out_finished)
        self.anim.start()

    def _on_fade_out_finished(self):
        try:
            self.anim.finished.disconnect(self._on_fade_out_finished)
        except Exception:
            pass
        self.setVisible(False)


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
        
        icon_path = get_asset_path("assets/icons/icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path.resolve())))

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

        # کانتینر پشته‌ای صفحات
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

        # ویجت سراسری اعلان شناور
        self.toast_widget = StudioToastNotification(self.central_widget)
        global_signals.show_toast.connect(self.toast_widget.show_message)

        # اتصالات ناوبری
        global_signals.navigate_to_page.connect(self._switch_page)
        global_signals.navigate_and_focus_project.connect(self._go_to_projects_tab)

        self.capsule_nav.update_responsive_layout(self.width())

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
        if hasattr(self, "toast_widget") and self.toast_widget.isVisible():
            parent_w = self.central_widget.width()
            parent_h = self.central_widget.height()
            self.toast_widget.move(int((parent_w - self.toast_widget.width()) / 2), parent_h - 75)

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