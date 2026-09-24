"""分类表渲染与增量刷新。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendRenderMixin:
    def render_legend(self):
        # “未分类”是固定系统分类：永远存在、永远置顶、side 永远无限制。
        current_categories = list(getattr(self, "categories", []))
        self.categories = ["未分类"] + [
            name for name in current_categories if name != "未分类"
        ]
        if not hasattr(self, "category_side_states"):
            self.category_side_states = {}
        self.category_side_states["未分类"] = "unrestricted"

        # 只要分类结构没有变化，就不要销毁/重建整张分类表。
        # side、事件数、显示状态、颜色等都可以原位刷新；这能避免 Windows
        # 上 Checkbutton 整列在每次数据更新时闪一下。真正新增/删除/重命名
        # 分类导致结构变化时，才进入下面的完整重建路径。
        existing_rows = getattr(self, "legend_row_widgets", {})
        if existing_rows and list(existing_rows.keys()) == self.categories:
            self.refresh_legend_incremental()
            return

        for widget in self.legend_frame.winfo_children():
            widget.destroy()

        if not hasattr(self, "selected_categories"):
            self.selected_categories = set()
        valid_selectable = {
            name for name in self.categories if name != "未分类"
        }
        self.selected_categories.intersection_update(valid_selectable)

        counts = {category: 0 for category in self.categories}
        for row in self.rows:
            category = row["category"]
            counts[category] = counts.get(category, 0) + 1
        self.legend_category_counts = counts

        # 分类管理表固定列：选择 | 显示 | 颜色 | 分类名 | 事件数 | side
        header_parent = getattr(self, "legend_header_frame", self.legend_frame)
        for widget in header_parent.winfo_children():
            widget.destroy()
        header = tk.Frame(header_parent, bg="#eef1f5", height=24)
        header.pack(fill="x")
        header.pack_propagate(False)

        select_width = 28
        visible_width = 34
        color_width = 32
        count_width = 48
        side_width = 126

        selectable = [name for name in self.categories if name != "未分类"]
        all_selected = bool(selectable) and all(
            name in self.selected_categories for name in selectable
        )
        select_all_var = tk.BooleanVar(value=all_selected)
        self.legend_select_all_var = select_all_var
        self.legend_select_vars = {}
        self.legend_row_widgets = {}
        self.legend_count_labels = {}
        self.legend_name_labels = {}
        self.legend_name_cells = {}
        self.legend_eye_canvases = {}
        self.legend_color_canvases = {}
        self.legend_side_controls = {}
        self.legend_field_widgets = {}

        tk.Checkbutton(
            header,
            variable=select_all_var,
            command=lambda: self._set_all_categories_selected(
                bool(select_all_var.get())
            ),
            bg="#eef1f5",
            activebackground="#eef1f5",
            bd=0,
            highlightthickness=0,
        ).pack(side="left", padx=(2, 0))
        tk.Frame(header, bg="#eef1f5", width=max(0, select_width - 23)).pack(
            side="left"
        )

        # “显示”表头改为可操作眼睛：优先作用于已勾选分类；没有勾选时作用于全部。
        visible_header = tk.Frame(header, bg="#eef1f5", width=visible_width)
        visible_header.pack(side="left", fill="y")
        visible_header.pack_propagate(False)
        header_eye = tk.Canvas(
            visible_header,
            width=22,
            height=20,
            bg="#eef1f5",
            highlightthickness=0,
            bd=0,
            cursor="hand2",
        )
        header_eye.pack(expand=True)
        header_eye.bind("<Button-1>", lambda _e: self.toggle_selected_category_visibility())
        self._bind_info_tooltip(header_eye, "切换所选分类显示", compact=True)
        self.legend_header_eye_canvas = header_eye

        color_header = tk.Frame(header, bg="#eef1f5", width=color_width)
        color_header.pack(side="left", fill="y")
        color_header.pack_propagate(False)
        tk.Label(
            color_header,
            text="颜色",
            bg="#eef1f5",
            fg="#526075",
            font=("Microsoft YaHei", 8),
        ).pack(expand=True)

        side_header = tk.Frame(header, bg="#eef1f5", width=side_width)
        side_header.pack(side="right", fill="y")
        side_header.pack_propagate(False)
        tk.Label(
            side_header,
            text="side",
            bg="#eef1f5",
            fg="#526075",
            font=("Microsoft YaHei", 8),
        ).pack(expand=True)

        count_header = tk.Frame(header, bg="#eef1f5", width=count_width)
        count_header.pack(side="right", fill="y")
        count_header.pack_propagate(False)
        tk.Label(
            count_header,
            text="事件数",
            bg="#eef1f5",
            fg="#526075",
            font=("Microsoft YaHei", 8),
        ).pack(expand=True)

        name_header = tk.Frame(header, bg="#eef1f5", width=150)
        name_header.pack(side="left", fill="y")
        name_header.pack_propagate(False)
        tk.Label(
            name_header,
            text="分类名",
            bg="#eef1f5",
            fg="#526075",
            anchor="w",
            font=("Microsoft YaHei", 8),
        ).pack(fill="both", expand=True, padx=(5, 0))

        tk.Frame(header_parent, bg="#cfd5df", height=1).pack(fill="x")

        for category in self.categories:
            row_bg = self._category_row_background(category)
            name_fg, count_fg = self._category_row_foregrounds(category)
            row_frame = tk.Frame(self.legend_frame, bg=row_bg, height=26)
            self.legend_row_widgets[category] = row_frame
            row_frame.pack(fill="x")
            row_frame.pack_propagate(False)

            select_cell = tk.Frame(row_frame, bg=row_bg, width=select_width)
            select_cell.pack(side="left", fill="y")
            select_cell.pack_propagate(False)
            if category != "未分类":
                selected_var = tk.BooleanVar(
                    value=category in self.selected_categories
                )
                self.legend_select_vars[category] = selected_var
                tk.Checkbutton(
                    select_cell,
                    variable=selected_var,
                    command=lambda c=category, v=selected_var:
                        self._set_category_selected(c, bool(v.get())),
                    bg=row_bg,
                    activebackground=row_bg,
                    bd=0,
                    highlightthickness=0,
                ).pack(expand=True)

            visible_cell = tk.Frame(row_frame, bg=row_bg, width=visible_width)
            visible_cell.pack(side="left", fill="y")
            visible_cell.pack_propagate(False)
            hidden = category in self.hidden_categories
            eye_canvas = tk.Canvas(
                visible_cell,
                width=22,
                height=20,
                bg=row_bg,
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )
            eye_canvas.pack(expand=True)
            self._draw_eye_icon(eye_canvas, hidden)
            eye_canvas.bind(
                "<Button-1>",
                lambda _event, c=category, canvas=eye_canvas:
                    self.toggle_category(c, canvas),
            )
            self.legend_eye_canvases[category] = eye_canvas

            color_cell = tk.Frame(row_frame, bg=row_bg, width=color_width)
            color_cell.pack(side="left", fill="y")
            color_cell.pack_propagate(False)
            color_canvas = tk.Canvas(
                color_cell,
                width=14,
                height=14,
                bg=row_bg,
                highlightthickness=0,
                bd=0,
            )
            color_canvas.pack(expand=True)
            color_canvas.create_rectangle(
                2, 2, 12, 12,
                fill=self.category_colors.get(category, "#808080"),
                outline="#30394c",
                width=1,
            )
            self.legend_color_canvases[category] = color_canvas

            side_cell = tk.Frame(row_frame, bg=row_bg, width=side_width)
            side_cell.pack(side="right", fill="y")
            side_cell.pack_propagate(False)
            side_control = self._create_category_side_control(side_cell, category)
            side_control.pack(expand=True)
            rendered_side = getattr(self, "category_side_states", {}).get(category)
            if category == "未分类":
                rendered_side = "unrestricted"
            elif rendered_side not in {"top", "bottom", "unrestricted"}:
                rendered_sides = {
                    row["side"] for row in getattr(self, "rows", [])
                    if row["category"] == category
                }
                rendered_side = (
                    next(iter(rendered_sides))
                    if len(rendered_sides) == 1 else "unrestricted"
                )
            side_control._rendered_side_state = (rendered_side, category == "未分类")
            self.legend_side_controls[category] = side_control

            count_cell = tk.Frame(row_frame, bg=row_bg, width=count_width)
            count_cell.pack(side="right", fill="y")
            count_cell.pack_propagate(False)
            count_label = tk.Label(
                count_cell,
                text=str(counts.get(category, 0)),
                bg=row_bg,
                fg=count_fg,
                font=("Microsoft YaHei", 8),
            )
            count_label.pack(expand=True)
            self.legend_count_labels[category] = count_label

            name_cell = tk.Frame(row_frame, bg=row_bg, width=150)
            name_cell.pack(side="left", fill="y")
            name_cell.pack_propagate(False)
            name_label = tk.Label(
                name_cell,
                text=category,
                bg=row_bg,
                fg=name_fg,
                anchor="w",
                font=("Microsoft YaHei", 8),
            )
            name_label.pack(fill="both", expand=True, padx=(3, 2))
            if category != "未分类":
                name_label.bind(
                    "<Double-1>",
                    lambda _event, c=category: self._begin_category_rename(c),
                )
            self.legend_name_cells[category] = name_cell
            self.legend_name_labels[category] = name_label
            self.legend_field_widgets[category] = {
                "display": visible_cell,
                "name": name_cell,
                "count": count_cell,
                "side": side_cell,
            }

        self.legend_frame.update_idletasks()
        self.update_legend_scrollregion()
        self._refresh_category_header_eye()
        self._refresh_all_category_row_visuals()
        if hasattr(self, "_align_category_search_control_to_legend"):
            self.after_idle(self._align_category_search_control_to_legend)

    def _refresh_category_side_control(self, category):
        canvas = getattr(self, "legend_side_controls", {}).get(category)
        if canvas is None:
            return
        try:
            if not canvas.winfo_exists():
                return
        except tk.TclError:
            return

        width, height = 93, 25
        segment_width = width // 3
        is_system_category = category == "未分类"
        current = getattr(self, "category_side_states", {}).get(category)
        if is_system_category:
            current = "unrestricted"
        elif current not in {"top", "bottom", "unrestricted"}:
            sides = {
                row["side"] for row in getattr(self, "rows", [])
                if row["category"] == category
            }
            current = next(iter(sides)) if len(sides) == 1 else "unrestricted"

        visual_state = (current, is_system_category)
        if getattr(canvas, "_rendered_side_state", None) == visual_state:
            return

        canvas.delete("all")
        for index, state in enumerate(("top", "bottom", "unrestricted")):
            left = index * segment_width
            self._draw_category_side_icon(
                canvas, left, 0, segment_width, height,
                state, state == current,
                disabled=is_system_category and state in {"top", "bottom"},
            )
            if index:
                canvas.create_line(left, 0, left, height, fill="#c7ceda", width=1)
        canvas._rendered_side_state = visual_state

    def refresh_legend_incremental(self):
        """原位刷新分类表；只有分类结构变化时才完整重建。"""
        self.categories = ["未分类"] + [
            name for name in getattr(self, "categories", [])
            if name != "未分类"
        ]
        self.category_side_states["未分类"] = "unrestricted"

        row_widgets = getattr(self, "legend_row_widgets", {})
        count_labels = getattr(self, "legend_count_labels", {})
        if list(row_widgets.keys()) != self.categories:
            self.render_legend()
            return

        counts = {category: 0 for category in self.categories}
        for row in getattr(self, "rows", []):
            category = row["category"]
            counts[category] = counts.get(category, 0) + 1
        self.legend_category_counts = counts

        self.selected_categories.intersection_update(
            {name for name in self.categories if name != "未分类"}
        )

        # 先更新文本/选择变量，再统一刷新行底色。整个过程不销毁任何行控件。
        for category in self.categories:
            label = count_labels.get(category)
            if label is not None:
                try:
                    if label.winfo_exists():
                        label.configure(text=str(counts.get(category, 0)))
                except tk.TclError:
                    pass
            selected_var = getattr(self, "legend_select_vars", {}).get(category)
            if selected_var is not None:
                selected_var.set(category in self.selected_categories)

        self._refresh_category_select_all_state()
        self._refresh_all_category_row_visuals()

        for category in self.categories:
            eye = getattr(self, "legend_eye_canvases", {}).get(category)
            if eye is not None:
                try:
                    self._draw_eye_icon(eye, category in self.hidden_categories)
                except tk.TclError:
                    pass

            color = getattr(self, "legend_color_canvases", {}).get(category)
            if color is not None:
                try:
                    color.delete("all")
                    color.create_rectangle(
                        2, 2, 12, 12,
                        fill=self.category_colors.get(category, "#808080"),
                        outline="#30394c", width=1,
                    )
                except tk.TclError:
                    pass

            self._refresh_category_side_control(category)

        self.update_legend_scrollregion()

    def toggle_category_from_label(self, category):
        variable = self.category_vars[category]
        variable.set(not variable.get())
        self.on_checkbox_changed(category)

    def toggle_category(self, category, eye_canvas=None):
        if category in self.hidden_categories:
            self.hidden_categories.discard(category)
        else:
            self.hidden_categories.add(category)

        # Clicking the eye changes only visibility. Rebuilding the complete
        # legend destroys/recreates every Checkbutton and causes the whole
        # selection column to flash on Windows. Update only this eye instead.
        if eye_canvas is not None:
            try:
                eye_canvas.delete("all")
                self._draw_eye_icon(
                    eye_canvas, category in self.hidden_categories
                )
            except tk.TclError:
                pass
        self._refresh_category_header_eye()
        if getattr(self, "category_search_focus_category", None) == category:
            self._apply_category_search_field_highlight(category)
        self.render()

    def visible_rows(self):
        return [
            row for row in self.rows
            if row["category"] not in self.hidden_categories
        ]
