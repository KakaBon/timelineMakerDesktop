"""主窗口三横区与各功能区布局构建。"""

import tkinter as tk
from tkinter import ttk

from .utils import resource_path


class UILayoutMixin:
    def _build_ui(self):
        self._configure_toolbar_styles()
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
            highlightcolor="#d9dde5",
            takefocus=0,
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
            ("工作方式\n"
             "CSV 编辑器中的修改先保留为草稿，点击“应用修改”后才同步到分类区和时间轴。\n\n"
             "撤销 / 重做分为两套：CSV 区按钮只管理尚未应用的 CSV 草稿；页面顶部按钮只管理已经正式生效的全局操作。\n\n"
             "Ctrl+Z / Ctrl+Y 按最近焦点分流：最近焦点在 CSV 区时操作 CSV 草稿，在 CSV 区外时操作全局正式历史。\n\n"
             "查找、筛选、定位、滚动、缩放和显示 / 隐藏等浏览操作不进入全局撤销历史。\n\n"
             "“导出 CSV”用于把当前 CSV 内容保存为文件。"),
            bg="white",
        )
        self.help_hit_area.pack(side="left", padx=(7, 0))

        global_actions = tk.Frame(header, bg="white")
        global_actions.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=7)

        # 全局撤销 / 重做使用经典弯箭头 icon。这里继续用 ttk.Button，
        # 让 application.py 现有的 state=normal/disabled 控制保持原生可靠。
        def run_global_action(command):
            # 若点击时恰好显示着 icon 的悬浮提示，必须先同步收起，
            # 避免后续操作弹出模态窗口时提示被冻结在界面上。
            self.hide_info_tooltip()
            try:
                self.update_idletasks()
            except tk.TclError:
                pass
            command()

        self.undo_button = ttk.Button(
            global_actions,
            text="↶",
            command=lambda: run_global_action(self.undo_global_action),
            style="Toolbar.Nav.TButton",
            cursor="hand2",
            takefocus=False,
            width=2,
        )
        self.undo_button.configure(state="disabled")
        self.undo_button._csv_validation_guard_bypass = True
        self._bind_info_tooltip(self.undo_button, "全局撤销", compact=True)
        self.undo_button.pack(side="left", padx=(0, 3))

        self.redo_button = ttk.Button(
            global_actions,
            text="↷",
            command=lambda: run_global_action(self.redo_global_action),
            style="Toolbar.Nav.TButton",
            cursor="hand2",
            takefocus=False,
            width=2,
        )
        self.redo_button.configure(state="disabled")
        self.redo_button._csv_validation_guard_bypass = True
        self._bind_info_tooltip(self.redo_button, "全局重做", compact=True)
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
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#d7dce5",
            highlightcolor="#d7dce5",
            takefocus=0,
            cursor="arrow",
        )
        self.info_log.grid(row=0, column=0, sticky="ew")
        # 信息记录区只用于查看：不出现文本输入光标，不允许鼠标选择；
        # 但点击这里仍应等价于“点击页面别处”，把分类/迁移下拉菜单收起。
        self.info_log.bind("<Button-1>", self._on_info_log_pointer_press)
        self.info_log.bind("<B1-Motion>", lambda _event: "break")
        self.info_log.bind("<Double-Button-1>", lambda _event: "break")
        self.info_log.bind("<Triple-Button-1>", lambda _event: "break")
        self.info_log_scrollbar = self._make_scrollbar(
            info_body, orient="vertical", command=self.info_log.yview
        )
        self.info_log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.info_log.configure(yscrollcommand=self.info_log_scrollbar.set)

        self.status_var = tk.StringVar(value="")
        self.status_var.trace_add("write", self._on_status_changed)

        # ── 第二横区：分类区与 CSV 编辑区 ─────────────────────
        workspace = tk.Frame(
            self,
            bg="#eef1f5",
            height=260,
        )
        workspace.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 4))
        workspace.grid_propagate(False)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1, minsize=560)
        workspace.grid_columnconfigure(1, weight=0, minsize=1)

        # 第二横区不再使用可拖动 PanedWindow。
        # CSV 区保留足够完整展示区标题行的固定基础宽度，
        # 分类区获得其余空间，并把多余空间交给“事件迁移”占位视窗。
        category_panel = tk.Frame(
            workspace,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        csv_panel = tk.Frame(
            workspace,
            bg="#f7f8fa",
            width=1,
            highlightthickness=1,
            highlightbackground="#d7dce5",
            highlightcolor="#d7dce5",
            takefocus=0,
        )
        self.csv_panel = csv_panel
        category_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        category_panel.configure(
            highlightcolor="#d7dce5", takefocus=0
        )
        csv_panel.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        csv_panel.grid_propagate(False)
        csv_panel.pack_propagate(False)

        # 分类区：左侧为分类工具栏 + 分类表；右侧事件迁移区从标题行上沿开始。
        category_layout = tk.Frame(category_panel, bg="#f7f8fa")
        category_layout.pack(fill="both", expand=True, padx=10, pady=(7, 8))
        category_layout.grid_rowconfigure(0, weight=1)
        category_layout.grid_columnconfigure(0, weight=0, minsize=390)
        category_layout.grid_columnconfigure(1, weight=1)

        category_left = tk.Frame(category_layout, bg="#f7f8fa", width=390)
        category_left.grid(row=0, column=0, sticky="nsew")
        category_left.grid_propagate(False)

        category_toolbar = tk.Frame(category_left, bg="#f7f8fa")
        category_toolbar.pack(fill="x", pady=(0, 4))

        self._panel_title(category_toolbar, "分类").pack(side="left")
        self._panel_info_icon(
            category_toolbar,
            ("分类管理\n"
             "筛选结果会自动勾选并整行高亮，↑ / ↓ 可逐项定位；事件数可输入具体数字，输入 >0 筛选非空分类。\n\n"
             "0 事件分类会灰显，但仍可操作。\n\n"
             "眼睛控制显示 / 隐藏；表头眼睛批量作用于当前已选分类，未选择时作用于全部分类。\n\n"
             "双击分类名可重命名。\n\n"
             "side 可设为上侧、下侧或无限制；切换到单侧时会同步分类内事件。\n\n"
             "事件迁移可选择部分事件、所有事件，或以“所有分类”为源统一迁入一个目标分类。\n\n"
             "“未分类”为固定分类，始终保留且 side 为无限制。"),
        ).pack(side="left", padx=(5, 8))

        # 分类增删改为同一外框中的纯图标动作。
        category_edit_actions = self._integrated_shell(category_toolbar)
        category_edit_actions.pack(side="left", padx=(0, 4), pady=0)
        self._integrated_icon_action(
            category_edit_actions, "add", self.create_category,
            tooltip_text="新建分类", width=25,
        ).pack(side="left", fill="y", padx=(1, 0), pady=1)
        self._integrated_separator(category_edit_actions).pack(side="left", fill="y", pady=1)
        self._integrated_icon_action(
            category_edit_actions, "delete", self.delete_selected_categories,
            tooltip_text="删除分类", width=25,
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

        # SearchCombi：分类筛选字段 → 值 → 查找 → 上下定位 → 结果计数。
        category_search_combi = tk.Frame(category_toolbar, bg="#f7f8fa")
        category_search_combi.pack(side="left", padx=(4, 0))
        self.build_category_search_controls(category_search_combi)

        legend_container = tk.Frame(
            category_left,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d7dce5",
            highlightcolor="#d7dce5",
            takefocus=0,
        )
        legend_container.pack(fill="both", expand=True)
        legend_container.grid_rowconfigure(1, weight=1)
        legend_container.grid_columnconfigure(0, weight=1)

        self.legend_header_frame = tk.Frame(
            legend_container,
            bg="#eef1f5",
            height=25,
        )
        self.legend_header_frame.grid(row=0, column=0, sticky="ew")
        self.legend_header_frame.grid_propagate(False)
        # 只把滚动条轨道色延伸到表头右侧；真正的滑块仍从内容区顶部开始。
        self.legend_scrollbar_cap = tk.Frame(
            legend_container,
            bg=getattr(self, "_scrollbar_trough_color", "#e6e9ef"),
            width=14,
            takefocus=0,
        )
        self.legend_scrollbar_cap.grid(row=0, column=1, sticky="nsew")

        self.legend_canvas = tk.Canvas(
            legend_container, bg="white", highlightthickness=0, bd=0
        )
        self.legend_scrollbar = self._make_scrollbar(
            legend_container, orient="vertical", command=self.on_legend_scrollbar
        )
        self.legend_canvas.configure(yscrollcommand=self.legend_scrollbar.set)
        self.legend_canvas.grid(row=1, column=0, sticky="nsew")
        self.legend_scrollbar.grid(row=1, column=1, sticky="ns")

        self.legend_frame = tk.Frame(self.legend_canvas, bg="white")
        self.legend_window = self.legend_canvas.create_window(
            (0, 0), window=self.legend_frame, anchor="nw"
        )
        self.legend_frame.bind("<Configure>", self.update_legend_scrollregion)
        self.legend_canvas.bind("<Configure>", self.resize_legend_window)

        # 事件迁移区与分类标题行上沿对齐，不再浪费一整行工具栏高度。
        self.migration_panel = tk.Frame(
            category_layout,
            bg="white",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        self.migration_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self.build_event_migration_controls(self.migration_panel)

        # CSV 区：所有操作保持完整名称，并按“输入框在左、操作按钮在右”排列。
        csv_toolbar = tk.Frame(csv_panel, bg="#f7f8fa")
        csv_toolbar.pack(fill="x", padx=8, pady=(7, 4))

        self._panel_title(csv_toolbar, "CSV 编辑器").pack(side="left")
        self._panel_info_icon(
            csv_toolbar,
            ("CSV 编辑\n"
             "双击单元格，或选中后按 Enter / F2 进入编辑；category 和 side 字段使用下拉选择。\n\n"
             "新增事件 / 字段、单元格编辑、预删除和日期排序在“应用修改”前都属于 CSV 草稿；CSV 区自己的撤销 / 重做按钮只管理这些未应用修改。\n\n"
             "Ctrl+Z / Ctrl+Y 按最近焦点分流：最近焦点在 CSV 区时只操作 CSV 草稿；在 CSV 区外时只操作顶部全局正式历史，两者不会互相越界。\n\n"
             "点击行号或列头可选择行 / 列；选中列以淡蓝色整列高亮。垃圾桶仅标记为预删除，应用后才正式删除；再次点击已预删除的行头 / 列头可取消预删除。带 * 的关键字段不可删除。\n\n"
             "查找 / 替换只处理数据单元格，不包含表头和行号。\n\n"
             "应用时如存在无效数据，会高亮对应单元格并逐项引导修正。\n\n"
             "date 支持常见日期写法：YYYY-MM-DD / YYYY/MM/DD / YYYY.MM.DD、YYYY年M月D日、DD.MM.YYYY / DD/MM/YYYY / DD-MM-YYYY、MM.DD.YYYY / MM/DD/YYYY / MM-DD-YYYY，以及 25 Sep 2014、Sep 25 2014、2014 Sep 25 这类英文或德文月份名称/缩写。纯数字的日月年或月日年若本身有歧义，会根据同一日期列中的无歧义日期统一判断；若整列都无法判断，则要求改成无歧义格式。\n\n"
             "导出 CSV 会保存当前 CSV 草稿内容。"),
        ).pack(side="left", padx=(5, 7))

        # CSV 主操作统一为一体式工具组。局部撤销 / 重做与顶部全局历史分离：
        # 载入示例 → 导入 → 导出 → 新增事件 → 新增字段 → 预删除 → 日期排序
        # → CSV 撤销 → CSV 重做 → 应用。
        csv_utility_combi = self._integrated_shell(csv_toolbar)
        csv_utility_combi.pack(side="left", padx=(0, 4), pady=0)

        csv_actions_before_history = (
            ("load_sample", self.load_sample, "载入示例", 25, False),
            ("import", self.import_csv, "导入 CSV", 25, True),
            ("export", self.export_csv, "导出 CSV", 25, True),
            ("add_event", self.add_csv_event_row, "新增事件", 25, False),
            ("add_field", self.add_csv_field, "新增字段", 25, False),
            ("delete", self.mark_selected_csv_for_deletion, "删除所选行 / 列", 25, False),
            ("sort_date", self.sort_csv_rows_by_date, "按日期排序", 27, False),
        )
        action_index = 0
        for icon, command, tooltip, width, primary in csv_actions_before_history:
            if action_index:
                self._integrated_separator(csv_utility_combi).pack(
                    side="left", fill="y", pady=1
                )
            self._integrated_icon_action(
                csv_utility_combi, icon, command, tooltip_text=tooltip,
                width=width, primary=primary,
            ).pack(side="left", fill="y", padx=(1, 0) if action_index == 0 else 0, pady=1)
            action_index += 1

        for symbol, command, tooltip, attr_name in (
            ("↶", self.undo_csv_local_edit, "CSV 草稿撤销", "csv_undo_button"),
            ("↷", self.redo_csv_local_edit, "CSV 草稿重做", "csv_redo_button"),
        ):
            self._integrated_separator(csv_utility_combi).pack(
                side="left", fill="y", pady=1
            )
            button = self._integrated_action(
                csv_utility_combi, symbol, command, width=1
            )
            button._csv_validation_guard_bypass = True
            self._bind_info_tooltip(button, tooltip, compact=True)
            button.pack(side="left", fill="y", pady=1)
            setattr(self, attr_name, button)

        self._integrated_separator(csv_utility_combi).pack(
            side="left", fill="y", pady=1
        )
        apply_button = self._integrated_icon_action(
            csv_utility_combi, "apply", self.apply_csv_editor_changes,
            tooltip_text="应用修改", width=27, primary=True,
        )
        apply_button.pack(side="left", fill="y", padx=(0, 1), pady=1)

        # SearchControl：真正的一体式 [值 | 查找 | ↑ | ↓ | 0/0]
        csv_search_combi = self._integrated_shell(csv_toolbar)
        csv_search_combi.pack(side="left", padx=(4, 4), pady=0)

        self.csv_text_search_var = tk.StringVar(value="")
        csv_find_box = self._integrated_entry(
            csv_search_combi, self.csv_text_search_var,
            clear_command=self.clear_csv_text_search, width=12,
        )
        csv_find_box.pack(side="left", fill="y", padx=1, pady=1)
        self.csv_text_search_entry = csv_find_box.entry
        self.csv_text_search_entry.bind("<Return>", lambda _event: self.execute_csv_text_search())

        self._integrated_separator(csv_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_icon_action(
            csv_search_combi, "search", self.execute_csv_text_search,
            tooltip_text="查找", width=25,
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(csv_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            csv_search_combi, "↑", self.show_previous_csv_text_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(csv_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            csv_search_combi, "↓", self.show_next_csv_text_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(csv_search_combi).pack(side="left", fill="y", pady=1)
        self.csv_text_search_counter_var = tk.StringVar(value="0/0")
        self._integrated_counter(
            csv_search_combi, self.csv_text_search_counter_var
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

        # ReplaceControl：真正的一体式 [替换值 | 替换 | 全部替换]
        csv_replace_combi = self._integrated_shell(csv_toolbar)
        csv_replace_combi.pack(side="left", padx=(4, 3), pady=0)

        self.csv_text_replace_var = tk.StringVar(value="")
        csv_replace_box = self._integrated_entry(
            csv_replace_combi, self.csv_text_replace_var,
            clear_command=self.clear_csv_text_replacement, width=12,
        )
        csv_replace_box.pack(side="left", fill="y", padx=1, pady=1)
        self.csv_text_replace_box = csv_replace_box
        self.csv_text_replace_entry = csv_replace_box.entry
        self.csv_text_replace_entry.bind(
            "<Return>", lambda _event: self.replace_current_csv_text_match()
        )
        self._integrated_separator(csv_replace_combi).pack(side="left", fill="y", pady=1)
        self.csv_text_replace_button = self._integrated_icon_action(
            csv_replace_combi, "replace", self.replace_current_csv_text_match,
            tooltip_text="替换", width=27,
        )
        self.csv_text_replace_button.pack(side="left", fill="y", pady=1)
        self._integrated_separator(csv_replace_combi).pack(side="left", fill="y", pady=1)
        self.csv_text_replace_all_button = self._integrated_icon_action(
            csv_replace_combi, "replace_all", self.replace_all_csv_text_matches,
            tooltip_text="全部替换", width=29,
        )
        self.csv_text_replace_all_button.pack(side="left", fill="y", padx=(0, 1), pady=1)

        def _lock_csv_panel_to_toolbar_width():
            # CSV 区宽度只由区标题行决定；表格内容再宽也只能在区内横向滚动。
            csv_toolbar.update_idletasks()
            required = csv_toolbar.winfo_reqwidth() + 18
            csv_panel.configure(width=required)
            workspace.grid_columnconfigure(1, minsize=required)

        self.after_idle(_lock_csv_panel_to_toolbar_width)

        csv_editor_frame = tk.Frame(
            csv_panel,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
            highlightcolor="#d7dce5",
            takefocus=0,
        )
        csv_editor_frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        csv_editor_frame.grid_rowconfigure(1, weight=1)
        csv_editor_frame.grid_columnconfigure(1, weight=1)

        csv_header_top_rule = tk.Frame(
            csv_editor_frame, bg="#d7dce5", height=1
        )
        csv_header_top_rule.grid(row=0, column=0, columnspan=3, sticky="ew")

        # CSV 的下拉编辑器使用与行聚焦一致的浅蓝选择色，
        # 不再出现系统默认的深蓝色文本选择块。
        self.option_add("*TCombobox*Listbox.selectBackground", "#dbeafe")
        self.option_add("*TCombobox*Listbox.selectForeground", "#263247")

        csv_style = ttk.Style(self)
        # Windows 原生 Treeview 表头会忽略自定义 background。
        # clam 主题允许 CSV 表头真正使用与分类表头一致的浅灰色。
        try:
            csv_style.theme_use("clam")
        except tk.TclError:
            pass

        csv_style.configure(
            "CsvCell.TCombobox",
            fieldbackground="#0b79d0",
            background="white",
            foreground="white",
            selectbackground="#0b79d0",
            selectforeground="white",
            arrowcolor="#263247",
            bordercolor="#8fa3b8",
            lightcolor="#8fa3b8",
            darkcolor="#8fa3b8",
        )
        csv_style.map(
            "CsvCell.TCombobox",
            fieldbackground=[
                ("readonly", "#0b79d0"),
                ("focus", "#0b79d0"),
                ("!disabled", "#0b79d0"),
            ],
            background=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
            foreground=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
            selectbackground=[
                ("readonly", "#0b79d0"),
                ("focus", "#0b79d0"),
                ("!disabled", "#0b79d0"),
            ],
            selectforeground=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
        )
        # 分类区工具栏下拉框：静止、聚焦和选择完成后都保持白底。
        # 只有展开后的列表项使用全局设定的淡蓝色当前项 / hover 高亮。
        csv_style.configure(
            "Toolbar.TCombobox",
            fieldbackground="white",
            background="white",
            foreground="#263247",
            selectbackground="white",
            selectforeground="#263247",
            arrowcolor="#263247",
            bordercolor="#8fa3b8",
            lightcolor="#8fa3b8",
            darkcolor="#8fa3b8",
        )
        csv_style.map(
            "Toolbar.TCombobox",
            fieldbackground=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
            background=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
            foreground=[
                ("readonly", "#263247"),
                ("focus", "#263247"),
                ("!disabled", "#263247"),
            ],
            selectbackground=[
                ("readonly", "white"),
                ("focus", "white"),
                ("!disabled", "white"),
            ],
            selectforeground=[
                ("readonly", "#263247"),
                ("focus", "#263247"),
                ("!disabled", "#263247"),
            ],
        )

        csv_style.layout(
            "CsvGrid.Treeview",
            [("Treeview.treearea", {"sticky": "nswe"})],
        )
        csv_style.layout(
            "CsvRowNumbers.Treeview",
            [("Treeview.treearea", {"sticky": "nswe"})],
        )
        csv_style.configure(
            "CsvGrid.Treeview",
            font=("Consolas", 10),
            rowheight=25,
            background="white",
            fieldbackground="white",
            foreground="#263247",
        )
        csv_style.map(
            "CsvGrid.Treeview",
            background=[("selected", "#dbeafe")],
            fieldbackground=[("selected", "#dbeafe")],
            foreground=[("selected", "#263247")],
        )
        csv_style.configure(
            "CsvGrid.Treeview.Heading",
            font=("Consolas", 9, "bold"),
            background="#eef1f5",
            foreground="#263247",
            relief="flat",
            borderwidth=1,
            bordercolor="#d7dce5",
            lightcolor="#d7dce5",
            darkcolor="#d7dce5",
        )
        csv_style.map(
            "CsvGrid.Treeview.Heading",
            background=[("active", "#eef1f5")],
        )

        # 固定行号列与分类区表头使用同一浅灰底色。
        csv_style.configure(
            "CsvRowNumbers.Treeview",
            font=("Consolas", 10),
            rowheight=25,
            background="#eef1f5",
            fieldbackground="#eef1f5",
            foreground="#263247",
            borderwidth=0,
        )
        csv_style.map(
            "CsvRowNumbers.Treeview",
            background=[("selected", "#dbeafe")],
            fieldbackground=[("selected", "#dbeafe")],
            foreground=[("selected", "#263247")],
        )
        csv_style.configure(
            "CsvRowNumbers.Treeview.Heading",
            font=("Consolas", 9, "bold"),
            background="#eef1f5",
            foreground="#263247",
            relief="flat",
            borderwidth=1,
            bordercolor="#d7dce5",
            lightcolor="#d7dce5",
            darkcolor="#d7dce5",
        )
        csv_style.map(
            "CsvRowNumbers.Treeview.Heading",
            background=[("active", "#eef1f5")],
        )

        # 行号单独使用一个 Treeview：它不参与横向滚动，因此始终固定在左侧。
        self.csv_row_numbers = ttk.Treeview(
            csv_editor_frame,
            columns=("rownum",),
            show="headings",
            style="CsvRowNumbers.Treeview",
            selectmode="extended",
            height=1,
        )
        self.csv_row_numbers.heading("rownum", text="行", anchor="center")
        self.csv_row_numbers.column(
            "rownum", width=48, minwidth=48, stretch=False, anchor="center"
        )

        self.csv_editor = ttk.Treeview(
            csv_editor_frame,
            show="headings",
            style="CsvGrid.Treeview",
            selectmode="extended",
        )

        self.csv_editor_scrollbar = self._make_scrollbar(
            csv_editor_frame,
            orient="vertical",
            command=self.on_csv_vertical_scrollbar,
            takefocus=0,
        )
        self.csv_editor_hscrollbar = self._make_scrollbar(
            csv_editor_frame, orient="horizontal", command=self.on_csv_horizontal_scrollbar
        )
        self.csv_editor.configure(
            yscrollcommand=self.on_csv_editor_yview_changed,
            xscrollcommand=self.on_csv_editor_xview_changed,
        )
        self.csv_row_numbers.configure(
            yscrollcommand=self.on_csv_row_numbers_yview_changed,
        )
        self.csv_row_numbers.grid(row=1, column=0, sticky="ns")
        self.csv_editor.grid(row=1, column=1, sticky="nsew")
        self.csv_editor_scrollbar.grid(row=1, column=2, sticky="ns")
        self.csv_editor_hscrollbar.grid(row=2, column=1, sticky="ew")

        # Treeview does not reliably expose the heading/body separator lines
        # under the Windows/clam combination. Draw the two missing internal
        # rules explicitly, using exactly the same subtle border colour as the
        # category table and the CSV table container.
        self.csv_header_bottom_rule = tk.Frame(
            csv_editor_frame, bg="#d7dce5", height=1, takefocus=0
        )
        self.csv_row_number_right_rule = tk.Frame(
            csv_editor_frame, bg="#d7dce5", width=1, takefocus=0
        )

        def _place_csv_internal_rules(_event=None):
            try:
                csv_editor_frame.update_idletasks()
                heading_h = 25
                rownum_w = self.csv_row_numbers.winfo_width()
                frame_w = csv_editor_frame.winfo_width()
                frame_h = csv_editor_frame.winfo_height()
                hscroll_h = self.csv_editor_hscrollbar.winfo_height()
                vscroll_w = self.csv_editor_scrollbar.winfo_width()
                self.csv_header_bottom_rule.place(
                    x=0, y=heading_h,
                    width=max(0, frame_w - vscroll_w), height=1
                )
                self.csv_row_number_right_rule.place(
                    x=rownum_w, y=1, width=1,
                    height=max(0, frame_h - hscroll_h - 1)
                )
                self.csv_header_bottom_rule.lift()
                self.csv_row_number_right_rule.lift()
            except tk.TclError:
                pass

        csv_editor_frame.bind("<Configure>", _place_csv_internal_rules, add="+")
        self.after_idle(_place_csv_internal_rules)

        self.csv_row_numbers.bind("<Motion>", self._normalize_csv_cursor, add="+")
        self.csv_row_numbers.bind("<Button-1>", self._block_csv_separator_drag)
        self.csv_row_numbers.bind("<Button-1>", self._sync_csv_active_row_from_row_number, add="+")
        self.csv_row_numbers.bind("<Button-1>", self.on_csv_row_number_click, add="+")
        self.csv_row_numbers.bind("<MouseWheel>", self.on_csv_grid_mousewheel)
        self.csv_row_numbers.bind("<Shift-MouseWheel>", self.on_csv_grid_shift_mousewheel)
        self.csv_editor.bind("<Motion>", self._normalize_csv_cursor, add="+")
        self.csv_editor.bind("<Button-1>", self._block_csv_separator_drag)
        self.csv_editor.bind("<Button-1>", self._sync_csv_active_row_from_editor, add="+")
        self.csv_editor.bind("<Button-1>", self.on_csv_grid_click, add="+")
        self.csv_editor.bind("<Double-1>", self.on_csv_grid_double_click)
        self.csv_editor.bind("<Return>", self.on_csv_grid_keyboard_edit)
        self.csv_editor.bind("<F2>", self.on_csv_grid_keyboard_edit)
        self.csv_editor.bind("<MouseWheel>", self.on_csv_grid_mousewheel)
        self.csv_editor.bind("<Shift-MouseWheel>", self.on_csv_grid_shift_mousewheel)
        self.csv_editor.bind("<Motion>", self.on_csv_grid_motion, add="+")
        self.csv_editor.bind("<Leave>", self.on_csv_grid_leave)
        self.csv_editor.bind("<Control-z>", self.undo_csv_local_edit)
        self.csv_editor.bind("<Control-y>", self.redo_csv_local_edit)

        self.bind_all("<MouseWheel>", self.on_global_mousewheel, add="+")
        self.bind_all("<Button-4>", self.on_global_mousewheel, add="+")
        self.bind_all("<Button-5>", self.on_global_mousewheel, add="+")

        # ── 第三横区：时间轴区 ──────────────────────────────
        timeline_panel = tk.Frame(
            self,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
            highlightcolor="#d7dce5",
            takefocus=0,
        )
        timeline_panel.grid(row=2, column=0, sticky="nsew", padx=12, pady=(4, 12))
        timeline_panel.grid_rowconfigure(1, weight=1)
        timeline_panel.grid_columnconfigure(0, weight=1)

        timeline_toolbar = tk.Frame(timeline_panel, bg="#f7f8fa")
        timeline_toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=7)
        self._panel_title(timeline_toolbar, "时间轴").pack(side="left")
        self._panel_info_icon(
            timeline_toolbar,
            ("时间轴操作\n"
             "滚轮：纵向滚动\n"
             "Shift + 滚轮：横向移动时间范围\n"
             "Ctrl + 滚轮：横向缩放时间范围\n"
             "Ctrl + Shift + 滚轮：二维缩放（横向时间密度 + 纵向事件布局）\n\n"
             "拖动画布：横向平移时间范围\n"
             "工具栏放大 / 缩小按钮：二维缩放\n"
             "日期范围：手动限定显示区间\n"
             "重置视图：恢复默认缩放、显示全部分类，并重新适配完整数据范围。"),
        ).pack(side="left", padx=(5, 8))

        # 独立动作：导出图片、重置视图
        self._small_button(timeline_toolbar, "导出图片", self.export_image).pack(
            side="left", padx=(0, 3)
        )
        self._small_button(timeline_toolbar, "重置视图", self.reset_view).pack(
            side="left", padx=(0, 4)
        )

        # ZoomControl：一体式 [放大镜内+ | 100% | 放大镜内−]
        zoom_controls = self._integrated_shell(timeline_toolbar)
        zoom_controls.pack(side="left", padx=(0, 4), pady=0)

        self._integrated_icon_action(
            zoom_controls, "zoom_in", self.visual_zoom_in,
            tooltip_text="放大", width=27,
        ).pack(side="left", fill="y", padx=(1, 0), pady=1)
        self._integrated_separator(zoom_controls).pack(side="left", fill="y", pady=1)

        self.visual_zoom_percent_var = tk.StringVar(value="100%")
        self._integrated_centered_value(
            zoom_controls, self.visual_zoom_percent_var, pixel_width=42,
        ).pack(side="left", fill="y", pady=1)

        self._integrated_separator(zoom_controls).pack(side="left", fill="y", pady=1)
        self._integrated_icon_action(
            zoom_controls, "zoom_out", self.visual_zoom_out,
            tooltip_text="缩小", width=27,
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

        # DateRangeControl：一体式 [日期值 | 至图标 | 日期值 | 应用范围]
        date_range_controls = self._integrated_shell(timeline_toolbar)
        date_range_controls.pack(side="left", padx=(0, 4), pady=0)

        start_box = self._integrated_plain_entry_box(date_range_controls, width=10, inner_padx=7)
        start_box.pack(side="left", fill="y", padx=(1, 0), pady=1)
        self.start_entry = start_box.entry

        self._integrated_separator(date_range_controls).pack(side="left", fill="y", pady=1)
        self._integrated_icon_static(
            date_range_controls, "date_range", width=27
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(date_range_controls).pack(side="left", fill="y", pady=1)
        end_box = self._integrated_plain_entry_box(date_range_controls, width=10, inner_padx=7)
        end_box.pack(side="left", fill="y", pady=1)
        self.end_entry = end_box.entry

        self._integrated_separator(date_range_controls).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            date_range_controls, "应用范围", self.apply_range
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

        # SearchControl：真正的一体式 [值 | 查找 | ↑ | ↓ | 0/0]
        timeline_search_combi = self._integrated_shell(timeline_toolbar)
        timeline_search_combi.pack(side="left", padx=(4, 0), pady=0)

        self.timeline_search_var = tk.StringVar(value="")
        timeline_search_box = self._integrated_entry(
            timeline_search_combi, self.timeline_search_var,
            clear_command=self.clear_timeline_search, width=12,
        )
        timeline_search_box.pack(side="left", fill="y", padx=1, pady=1)
        self.timeline_search_entry = timeline_search_box.entry
        self.timeline_search_entry.bind("<Return>", lambda _event: self.execute_timeline_search())

        self._integrated_separator(timeline_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_icon_action(
            timeline_search_combi, "search", self.execute_timeline_search,
            tooltip_text="查找", width=25,
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(timeline_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            timeline_search_combi, "↑", self.show_previous_timeline_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(timeline_search_combi).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            timeline_search_combi, "↓", self.show_next_timeline_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(timeline_search_combi).pack(side="left", fill="y", pady=1)
        self.timeline_search_counter_var = tk.StringVar(value="0/0")
        self._integrated_counter(
            timeline_search_combi, self.timeline_search_counter_var
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

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
        self.vbar = self._make_scrollbar(
            canvas_area, orient="vertical", command=self.canvas.yview
        )
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

        # 除 CSV 表格内的单元格编辑器外，页面上的普通文本输入框在点击框外后
        # 立即失去输入焦点，不再保留闪烁光标。
        self.bind_all("<Button-1>", self._release_non_table_text_focus, add="+")

    def _set_initial_workspace_split(self, workspace):
        try:
            width = max(workspace.winfo_width(), 900)
            workspace.sash_place(0, int(width * 0.45), 1)
        except tk.TclError:
            pass
