"""LegendMixin：按功能拆分自原始桌面时间轴工具。"""

import tkinter as tk


class LegendMixin:
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

    def render_legend(self):
        for child in self.legend_frame.winfo_children():
            child.destroy()

        self.category_vars = {}

        for category in self.categories:
            side = next(
                (row["side"] for row in self.rows if row["category"] == category),
                "top",
            )
            variable = tk.BooleanVar(value=category not in self.hidden_categories)
            self.category_vars[category] = variable

            row_frame = tk.Frame(self.legend_frame, bg="#f7f8fa")
            row_frame.pack(fill="x", pady=2)

            check = tk.Checkbutton(
                row_frame,
                variable=variable,
                command=lambda name=category: self.on_checkbox_changed(name),
                bg="#f7f8fa",
                activebackground="#f7f8fa",
                selectcolor=self.category_colors[category],
                cursor="hand2",
                bd=0,
                highlightthickness=0,
            )
            check.pack(side="left")

            name_label = tk.Label(
                row_frame,
                text=category,
                font=("Microsoft YaHei", 9),
                bg="#f7f8fa",
                fg="#30394c",
                cursor="hand2",
            )
            name_label.pack(side="left", padx=(4, 0))

            side_label = tk.Label(
                row_frame,
                text="上方" if side == "top" else "下方",
                font=("Microsoft YaHei", 8),
                bg="#f7f8fa",
                fg="#7a8391",
                cursor="hand2",
            )
            side_label.pack(side="right")

            name_label.bind("<Button-1>", lambda _event, name=category: self.toggle_category_from_label(name))
            side_label.bind("<Button-1>", lambda _event, name=category: self.toggle_category_from_label(name))

        # 必须等待 Tk 完成本轮尺寸计算后，再计算真实内容高度。
        self.legend_canvas.coords(self.legend_window, 0, 0)
        self.after_idle(self.finish_legend_layout)

    def finish_legend_layout(self):
        self.update_idletasks()
        self.update_legend_scrollregion()
        self.legend_canvas.yview_moveto(0.0)

    def on_checkbox_changed(self, category):
        variable = self.category_vars[category]
        if variable.get():
            self.hidden_categories.discard(category)
        else:
            self.hidden_categories.add(category)
        self.render()

    def toggle_category_from_label(self, category):
        variable = self.category_vars[category]
        variable.set(not variable.get())
        self.on_checkbox_changed(category)

    def visible_rows(self):
        return [
            row for row in self.rows
            if row["category"] not in self.hidden_categories
        ]
