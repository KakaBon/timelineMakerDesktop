"""主窗口：只负责应用状态初始化和组合各功能模块。"""

import tkinter as tk
from datetime import datetime
from pathlib import Path

from .csv_manager import CSVManagerMixin
from .csv_document import CsvFormat
from .exporters import ExportMixin
from .legend import LegendMixin
from .search import TimelineSearchMixin
from .timeline import TimelineMixin
from .ui import UIMixin
from .utils import resource_path


class TimelineApp(
    UIMixin,
    CSVManagerMixin,
    LegendMixin,
    TimelineSearchMixin,
    TimelineMixin,
    ExportMixin,
    tk.Tk,
):
    def __init__(self):
        super().__init__()
        self.title("时间轴制作工具")

        try:
            self.iconbitmap(
                str(resource_path("assets/images/icon.ico"))
            )
        except tk.TclError:
            pass

        self.geometry("1500x900")
        self.minsize(1050, 700)

        # 数据与分类状态
        self.rows = []
        self.categories = []
        self.category_colors = {}
        self.category_vars = {}
        self.hidden_categories = set()

        # 当前时间范围
        self.view_start = datetime(2013, 1, 1)
        self.view_end = datetime(2028, 1, 1)

        # 时间轴布局参数
        self.label_column_width = 118
        self.clip_start = 126
        self.plot_start = 136
        self.right_margin = 42
        self.top_margin = 70
        self.bottom_margin = 70
        self.axis_gap = 45
        self.box_height = 46
        self.item_gap = 12
        self.lane_gap = 26

        # 画布交互与悬浮提示状态
        self.drag_start_x = None
        self.drag_start_view = None
        self.tooltip = None
        self.help_tooltip = None
        self.last_layout = None

        # 时间轴搜索状态
        self.timeline_search_matches = []
        self.timeline_search_index = -1
        self.timeline_search_query = ""
        self.selected_event_id = None

        # 当前 CSV 与导出状态
        self.current_csv_text = ""
        self.current_csv_format = CsvFormat()
        self.current_csv_name = "test-data.csv"
        self.current_csv_directory = Path.cwd()
        self.has_unexported_csv_edits = False

        # CSV 编辑区搜索状态
        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self.csv_text_search_query = ""

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close_request)
        self.load_sample()
