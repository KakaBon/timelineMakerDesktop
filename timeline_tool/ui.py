"""UIMixin：按功能拆分自原始桌面时间轴工具。"""

import tkinter as tk

from .utils import resource_path


class UIMixin:
    def _build_ui(self):
        """建立三横区界面骨架，并保留 v1.0.1 的全部现有功能。"""
        self.configure(bg="#eef1f5")
        self.grid_rowconfigure(0, weight=0)
        # 第二横区保持紧凑，主要空间留给时间轴。
        self.grid_rowconfigure(1, weight=0, minsize=250)
        self.grid_rowconfigure(2, weight=1, minsize=440)
        self.grid_columnconfigure(0, weight=1)

        # ── 第一横区：标题、全局操作预留、信息记录区 ─────────────
        header = tk.Frame(
            self,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d9dde5",
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(2, weight=1)

        brand = tk.Frame(header, bg="white")
        brand.grid(row=0, column=0, sticky="w", padx=(16, 12), pady=9)

        title_label = tk.Label(
            brand,
            text="时间轴制作工具",
            font=("Microsoft YaHei", 11, "bold"),
            bg="white",
            fg="#172033",
        )
        title_label.pack(side="left")

        # 工具标题旁的 i 标与三个分区使用完全相同的 Label 组件和 Tooltip 逻辑。
        self.help_hit_area = self._panel_info_icon(
            brand,
            "工具标题-i标tooltip占位文本",
            bg="white",
        )
        self.help_hit_area.pack(side="left", padx=(7, 0))

        global_actions = tk.Frame(header, bg="white")
        global_actions.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=7)
        self.undo_button = self._button(global_actions, "撤销", lambda: None)
        self.undo_button.configure(state="disabled")
        self.undo_button.pack(side="left", padx=(0, 3))
        self.redo_button = self._button(global_actions, "重做", lambda: None)
        self.redo_button.configure(state="disabled")
        self.redo_button.pack(side="left", padx=3)

        info_shell = tk.Frame(header, bg="white")
        info_shell.grid(row=0, column=2, sticky="nsew", padx=(0, 14), pady=6)
        info_shell.grid_rowconfigure(1, weight=1)
        info_shell.grid_columnconfigure(0, weight=1)
        tk.Label(
            info_shell,
            text="信息记录",
            font=("Microsoft YaHei", 8, "bold"),
            bg="white",
            fg="#526075",
        ).grid(row=0, column=0, sticky="w")

        info_body = tk.Frame(info_shell, bg="white")
        info_body.grid(row=1, column=0, sticky="ew")
        info_body.grid_columnconfigure(0, weight=1)
        self.info_log = tk.Text(
            info_body,
            height=3,
            wrap="word",
            state="disabled",
            font=("Microsoft YaHei", 8),
            bg="#f8fafc",
            fg="#526075",
            relief="sunken",
            bd=1,
            highlightthickness=0,
        )
        self.info_log.grid(row=0, column=0, sticky="ew")
        self.info_log_scrollbar = tk.Scrollbar(
            info_body, orient="vertical", command=self.info_log.yview
        )
        self.info_log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.info_log.configure(yscrollcommand=self.info_log_scrollbar.set)

        self.status_var = tk.StringVar(value="")
        self.status_var.trace_add("write", self._on_status_changed)

        # ── 第二横区：分类区与 CSV 编辑区 ─────────────────────
        workspace = tk.PanedWindow(
            self,
            orient="horizontal",
            bg="#eef1f5",
            sashwidth=7,
            sashrelief="flat",
            bd=0,
        )
        workspace.configure(height=260)
        workspace.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))

        # 分类区放左侧，CSV 区放右侧；初始比例约 4.5 : 5.5。
        category_panel = tk.Frame(
            workspace,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        csv_panel = tk.Frame(
            workspace,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        workspace.add(category_panel, minsize=380, stretch="always")
        workspace.add(csv_panel, minsize=460, stretch="always")

        # 分类区：标题、操作与查找统一放在同一行，按钮按文字自然宽度排列。
        category_toolbar = tk.Frame(category_panel, bg="#f7f8fa")
        category_toolbar.pack(fill="x", padx=10, pady=(7, 4))

        self._panel_title(category_toolbar, "分类").pack(side="left")
        self._panel_info_icon(
            category_toolbar,
            "分类区-i标tooltip占位文本",
        ).pack(side="left", padx=(5, 8))

        self._small_button(category_toolbar, "新建分类", lambda: None).pack(
            side="left", padx=(0, 2)
        )
        self._small_button(category_toolbar, "删除", lambda: None).pack(
            side="left", padx=2
        )
        self._small_button(category_toolbar, "事件迁移", lambda: None).pack(
            side="left", padx=2
        )

        self.category_search_var = tk.StringVar(value="")
        category_search_box = self._entry_box(
            category_toolbar,
            self.category_search_var,
            width=12,
            clear_command=lambda: self.category_search_var.set(""),
        )
        category_search_box.pack(side="left", padx=(8, 2))
        category_search_box.entry.configure(state="disabled")
        category_find_button = self._small_button(category_toolbar, "查找", lambda: None)
        category_find_button.configure(state="disabled")
        category_find_button.pack(side="left")

        legend_container = tk.Frame(
            category_panel,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#c7ceda",
        )
        legend_container.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        legend_container.grid_rowconfigure(0, weight=1)
        legend_container.grid_columnconfigure(0, weight=1)

        self.legend_canvas = tk.Canvas(
            legend_container, bg="#f7f8fa", highlightthickness=0, bd=0
        )
        self.legend_scrollbar = tk.Scrollbar(
            legend_container, orient="vertical", command=self.on_legend_scrollbar
        )
        self.legend_canvas.configure(yscrollcommand=self.legend_scrollbar.set)
        self.legend_canvas.grid(row=0, column=0, sticky="nsew")
        self.legend_scrollbar.grid(row=0, column=1, sticky="ns")

        self.legend_frame = tk.Frame(self.legend_canvas, bg="#f7f8fa")
        self.legend_window = self.legend_canvas.create_window(
            (0, 0), window=self.legend_frame, anchor="nw"
        )
        self.legend_frame.bind("<Configure>", self.update_legend_scrollregion)
        self.legend_canvas.bind("<Configure>", self.resize_legend_window)

        # CSV 区：所有操作保持完整名称，并按“输入框在左、操作按钮在右”排列。
        csv_toolbar = tk.Frame(csv_panel, bg="#f7f8fa")
        csv_toolbar.pack(fill="x", padx=8, pady=(7, 4))

        self._panel_title(csv_toolbar, "CSV 编辑器").pack(side="left")
        self._panel_info_icon(
            csv_toolbar,
            "CSV区-i标tooltip占位文本",
        ).pack(side="left", padx=(5, 7))

        self._small_button(csv_toolbar, "导入 CSV", self.import_csv, primary=True).pack(
            side="left", padx=(0, 2)
        )
        self._small_button(csv_toolbar, "载入示例", self.load_sample).pack(
            side="left", padx=2
        )
        self._small_button(csv_toolbar, "导出 CSV", self.export_csv).pack(
            side="left", padx=(2, 7)
        )

        self.csv_text_search_var = tk.StringVar(value="")
        csv_find_box = self._entry_box(
            csv_toolbar,
            self.csv_text_search_var,
            width=12,
            clear_command=self.clear_csv_text_search,
        )
        csv_find_box.pack(side="left", padx=(0, 2))
        self.csv_text_search_entry = csv_find_box.entry
        self.csv_text_search_entry.bind(
            "<Return>", lambda _event: self.execute_csv_text_search()
        )
        self._small_button(csv_toolbar, "查找", self.execute_csv_text_search).pack(
            side="left", padx=1
        )
        self._compact_button(
            csv_toolbar, "↑", self.show_previous_csv_text_search_match
        ).pack(side="left", padx=1)
        self._compact_button(
            csv_toolbar, "↓", self.show_next_csv_text_search_match
        ).pack(side="left", padx=1)
        self.csv_text_search_counter_var = tk.StringVar(value="0/0")
        tk.Label(
            csv_toolbar,
            textvariable=self.csv_text_search_counter_var,
            width=4,
            font=("Microsoft YaHei", 7),
            bg="#f7f8fa",
            fg="#64748b",
        ).pack(side="left", padx=(1, 6))

        self.csv_text_replace_var = tk.StringVar(value="")
        csv_replace_box = self._entry_box(
            csv_toolbar,
            self.csv_text_replace_var,
            width=12,
            clear_command=self.clear_csv_text_replacement,
        )
        csv_replace_box.pack(side="left", padx=(0, 2))
        self.csv_text_replace_entry = csv_replace_box.entry
        self.csv_text_replace_entry.bind(
            "<Return>", lambda _event: self.replace_current_csv_text_match()
        )
        self._small_button(
            csv_toolbar, "替换", self.replace_current_csv_text_match
        ).pack(side="left", padx=1)
        self._small_button(
            csv_toolbar, "全部替换", self.replace_all_csv_text_matches
        ).pack(side="left", padx=1)
        self._small_button(
            csv_toolbar, "应用修改", self.apply_csv_editor_changes, primary=True
        ).pack(side="left", padx=(3, 0))

        csv_editor_frame = tk.Frame(csv_panel, bg="#f7f8fa")
        csv_editor_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        csv_editor_frame.grid_rowconfigure(0, weight=1)
        csv_editor_frame.grid_columnconfigure(0, weight=1)

        self.csv_editor = tk.Text(
            csv_editor_frame,
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
            csv_editor_frame, orient="vertical", command=self.csv_editor.yview
        )
        self.csv_editor_hscrollbar = tk.Scrollbar(
            csv_editor_frame, orient="horizontal", command=self.csv_editor.xview
        )
        self.csv_editor.configure(
            yscrollcommand=self.csv_editor_scrollbar.set,
            xscrollcommand=self.csv_editor_hscrollbar.set,
        )
        self.csv_editor.grid(row=0, column=0, sticky="nsew")
        self.csv_editor_scrollbar.grid(row=0, column=1, sticky="ns")
        self.csv_editor_hscrollbar.grid(row=1, column=0, sticky="ew")

        self.bind_all("<MouseWheel>", self.on_global_mousewheel, add="+")
        self.bind_all("<Button-4>", self.on_global_mousewheel, add="+")
        self.bind_all("<Button-5>", self.on_global_mousewheel, add="+")

        # ── 第三横区：时间轴区 ──────────────────────────────
        timeline_panel = tk.Frame(
            self,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        timeline_panel.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))
        timeline_panel.grid_rowconfigure(1, weight=1)
        timeline_panel.grid_columnconfigure(0, weight=1)

        timeline_toolbar = tk.Frame(timeline_panel, bg="#f7f8fa")
        timeline_toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=7)
        self._panel_title(timeline_toolbar, "时间轴").pack(side="left")
        self._panel_info_icon(
            timeline_toolbar,
            "时间轴区-i标tooltip占位文本",
        ).pack(side="left", padx=(5, 8))

        tk.Label(
            timeline_toolbar,
            text="起始日期",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(side="left")
        self.start_entry = tk.Entry(timeline_toolbar, width=12, font=("Consolas", 9))
        self.start_entry.pack(side="left", padx=(3, 7))
        tk.Label(
            timeline_toolbar,
            text="结束日期",
            font=("Microsoft YaHei", 8),
            bg="#f7f8fa",
            fg="#5f6879",
        ).pack(side="left")
        self.end_entry = tk.Entry(timeline_toolbar, width=12, font=("Consolas", 9))
        self.end_entry.pack(side="left", padx=(3, 5))
        self._small_button(timeline_toolbar, "应用范围", self.apply_range).pack(
            side="left", padx=(0, 5)
        )
        self._small_button(timeline_toolbar, "重置视图", self.reset_view).pack(
            side="left", padx=1
        )
        zoom_controls = tk.Frame(timeline_toolbar, bg="#f7f8fa")
        zoom_controls.pack(side="left", padx=(1, 5))

        self._zoom_icon_button(
            zoom_controls,
            symbol="＋",
            command=self.visual_zoom_in,
            accessible_text="放大视野",
        ).pack(side="left")

        self.visual_zoom_percent_var = tk.StringVar(value="100%")
        tk.Label(
            zoom_controls,
            textvariable=self.visual_zoom_percent_var,
            width=5,
            anchor="center",
            font=("Consolas", 8, "bold"),
            bg="#ffffff",
            fg="#334155",
            relief="solid",
            bd=1,
            padx=2,
            pady=2,
        ).pack(side="left", padx=2)

        self._zoom_icon_button(
            zoom_controls,
            symbol="－",
            command=self.visual_zoom_out,
            accessible_text="缩小视野",
        ).pack(side="left")
        self._small_button(timeline_toolbar, "导出图片", self.export_image).pack(
            side="left", padx=(0, 8)
        )

        self.timeline_search_var = tk.StringVar(value="")
        timeline_search_box = self._entry_box(
            timeline_toolbar,
            self.timeline_search_var,
            width=12,
            clear_command=self.clear_timeline_search,
        )
        timeline_search_box.pack(side="left", padx=(0, 2))
        self.timeline_search_entry = timeline_search_box.entry
        self.timeline_search_entry.bind(
            "<Return>", lambda _event: self.execute_timeline_search()
        )
        self._small_button(timeline_toolbar, "查找", self.execute_timeline_search).pack(
            side="left", padx=1
        )
        self._compact_button(
            timeline_toolbar, "↑", self.show_previous_timeline_search_match
        ).pack(side="left", padx=1)
        self._compact_button(
            timeline_toolbar, "↓", self.show_next_timeline_search_match
        ).pack(side="left", padx=1)
        self.timeline_search_counter_var = tk.StringVar(value="0/0")
        tk.Label(
            timeline_toolbar,
            textvariable=self.timeline_search_counter_var,
            width=4,
            font=("Microsoft YaHei", 7),
            bg="#f7f8fa",
            fg="#64748b",
        ).pack(side="left", padx=(1, 0))

        canvas_area = tk.Frame(timeline_panel, bg="#eef1f5")
        canvas_area.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        canvas_area.grid_rowconfigure(0, weight=1)
        canvas_area.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            canvas_area,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d8dde6",
            yscrollincrement=1,
        )
        self.vbar = tk.Scrollbar(canvas_area, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")

        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_drag_end)
        self.bind_all("<ButtonRelease-1>", self.on_event_release, add="+")
        # 所有滚轮操作统一进入同一个分派函数。Windows 下 Alt 会尝试
        # 激活系统菜单，因此单独接管 Alt 的按下/松开，并在失焦时复位。
        # 不再使用 <Alt-MouseWheel>，避免 Alt 被 Tk 当成开关后污染后续滚轮。
        self._alt_down = False
        self.bind_all("<KeyPress-Alt_L>", self.on_alt_key_press, add="+")
        self.bind_all("<KeyPress-Alt_R>", self.on_alt_key_press, add="+")
        self.bind_all("<KeyRelease-Alt_L>", self.on_alt_key_release, add="+")
        self.bind_all("<KeyRelease-Alt_R>", self.on_alt_key_release, add="+")
        self.bind_all("<FocusOut>", self.on_modifier_focus_out, add="+")

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Configure>", lambda _e: self.render())

        # 初始分割比例在窗口真正显示后再设置，兼顾不同屏幕尺寸。
        self.after_idle(lambda: self._set_initial_workspace_split(workspace))

    def _set_initial_workspace_split(self, workspace):
        try:
            width = max(workspace.winfo_width(), 900)
            workspace.sash_place(0, int(width * 0.45), 1)
        except tk.TclError:
            pass

    def _on_status_changed(self, *_args):
        message = self.status_var.get().strip()
        if not message or not hasattr(self, "info_log"):
            return
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.info_log.configure(state="normal")
        self.info_log.insert("end", f"[{timestamp}] {message}\n")
        self.info_log.see("end")
        self.info_log.configure(state="disabled")

    def _bind_info_tooltip(self, widget, text):
        """进入 i 标立即显示；离开时在事件循环末尾确认后隐藏。"""
        widget.bind(
            "<Enter>",
            lambda event, target=widget, content=text: self.show_info_tooltip(
                event, target, content
            ),
        )
        widget.bind("<Leave>", self.schedule_hide_info_tooltip)

    def _ensure_info_tooltip_window(self):
        """只创建一次 Tooltip 窗口，之后反复显示和隐藏。"""
        tooltip = getattr(self, "help_tooltip", None)

        if tooltip is not None:
            try:
                if tooltip.winfo_exists():
                    return
            except tk.TclError:
                pass

        self.help_tooltip = tk.Toplevel(self)
        self.help_tooltip.withdraw()
        self.help_tooltip.overrideredirect(True)
        self.help_tooltip.attributes("-topmost", True)

        self._info_tooltip_label = tk.Label(
            self.help_tooltip,
            text="",
            justify="left",
            bg="white",
            fg="#293247",
            relief="solid",
            borderwidth=1,
            padx=12,
            pady=10,
            font=("Microsoft YaHei", 9),
        )
        self._info_tooltip_label.pack()

    def _cancel_info_tooltip_hide_job(self):
        """取消尚未执行的隐藏任务，防止旧 Leave 覆盖新的 Enter。"""
        hide_job = getattr(self, "_info_tooltip_hide_job", None)

        if hide_job is not None:
            try:
                self.after_cancel(hide_job)
            except tk.TclError:
                pass

        self._info_tooltip_hide_job = None

    def _pointer_inside_widget(self, widget):
        """检查鼠标热点当前是否仍在指定 i 标内部。"""
        try:
            pointer_x = self.winfo_pointerx()
            pointer_y = self.winfo_pointery()

            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
        except tk.TclError:
            return False

        return left <= pointer_x < right and top <= pointer_y < bottom

    def show_info_tooltip(self, _event, widget, text):
        """鼠标进入 i 标时立即显示，并在当前事件循环结束后再次确认。"""
        self._cancel_info_tooltip_hide_job()
        self._ensure_info_tooltip_window()

        self._info_tooltip_widget = widget
        self._info_tooltip_text = text
        self._info_tooltip_label.configure(text=text)

        self.help_tooltip.update_idletasks()

        # Tooltip 放在控件边界之外，避免遮挡 i 标本身。
        x = widget.winfo_rootx() + widget.winfo_width() + 8
        y = widget.winfo_rooty() + widget.winfo_height() + 8
        self.help_tooltip.geometry(f"+{x}+{y}")

        self.help_tooltip.deiconify()
        self.help_tooltip.lift()

        # 防止同一轮事件中较晚到达的旧 withdraw 覆盖本次显示。
        self.after_idle(
            lambda target=widget: self._confirm_info_tooltip_visible(target)
        )

    def _confirm_info_tooltip_visible(self, widget):
        """若鼠标仍在当前 i 标内，确保 Tooltip 最终处于显示状态。"""
        if (
            getattr(self, "_info_tooltip_widget", None) is not widget
            or not self._pointer_inside_widget(widget)
        ):
            return

        tooltip = getattr(self, "help_tooltip", None)
        if tooltip is None:
            return

        try:
            tooltip.deiconify()
            tooltip.lift()
        except tk.TclError:
            pass

    def schedule_hide_info_tooltip(self, _event=None):
        """把隐藏操作排到当前 Enter/Leave 事件处理完成之后。"""
        self._cancel_info_tooltip_hide_job()
        self._info_tooltip_hide_job = self.after_idle(
            self._hide_info_tooltip_if_pointer_outside
        )

    def _hide_info_tooltip_if_pointer_outside(self):
        """只有鼠标确实不在当前 i 标内时才隐藏。"""
        self._info_tooltip_hide_job = None
        widget = getattr(self, "_info_tooltip_widget", None)

        if widget is not None and self._pointer_inside_widget(widget):
            return

        self.hide_info_tooltip()

    def hide_info_tooltip(self, _event=None):
        """隐藏 Tooltip，但保留窗口供下一次立即复用。"""
        self._cancel_info_tooltip_hide_job()

        tooltip = getattr(self, "help_tooltip", None)
        if tooltip is not None:
            try:
                tooltip.withdraw()
            except tk.TclError:
                self.help_tooltip = None
                self._info_tooltip_label = None

        self._info_tooltip_widget = None
        self._info_tooltip_text = None

    # 保留旧方法名，避免项目中其它代码仍引用它们。
    def show_help_tooltip(self, event=None):
        self.show_info_tooltip(
            event,
            self.help_hit_area,
            "工具标题-i标tooltip占位文本",
        )

    def hide_help_tooltip(self, event=None):
        self.schedule_hide_info_tooltip(event)

    def _entry_box(self, parent, variable, width=12, clear_command=None):
        """创建统一尺寸的输入框：输入区在左，清除键在框内右侧。"""
        box = tk.Frame(parent, bg="white", relief="sunken", bd=1)
        entry = tk.Entry(
            box,
            textvariable=variable,
            width=width,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        entry.pack(side="left", padx=(3, 0), pady=1)
        box.entry = entry
        if clear_command is not None:
            tk.Button(
                box,
                text="×",
                command=clear_command,
                font=("Microsoft YaHei", 7),
                relief="flat",
                padx=2,
                pady=0,
                bg="white",
                fg="#64748b",
                activebackground="#f3f4f6",
                activeforeground="#1f2937",
                bd=0,
                highlightthickness=0,
            ).pack(side="right", padx=1)
        return box

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

    def _small_button(self, parent, text, command, primary=False):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", 8),
            relief="raised",
            cursor="hand2",
            padx=5,
            pady=2,
            bg="#2968e8" if primary else "#ffffff",
            fg="#ffffff" if primary else "#253044",
            activebackground="#1f57c5" if primary else "#edf2f7",
            activeforeground="#ffffff" if primary else "#253044",
            bd=1,
            highlightthickness=0,
        )

    def _panel_info_icon(self, parent, tooltip_text, bg="#f7f8fa"):
        """创建所有区域共用的 i 标，并绑定同一套即时 Tooltip。"""
        icon = tk.Label(
            parent,
            text="i",
            width=2,
            font=("Microsoft YaHei", 8, "bold"),
            bg=bg,
            fg="#526075",
            relief="solid",
            bd=1,
            cursor="hand2",
        )
        self._bind_info_tooltip(icon, tooltip_text)
        return icon

    def _zoom_icon_button(self, parent, symbol, command, accessible_text):
        """创建“放大镜 + 加/减号”形式的二维缩放按钮。"""
        button = tk.Button(
            parent,
            text=f"⌕{symbol}",
            command=command,
            font=("Segoe UI Symbol", 9, "bold"),
            relief="raised",
            cursor="hand2",
            padx=4,
            pady=2,
            bg="#ffffff",
            fg="#253044",
            activebackground="#edf2f7",
            activeforeground="#253044",
            bd=1,
            highlightthickness=0,
            takefocus=True,
        )
        # 保留可读名称，后续若增加状态栏或 Tooltip 可直接复用。
        button.accessible_text = accessible_text
        return button

    def _compact_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", 9),
            relief="raised",
            cursor="hand2",
            padx=3,
            pady=2,
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
