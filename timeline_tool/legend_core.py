"""分类区滚动、side、新建与删除。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendCoreMixin:
    def resize_legend_window(self, event):
        self.legend_canvas.itemconfigure(
            self.legend_window,
            width=max(1, event.width),
        )
        self.legend_canvas.coords(self.legend_window, 0, 0)
        self.update_legend_scrollregion()

    def update_legend_scrollregion(self, _event=None):
        self.legend_frame.update_idletasks()
        self.legend_canvas.coords(self.legend_window, 0, 0)

        bounds = self.legend_canvas.bbox(self.legend_window)
        content_height = max(1, bounds[3] if bounds else 1)
        canvas_width = max(1, self.legend_canvas.winfo_width())

        self.legend_content_height = content_height
        self.legend_canvas.configure(
            scrollregion=(0, 0, canvas_width, content_height),
        )
        self.clamp_legend_view()

    def legend_scroll_limits(self):
        content_height = max(
            1,
            getattr(self, "legend_content_height", 1),
        )
        viewport_height = max(1, self.legend_canvas.winfo_height())
        max_top = max(0, content_height - viewport_height)
        return content_height, max_top

    def set_legend_top(self, target_top):
        content_height, max_top = self.legend_scroll_limits()
        target_top = max(0, min(float(target_top), float(max_top)))
        self.legend_canvas.yview_moveto(target_top / content_height)

    def clamp_legend_view(self):
        try:
            current_top = self.legend_canvas.canvasy(0)
            self.set_legend_top(current_top)
        except tk.TclError:
            pass

    def on_legend_scrollbar(self, *args):
        if not args:
            return

        content_height, max_top = self.legend_scroll_limits()

        if args[0] == "moveto":
            requested_top = float(args[1]) * content_height
            self.set_legend_top(min(requested_top, max_top))
            return

        if args[0] == "scroll":
            amount = int(args[1])
            mode = args[2]
            viewport_height = max(1, self.legend_canvas.winfo_height())
            step = viewport_height * 0.9 if mode == "pages" else 24
            current_top = self.legend_canvas.canvasy(0)
            self.set_legend_top(current_top + amount * step)

    def pointer_is_over_legend(self):
        try:
            pointer_x = self.winfo_pointerx()
            pointer_y = self.winfo_pointery()
            left = self.legend_canvas.winfo_rootx()
            top = self.legend_canvas.winfo_rooty()
            right = left + self.legend_canvas.winfo_width()
            bottom = top + self.legend_canvas.winfo_height()
            return left <= pointer_x < right and top <= pointer_y < bottom
        except tk.TclError:
            return False

    def on_global_mousewheel(self, event):
        if not self.pointer_is_over_legend():
            return None

        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        elif event.delta > 0:
            direction = -1
        elif event.delta < 0:
            direction = 1
        else:
            return "break"

        current_top = self.legend_canvas.canvasy(0)
        self.set_legend_top(current_top + direction * 24)
        return "break"

    @staticmethod
    def _category_side_label(state):
        return {
            "top": "上侧",
            "bottom": "下侧",
            "unrestricted": "无限制",
        }.get(state, "无限制")

    def _draw_category_side_icon(self, canvas, left, top, width, height, state, active, disabled=False):
        """在一个三段格内画“时间轴 + 事件块”图标。"""
        bg = "#dbeafe" if active else "white"
        fg = "#b8bec8" if disabled else ("#2563eb" if active else "#64748b")
        canvas.create_rectangle(
            left, top, left + width, top + height,
            fill=bg, outline="", tags=(f"side_{state}",)
        )

        cx = left + width / 2
        cy = top + height / 2
        line_left = cx - 8
        line_right = cx + 8
        canvas.create_line(
            line_left, cy, line_right, cy,
            fill=fg, width=1, tags=(f"side_{state}",)
        )

        block_w = 5
        block_h = 5
        if state in {"top", "unrestricted"}:
            canvas.create_rectangle(
                cx - block_w / 2, cy - 7,
                cx + block_w / 2, cy - 7 + block_h,
                fill=fg, outline=fg, tags=(f"side_{state}",)
            )
        if state in {"bottom", "unrestricted"}:
            canvas.create_rectangle(
                cx - block_w / 2, cy + 2,
                cx + block_w / 2, cy + 2 + block_h,
                fill=fg, outline=fg, tags=(f"side_{state}",)
            )

    def _create_category_side_control(self, parent, category):
        width, height = 93, 25
        segment_width = width // 3
        is_system_category = category == "未分类"
        canvas = tk.Canvas(
            parent,
            width=width,
            height=height,
            bg="white",
            highlightthickness=1,
            highlightbackground="#c7ceda",
            bd=0,
            cursor="arrow" if is_system_category else "hand2",
        )

        current = getattr(self, "category_side_states", {}).get(category)
        if is_system_category:
            current = "unrestricted"
        elif current not in {"top", "bottom", "unrestricted"}:
            sides = {
                row["side"]
                for row in self.rows
                if row["category"] == category
            }
            current = next(iter(sides)) if len(sides) == 1 else "unrestricted"

        states = ("top", "bottom", "unrestricted")
        for index, state in enumerate(states):
            left = index * segment_width
            self._draw_category_side_icon(
                canvas, left, 0, segment_width, height,
                state, state == current,
                disabled=is_system_category and state in {"top", "bottom"},
            )
            if index:
                canvas.create_line(
                    left, 0, left, height,
                    fill="#c7ceda", width=1
                )

        def on_click(event):
            if is_system_category:
                return
            index = min(2, max(0, int(event.x // segment_width)))
            self.change_category_side(category, states[index])

        canvas.bind("<Button-1>", on_click)

        # 三段控件使用自己的悬浮 tooltip。
        # 不复用面板 i 标的 tooltip 生命周期，避免 Canvas item 的
        # Enter/Leave 与 widget 级指针检测互相干扰而留下“永久”提示。
        hover = {"window": None, "state": None}

        def hide_side_tooltip(_event=None):
            window = hover["window"]
            if window is not None:
                try:
                    window.destroy()
                except tk.TclError:
                    pass
            hover["window"] = None
            hover["state"] = None

        def show_side_tooltip(state):
            if hover["state"] == state and hover["window"] is not None:
                return

            hide_side_tooltip()
            tooltip = tk.Toplevel(self)
            tooltip.overrideredirect(True)
            tooltip.attributes("-topmost", True)
            tk.Label(
                tooltip,
                text=self._category_side_label(state),
                justify="left",
                bg="white",
                fg="#293247",
                relief="solid",
                borderwidth=1,
                padx=10,
                pady=7,
                font=("Microsoft YaHei", 9),
            ).pack()

            self.update_idletasks()
            x = self.winfo_pointerx() + 12
            y = self.winfo_pointery() + 14
            tooltip.geometry(f"+{x}+{y}")
            hover["window"] = tooltip
            hover["state"] = state

        def on_motion(event):
            index = min(2, max(0, int(event.x // segment_width)))
            show_side_tooltip(states[index])

        canvas.bind("<Motion>", on_motion)
        canvas.bind("<Leave>", hide_side_tooltip)
        canvas.bind("<Button-1>", lambda event: (hide_side_tooltip(), on_click(event))[1])

        return canvas

    def _category_side_confirmation_text(self, category, old_state, new_state):
        old_label = self._category_side_label(old_state)
        new_label = self._category_side_label(new_state)

        if old_state in {"top", "bottom"} and new_state in {"top", "bottom"}:
            return (
                f"分类“{category}”当前 side 为{old_label}。"
                f"是否将该分类的 side 改为{new_label}？\n\n"
                f"是：分类“{category}”的 side 从{old_label}改为{new_label}；"
                f"分类内所有事件的 side 均改为{new_label}。\n"
                f"否：分类“{category}”及分类内事件的 side 均保持不变。"
            )

        if old_state in {"top", "bottom"} and new_state == "unrestricted":
            return (
                f"分类“{category}”当前 side 为{old_label}。"
                "是否将该分类的 side 改为“无限制”？\n\n"
                f"是：分类“{category}”的 side 从{old_label}改为“无限制”；"
                "只放宽分类的 side 约束，分类内现有事件保留原 side。\n"
                f"否：分类“{category}”的 side 保持{old_label}，"
                "分类内事件保留原 side。"
            )

        if old_state == "unrestricted" and new_state in {"top", "bottom"}:
            return (
                f"分类“{category}”当前 side 为“无限制”。"
                f"是否将该分类的 side 改为{new_label}？\n\n"
                f"是：分类“{category}”的 side 从“无限制”改为{new_label}；"
                f"分类内所有事件的 side 均改为{new_label}。\n"
                "否：分类“{category}”的 side 保持“无限制”，"
                "分类内事件保留原 side。"
            )

        return ""

    def change_category_side(self, category, new_state):
        if category == "未分类":
            self.category_side_states["未分类"] = "unrestricted"
            return

        old_state = getattr(self, "category_side_states", {}).get(category)
        if old_state not in {"top", "bottom", "unrestricted"}:
            sides = {
                row["side"]
                for row in self.rows
                if row["category"] == category
            }
            old_state = next(iter(sides)) if len(sides) == 1 else "unrestricted"

        if new_state == old_state:
            return

        prompt = self._category_side_confirmation_text(
            category, old_state, new_state
        )
        if not messagebox.askyesno("修改分类 side", prompt):
            return

        history_before = (
            self._capture_global_snapshot()
            if hasattr(self, "_capture_global_snapshot") else None
        )
        self.category_side_states[category] = new_state

        # 单侧 -> 无限制只改变分类约束，不改变事件。
        if new_state in {"top", "bottom"}:
            for row in self.rows:
                if row["category"] == category:
                    row["side"] = new_state

            # CSV 表格保留每个事件原有的语言/词形风格。
            category_field = self._csv_category_field()
            side_field = self._csv_side_field()
            if category_field and side_field:
                for row in self.csv_model_rows:
                    row_category = str(row.get(category_field, "")).strip() or "未分类"
                    if row_category != category:
                        continue
                    old_display = row.get(side_field, "")
                    row[side_field] = self._side_display_for_semantic(
                        new_state, old_display
                    )
                self._render_csv_grid()

        self.has_unexported_csv_edits = True
        self.render_legend()
        self.render()
        self.status_var.set(
            f"已将分类“{category}”的 side 从"
            f"{self._category_side_label(old_state)}改为"
            f"{self._category_side_label(new_state)}"
        )
        if hasattr(self, "_commit_global_history"):
            self._commit_global_history(
                history_before,
                f"修改分类 side：{category}",
                clear_csv_local_history=True,
            )

    def _next_category_color(self):
        used = set(getattr(self, "category_colors", {}).values())
        for color in PALETTE:
            if color not in used:
                return color
        index = max(0, len(getattr(self, "categories", [])) - 1)
        return PALETTE[index % len(PALETTE)]

    def create_category(self):
        dialog = tk.Toplevel(self)
        dialog.title("新建分类")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()

        body = tk.Frame(dialog, bg="#f7f8fa", padx=18, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="分类名",
            bg="#f7f8fa",
            fg="#30394c",
            font=("Microsoft YaHei", 9),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        name_var = tk.StringVar()
        name_entry = tk.Entry(
            body,
            textvariable=name_var,
            width=28,
            font=("Microsoft YaHei", 9),
        )
        name_entry.grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8))

        tk.Label(
            body,
            text="side",
            bg="#f7f8fa",
            fg="#30394c",
            font=("Microsoft YaHei", 9),
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        side_var = tk.StringVar(value="unrestricted")
        for column, (text, value) in enumerate(
            (("上侧", "top"), ("下侧", "bottom"), ("无限制", "unrestricted")),
            start=1,
        ):
            tk.Radiobutton(
                body,
                text=text,
                value=value,
                variable=side_var,
                bg="#f7f8fa",
                activebackground="#f7f8fa",
                font=("Microsoft YaHei", 9),
            ).grid(row=1, column=column, sticky="w", padx=(0, 8), pady=(0, 12))

        button_row = tk.Frame(body, bg="#f7f8fa")
        button_row.grid(row=2, column=0, columnspan=4, sticky="e")

        def submit(_event=None):
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("无法新建分类", "分类名不能为空。", parent=dialog)
                name_entry.focus_set()
                return

            existing = {
                str(category).strip().casefold()
                for category in getattr(self, "categories", [])
            }
            if name.casefold() in existing:
                messagebox.showwarning(
                    "无法新建分类",
                    f"分类“{name}”已经存在。",
                    parent=dialog,
                )
                name_entry.focus_set()
                name_entry.selection_range(0, tk.END)
                return

            history_before = (
                self._capture_global_snapshot()
                if hasattr(self, "_capture_global_snapshot") else None
            )
            self.categories.append(name)
            self.category_side_states[name] = side_var.get()
            self.category_colors[name] = self._next_category_color()
            self.hidden_categories.discard(name)

            dialog.grab_release()
            dialog.destroy()
            self.render_legend()
            self.render()
            self.status_var.set(
                f"已新建分类“{name}”，side 为"
                f"{self._category_side_label(self.category_side_states[name])}"
            )
            if hasattr(self, "_commit_global_history"):
                self._commit_global_history(
                    history_before,
                    f"新建分类：{name}",
                )

        tk.Button(
            button_row,
            text="取消",
            command=dialog.destroy,
            font=("Microsoft YaHei", 9),
            padx=10,
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            button_row,
            text="创建",
            command=submit,
            font=("Microsoft YaHei", 9),
            padx=10,
        ).pack(side="right")

        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_reqheight()) // 3)
        dialog.geometry(f"+{x}+{y}")
        name_entry.focus_set()

    def delete_selected_categories(self):
        selected = [
            category for category in getattr(self, "categories", [])
            if category != "未分类"
            and category in getattr(self, "selected_categories", set())
        ]
        if not selected:
            messagebox.showwarning("删除分类", "请先勾选要删除的分类。")
            return

        counts = {category: 0 for category in selected}
        for row in getattr(self, "rows", []):
            category = str(row.get("category", "")).strip() or "未分类"
            if category in counts:
                counts[category] += 1

        total_events = sum(counts.values())
        has_events = total_events > 0

        dialog = tk.Toplevel(self)
        dialog.title("删除分类")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.grab_set()

        body = tk.Frame(dialog, bg="#f7f8fa", padx=18, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(
            body,
            text="确认删除以下分类？",
            bg="#f7f8fa",
            fg="#30394c",
            font=("Microsoft YaHei", 10, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        table = tk.Frame(
            body,
            bg="#f7f8fa",
            highlightthickness=1,
            highlightbackground="#d7dce5",
        )
        table.pack(fill="x")
        table.grid_columnconfigure(0, weight=1, minsize=230)
        table.grid_columnconfigure(1, minsize=80)

        for column, text in enumerate(("分类名", "事件数")):
            tk.Label(
                table,
                text=text,
                bg="#eef1f5",
                fg="#526075",
                font=("Microsoft YaHei", 8),
                anchor="w" if column == 0 else "center",
                padx=8,
                pady=4,
            ).grid(row=0, column=column, sticky="nsew")
        tk.Frame(table, bg="#cfd5df", height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew"
        )

        for index, category in enumerate(selected, start=2):
            tk.Label(
                table,
                text=category,
                bg="#f7f8fa",
                fg="#30394c",
                font=("Microsoft YaHei", 9),
                anchor="w",
                padx=8,
                pady=4,
            ).grid(row=index, column=0, sticky="nsew")
            tk.Label(
                table,
                text=str(counts[category]),
                bg="#f7f8fa",
                fg="#30394c",
                font=("Microsoft YaHei", 9),
                anchor="center",
                padx=8,
                pady=4,
            ).grid(row=index, column=1, sticky="nsew")

        tk.Label(
            body,
            text=f"共选择 {len(selected)} 个分类，其中包含 {total_events} 个事件。",
            bg="#f7f8fa",
            fg="#30394c",
            font=("Microsoft YaHei", 9),
            anchor="w",
        ).pack(fill="x", pady=(10, 4))

        notice = (
            "所选分类中包含非空分类。继续删除将同时删除这些分类中的所有事件；\n"
            "如需保留相关事件，请先使用“事件迁移”将其移至其它分类。"
            if has_events else
            "所选分类均为空分类，删除后不会影响任何事件。"
        )
        tk.Label(
            body,
            text=notice,
            bg="#f7f8fa",
            fg="#526075",
            font=("Microsoft YaHei", 9),
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(0, 12))

        buttons = tk.Frame(body, bg="#f7f8fa")
        buttons.pack(fill="x")

        def cancel(_event=None):
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def confirm(_event=None):
            cancel()
            self.delete_categories_from_data(selected)

        tk.Button(
            buttons,
            text="取消",
            command=cancel,
            font=("Microsoft YaHei", 9),
            padx=10,
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            buttons,
            text="确认删除",
            command=confirm,
            font=("Microsoft YaHei", 9),
            padx=10,
        ).pack(side="right")

        dialog.bind("<Return>", confirm)
        dialog.bind("<Escape>", cancel)
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(
            0, (self.winfo_width() - dialog.winfo_reqwidth()) // 2
        )
        y = self.winfo_rooty() + max(
            0, (self.winfo_height() - dialog.winfo_reqheight()) // 3
        )
        dialog.geometry(f"+{x}+{y}")
