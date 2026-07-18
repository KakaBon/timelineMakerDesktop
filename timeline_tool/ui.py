"""UIMixin：按功能拆分自原始桌面时间轴工具。"""

import tkinter as tk

from .utils import resource_path


class UIMixin:
    def _build_ui(self):
        sidebar_width = 238

        # 整个窗口明确分成两列：
        # 左列始终是工具标题 / 左侧控制栏；右列是工具栏 / 时间轴画布。
        header = tk.Frame(
            self,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d9dde5",
        )
        header.pack(side="top", fill="x")

        brand = tk.Frame(
            header,
            width=sidebar_width,
            height=54,
            bg="white",
        )
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)

        # 标题和方形 i 标作为一个整体，在左上区域内严格居中。
        brand_inner = tk.Frame(brand, bg="white")
        brand_inner.place(relx=0.5, rely=0.5, anchor="center")

        title_label = tk.Label(
            brand_inner,
            text="时间轴制作工具",
            font=("Microsoft YaHei", 11, "bold"),
            bg="white",
            fg="#172033",
        )
        title_label.grid(row=0, column=0, sticky="ns")

        # 方形 i 标本身就是唯一的悬浮感应区。
        self.help_hit_area = tk.Canvas(
            brand_inner,
            width=18,
            height=18,
            bg="white",
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        self.help_hit_area.create_rectangle(
            1, 1, 17, 17,
            outline="#526075",
            width=1,
        )
        self.help_hit_area.create_text(
            9, 9,
            text="i",
            font=("Microsoft YaHei", 8, "bold"),
            fill="#526075",
        )
        self.help_hit_area.grid(
            row=0,
            column=1,
            padx=(6, 0),
        )
        # 只使用这一个方形控件作为感应区。Enter 负责首次进入，
        # Motion 负责鼠标在方形内快速来回移动时持续确认显示；
        # 不使用轮询、延时或额外感应层。
        self.help_hit_area.bind("<Enter>", self.show_help_tooltip)
        self.help_hit_area.bind("<Motion>", self.show_help_tooltip)
        self.help_hit_area.bind("<Leave>", self.hide_help_tooltip)

        # 右侧工具栏从左侧栏边界之后才开始。
        toolbar_area = tk.Frame(header, bg="white")
        toolbar_area.pack(side="left", fill="x", expand=True)

        toolbar = tk.Frame(toolbar_area, bg="white")
        toolbar.pack(side="left", padx=(10, 6), pady=7)

        self._button(
            toolbar,
            "导入 CSV",
            self.import_csv,
            primary=True,
        ).pack(side="left", padx=3)
        self._button(
            toolbar,
            "载入示例",
            self.load_sample,
        ).pack(side="left", padx=3)
        self._button(
            toolbar,
            "导出 CSV",
            self.export_csv,
        ).pack(side="left", padx=3)
        self._button(
            toolbar,
            "重置视图",
            self.reset_view,
        ).pack(side="left", padx=3)
        self._button(
            toolbar,
            "导出图片",
            self.export_image,
        ).pack(side="left", padx=3)

        search_area = tk.Frame(toolbar_area, bg="white")
        search_area.pack(side="left", padx=(8, 4), pady=7)

        self.timeline_search_var = tk.StringVar(value="")
        timeline_entry_box = tk.Frame(
            search_area,
            bg="white",
            relief="sunken",
            bd=1,
        )
        timeline_entry_box.pack(side="left")

        self.timeline_search_entry = tk.Entry(
            timeline_entry_box,
            textvariable=self.timeline_search_var,
            width=19,
            font=("Consolas", 10),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.timeline_search_entry.pack(
            side="left",
            padx=(3, 0),
        )
        self.timeline_search_entry.bind(
            "<Return>",
            lambda _event: self.execute_timeline_search(),
        )

        self.timeline_search_clear_button = tk.Button(
            timeline_entry_box,
            text="×",
            command=self.clear_timeline_search,
            font=("Microsoft YaHei", 8),
            relief="flat",
            padx=3,
            pady=0,
            bg="white",
            fg="#64748b",
            activebackground="#f3f4f6",
            activeforeground="#1f2937",
            bd=0,
            highlightthickness=0,
        )
        self.timeline_search_clear_button.pack(
            side="right",
            padx=(1, 1),
        )

        # 顶部查找按钮与所有其它按钮使用同一种可见背景、边框和字体。
        self._button(
            search_area,
            "查找",
            self.execute_timeline_search,
        ).pack(side="left", padx=(4, 2))
        self._compact_button(
            search_area,
            "↑",
            self.show_previous_timeline_search_match,
        ).pack(side="left", padx=1)
        self._compact_button(
            search_area,
            "↓",
            self.show_next_timeline_search_match,
        ).pack(side="left", padx=1)

        self.timeline_search_counter_var = tk.StringVar(value="0/0")
        tk.Label(
            search_area,
            textvariable=self.timeline_search_counter_var,
            width=4,
            font=("Microsoft YaHei", 7),
            bg="white",
            fg="#64748b",
        ).pack(side="left", padx=(3, 0))

        self.status_var = tk.StringVar(value="")
        tk.Label(
            toolbar_area,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 8),
            bg="white",
            fg="#687386",
        ).pack(side="right", padx=(8, 14))

        body = tk.Frame(self, bg="#eef1f5")
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(
            body,
            width=sidebar_width,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # ── 分类 ─────────────────────────────────────────────
        self._panel_title(sidebar, "分类").pack(
            anchor="w",
            padx=12,
            pady=(12, 6),
        )

        # 分类区只保留约 4～5 行的固定视口。
        # 内部控件采用 grid，因此必须关闭 grid_propagate；
        # 只关闭 pack_propagate 并不能阻止内部分类列表把容器撑高。
        legend_container = tk.Frame(
            sidebar,
            bg="#f7f8fa",
            height=137,
            highlightthickness=1,
            highlightbackground="#c7ceda",
        )
        legend_container.pack(fill="x", padx=12)
        legend_container.pack_propagate(False)
        legend_container.grid_propagate(False)

        self.legend_canvas = tk.Canvas(
            legend_container,
            bg="#f7f8fa",
            highlightthickness=0,
            bd=0,
        )
        self.legend_scrollbar = tk.Scrollbar(
            legend_container,
            orient="vertical",
            command=self.on_legend_scrollbar,
        )
        self.legend_canvas.configure(
            yscrollcommand=self.legend_scrollbar.set,
        )

        # 使用 grid 固定分配滚动条列，确保滚动条始终可见。
        self.legend_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.legend_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        legend_container.rowconfigure(0, weight=1)
        legend_container.columnconfigure(0, weight=1)

        self.legend_frame = tk.Frame(
            self.legend_canvas,
            bg="#f7f8fa",
        )
        self.legend_window = self.legend_canvas.create_window(
            (0, 0),
            window=self.legend_frame,
            anchor="nw",
        )

        self.legend_frame.bind(
            "<Configure>",
            self.update_legend_scrollregion,
        )
        self.legend_canvas.bind(
            "<Configure>",
            self.resize_legend_window,
        )
        # 分类区滚轮使用唯一的全窗口分派：仅当鼠标位于分类视口内时接管。
        # 这样条目、复选框和空白处的滚动行为完全一致，主时间轴不受影响。
        self.bind_all(
            "<MouseWheel>",
            self.on_global_mousewheel,
            add="+",
        )
        self.bind_all(
            "<Button-4>",
            self.on_global_mousewheel,
            add="+",
        )
        self.bind_all(
            "<Button-5>",
            self.on_global_mousewheel,
            add="+",
        )

        # ── 当前视图 ─────────────────────────────────────────
        self._panel_title(sidebar, "当前视图").pack(
            anchor="w",
            padx=12,
            pady=(12, 6),
        )

        tk.Label(
            sidebar,
            text="起始日期",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(anchor="w", padx=14)

        self.start_entry = tk.Entry(
            sidebar,
            font=("Consolas", 10),
        )
        self.start_entry.pack(
            fill="x",
            padx=12,
            pady=(3, 7),
        )

        tk.Label(
            sidebar,
            text="结束日期",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(anchor="w", padx=14)

        self.end_entry = tk.Entry(
            sidebar,
            font=("Consolas", 10),
        )
        self.end_entry.pack(
            fill="x",
            padx=12,
            pady=(3, 7),
        )

        self._button(
            sidebar,
            "应用范围",
            self.apply_range,
        ).pack(fill="x", padx=12)

        # ── CSV 编辑器 ───────────────────────────────────────
        self._panel_title(sidebar, "CSV 编辑器").pack(
            anchor="w",
            padx=12,
            pady=(12, 5),
        )

        tk.Label(
            sidebar,
            text="查找文本",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(anchor="w", padx=14)

        csv_find_box = tk.Frame(
            sidebar,
            bg="white",
            relief="sunken",
            bd=1,
        )
        csv_find_box.pack(
            fill="x",
            padx=12,
            pady=(3, 4),
        )

        self.csv_text_search_var = tk.StringVar(value="")
        self.csv_text_search_entry = tk.Entry(
            csv_find_box,
            textvariable=self.csv_text_search_var,
            font=("Consolas", 10),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.csv_text_search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(3, 0),
        )
        self.csv_text_search_entry.bind(
            "<Return>",
            lambda _event: self.execute_csv_text_search(),
        )

        tk.Button(
            csv_find_box,
            text="×",
            command=self.clear_csv_text_search,
            font=("Microsoft YaHei", 8),
            relief="flat",
            padx=3,
            pady=0,
            bg="white",
            fg="#64748b",
            activebackground="#f3f4f6",
            activeforeground="#1f2937",
            bd=0,
            highlightthickness=0,
        ).pack(side="right", padx=(1, 1))

        find_nav_row = tk.Frame(
            sidebar,
            bg="#f7f8fa",
        )
        find_nav_row.pack(
            fill="x",
            padx=12,
            pady=(0, 5),
        )

        self._button(
            find_nav_row,
            "查找",
            self.execute_csv_text_search,
        ).pack(side="left")

        self._compact_button(
            find_nav_row,
            "↑",
            self.show_previous_csv_text_search_match,
        ).pack(side="left", padx=(4, 1))

        self._compact_button(
            find_nav_row,
            "↓",
            self.show_next_csv_text_search_match,
        ).pack(side="left", padx=1)

        self.csv_text_search_counter_var = tk.StringVar(value="0/0")
        tk.Label(
            find_nav_row,
            textvariable=self.csv_text_search_counter_var,
            width=4,
            font=("Microsoft YaHei", 7),
            bg="#f7f8fa",
            fg="#64748b",
        ).pack(side="left", padx=(3, 0))

        tk.Label(
            sidebar,
            text="替换为",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(anchor="w", padx=14)

        csv_replace_box = tk.Frame(
            sidebar,
            bg="white",
            relief="sunken",
            bd=1,
        )
        csv_replace_box.pack(
            fill="x",
            padx=12,
            pady=(3, 4),
        )

        self.csv_text_replace_var = tk.StringVar(value="")
        self.csv_text_replace_entry = tk.Entry(
            csv_replace_box,
            textvariable=self.csv_text_replace_var,
            font=("Consolas", 10),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.csv_text_replace_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(3, 0),
        )
        self.csv_text_replace_entry.bind(
            "<Return>",
            lambda _event: self.replace_current_csv_text_match(),
        )

        tk.Button(
            csv_replace_box,
            text="×",
            command=self.clear_csv_text_replacement,
            font=("Microsoft YaHei", 8),
            relief="flat",
            padx=3,
            pady=0,
            bg="white",
            fg="#64748b",
            activebackground="#f3f4f6",
            activeforeground="#1f2937",
            bd=0,
            highlightthickness=0,
        ).pack(side="right", padx=(1, 1))

        csv_action_row = tk.Frame(
            sidebar,
            bg="#f7f8fa",
        )
        csv_action_row.pack(
            fill="x",
            padx=12,
            pady=(0, 5),
        )

        self._button(
            csv_action_row,
            "替换",
            self.replace_current_csv_text_match,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 2),
        )

        self._button(
            csv_action_row,
            "全部替换",
            self.replace_all_csv_text_matches,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(2, 0),
        )

        self._button(
            sidebar,
            "应用修改",
            self.apply_csv_editor_changes,
            primary=True,
        ).pack(
            fill="x",
            padx=12,
            pady=(0, 6),
        )

        # CSV 正文编辑区有自己的专属垂直滚动条。
        csv_editor_frame = tk.Frame(
            sidebar,
            bg="#f7f8fa",
        )
        csv_editor_frame.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(0, 12),
        )

        self.csv_editor = tk.Text(
            csv_editor_frame,
            height=18,
            wrap="none",
            undo=True,
            exportselection=False,
            font=("Consolas", 10),
            bg="white",
            fg="#263247",
            insertbackground="#263247",
            relief="sunken",
            bd=1,
            highlightthickness=0,
        )
        self.csv_editor_scrollbar = tk.Scrollbar(
            csv_editor_frame,
            orient="vertical",
            command=self.csv_editor.yview,
        )
        self.csv_editor.configure(
            yscrollcommand=self.csv_editor_scrollbar.set,
        )

        self.csv_editor.pack(
            side="left",
            fill="both",
            expand=True,
        )
        self.csv_editor_scrollbar.pack(
            side="right",
            fill="y",
        )

        # 右下区域完整留给时间轴画布。
        canvas_area = tk.Frame(
            body,
            bg="#eef1f5",
        )
        canvas_area.pack(
            side="left",
            fill="both",
            expand=True,
            padx=12,
            pady=14,
        )

        self.canvas = tk.Canvas(
            canvas_area,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d8dde6",
            yscrollincrement=1,
        )
        self.vbar = tk.Scrollbar(
            canvas_area,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(
            yscrollcommand=self.vbar.set,
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self.vbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        canvas_area.rowconfigure(0, weight=1)
        canvas_area.columnconfigure(0, weight=1)

        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Configure>", lambda _e: self.render())

    def show_help_tooltip(self, _event=None):
        if self.help_tooltip is not None:
            return

        self.help_tooltip = tk.Toplevel(self)
        self.help_tooltip.overrideredirect(True)
        self.help_tooltip.attributes("-topmost", True)

        content = (
            "单轴双侧 · 分类着色 · 自动避让 · CSV 导入与编辑\n\n"
            "左键拖动：左右移动\n"
            "Shift + 滚轮：快速左右移动\n"
            "Ctrl + 滚轮：横向缩放\n"
            "滚轮：快速上下滚动\n"
            "点击分类：显示或隐藏\n"
            "悬停事件：显示备注"
        )

        label = tk.Label(
            self.help_tooltip,
            text=content,
            justify="left",
            bg="white",
            fg="#293247",
            relief="solid",
            borderwidth=1,
            padx=12,
            pady=10,
            font=("Microsoft YaHei", 9),
        )
        label.pack()

        self.update_idletasks()
        x = self.help_hit_area.winfo_rootx()
        y = (
            self.help_hit_area.winfo_rooty()
            + self.help_hit_area.winfo_height()
            + 3
        )
        self.help_tooltip.geometry(f"+{x}+{y}")

    def hide_help_tooltip(self, _event=None):
        if self.help_tooltip is not None:
            try:
                self.help_tooltip.destroy()
            except tk.TclError:
                pass
            self.help_tooltip = None

    def _button(self, parent, text, command, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", 9),
            relief="raised",
            cursor="hand2",
            padx=8,
            pady=4,
            bg="#2968e8" if primary else "#ffffff",
            fg="#ffffff" if primary else "#253044",
            activebackground="#1f57c5" if primary else "#edf2f7",
            activeforeground="#ffffff" if primary else "#253044",
            bd=1,
            highlightthickness=0,
        )

    def _compact_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", 9),
            relief="raised",
            cursor="hand2",
            padx=4,
            pady=4,
            bg="#ffffff",
            fg="#253044",
            activebackground="#edf2f7",
            activeforeground="#253044",
            bd=1,
            highlightthickness=0,
        )

    def _panel_title(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei", 11, "bold"),
            bg="#f7f8fa",
            fg="#172033",
        )
