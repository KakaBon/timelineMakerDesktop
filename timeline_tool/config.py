"""应用级常量。"""

APP_NAME = "timelineMakerDesktop"
VERSION = "1.0.0"
AUTHOR = "KaKaBon"


from datetime import datetime

DATE_FORMAT = "%Y-%m-%d"
PALETTE = [
    "#2563eb", "#dc2626", "#059669", "#7c3aed", "#ea580c",
    "#0891b2", "#be123c", "#4d7c0f", "#9333ea", "#0f766e",
    "#b45309", "#475569", "#c026d3", "#0369a1",
]
DEFAULT_VIEW_START = datetime(2013, 1, 1)
DEFAULT_VIEW_END = datetime(2028, 1, 1)
