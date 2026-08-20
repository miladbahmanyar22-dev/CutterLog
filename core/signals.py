# ==================================================
# FILE: core/signals.py
# ==================================================
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    # --- Pipeline & Project Signals ---
    project_created = Signal(dict)
    project_updated = Signal(int)       
    stage_changed = Signal(int, str)    
    project_deleted = Signal(int)       

    # --- Clip Status Signals ---
    clip_status_toggled = Signal(int, int)  # (project_id, clip_id)

    # --- Archive & Revision Signals ---
    project_archived = Signal(int)      
    project_unarchived = Signal(int)    
    revision_added = Signal(int)        # (project_id)
    revision_updated = Signal(int, int) # (project_id, revision_id)
    revision_task_toggled = Signal(int, int, int)  # (project_id, revision_id, task_id)
    revision_deleted = Signal(int, int) # (project_id, revision_id)

    # --- Financial & Ledger Signals ---
    transaction_recorded = Signal(int)  
    client_balance_updated = Signal(int)

    # --- Time Tracking & Monitoring Signals ---
    session_started = Signal(int)       # (session_id)
    session_paused = Signal(int)        # (session_id)
    session_resumed = Signal(int)       # (session_id)
    session_ended = Signal(int)         # (session_id)
    timer_tick = Signal(dict)           # (state_snapshot)
    system_activity_updated = Signal(dict)  # (metrics_dict)

    # --- Settings Signals ---
    settings_updated = Signal()

    # --- UI / Navigation Signals ---
    navigate_to_page = Signal(int)      
    navigate_and_focus_project = Signal(int) 
    show_toast = Signal(str, str)       


global_signals = SignalBus()