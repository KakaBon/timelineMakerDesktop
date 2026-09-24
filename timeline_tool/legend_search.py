"""分类筛选、查找与定位。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendSearchMixin:
    def _category_search_icon_canvas(self, parent, width=118, height=23):
        canvas = tk.Canvas(
            parent, width=width, height=height, bg="white",
            highlightthickness=0, bd=0, cursor="arrow",
        )
        return canvas

    def _draw_search_eye(self, canvas, hidden=False, bg="white"):
        canvas.delete("all")
        canvas.configure(bg=bg)
        fg = "#a7adb7" if hidden else "#526075"
        w = max(1, int(canvas.winfo_width()), int(canvas.cget("width")))
        h = max(1, int(canvas.winfo_height()), int(canvas.cget("height")))
        cx, cy = w / 2, h / 2
        canvas.create_oval(cx - 9, cy - 5, cx + 9, cy + 5, outline=fg, width=1.5)
        canvas.create_oval(cx - 2.2, cy - 2.2, cx + 2.2, cy + 2.2, fill=fg, outline=fg)
        if hidden:
            canvas.create_line(cx - 10, cy + 7, cx + 10, cy - 7, fill=fg, width=1.8)

    def _draw_search_side(self, canvas, state, bg="white"):
        canvas.delete("all")
        canvas.configure(bg=bg)
        fg = "#64748b"
        w = max(1, int(canvas.winfo_width()), int(canvas.cget("width")))
        h = max(1, int(canvas.winfo_height()), int(canvas.cget("height")))
        cx, cy = w / 2, h / 2
        canvas.create_line(cx - 10, cy, cx + 10, cy, fill=fg, width=1)
        if state in {"top", "unrestricted"}:
            canvas.create_rectangle(cx - 2.5, cy - 7, cx + 2.5, cy - 2, fill=fg, outline=fg)
        if state in {"bottom", "unrestricted"}:
            canvas.create_rectangle(cx - 2.5, cy + 2, cx + 2.5, cy + 7, fill=fg, outline=fg)

    def build_category_search_controls(self, parent):
        self.category_search_field_var = tk.StringVar(value="分类名")
        self.category_search_value_var = tk.StringVar(value="")
        self.category_search_matches = []
        self.category_search_index = -1

        # FilterSearchControl：一个外框内完整包含
        # [筛选字段▼ | 值 | 查找 | ↑ | ↓ | 0/0]
        shell = self._integrated_shell(parent)
        shell.pack(side="left")
        self.category_search_shell = shell

        # 筛选字段也使用与右侧图标值下拉框相同的手搓结构，
        # 避免 ttk.Combobox 原生边框/箭头与一体式控件不一致。
        # 分类筛选字段进一步收紧：箭头保留独立固定宽度，
        # 文本本体只保留很小的左右呼吸空间。
        field_segment_width = 72
        dropdown_arrow_width = 22
        self.category_search_field_base_width = field_segment_width
        self.category_search_value_base_width = 82
        self.category_search_dropdown_arrow_width = dropdown_arrow_width
        self.category_search_field = tk.Frame(
            shell, bg="white", bd=0, highlightthickness=0,
            width=field_segment_width, height=21,
        )
        self.category_search_field.pack(side="left", fill="y", padx=1, pady=1)
        self.category_search_field.pack_propagate(False)

        # 文本与箭头分成两个真正独立的几何区。文本只在不包含箭头的
        # 左侧内容区内居中，因此收窄后仍不会被箭头挤偏。
        self.category_search_field_label = tk.Label(
            self.category_search_field,
            textvariable=self.category_search_field_var,
            anchor="center",
            font=("Microsoft YaHei", 8),
            bg="white",
            fg="#253044",
            padx=0,
        )
        self.category_search_field_label.place(
            x=0, y=0,
            width=field_segment_width - dropdown_arrow_width,
            height=21,
        )

        self.category_search_field_arrow = tk.Button(
            self.category_search_field,
            text="▼",
            font=("Microsoft YaHei", 7),
            bg="white", fg="#263247",
            activebackground="#edf2f7", activeforeground="#263247",
            relief="flat", bd=0, padx=3, pady=0,
            highlightthickness=0, takefocus=False,
            command=self._open_category_search_field_popup,
        )
        self.category_search_field_arrow.place(
            x=field_segment_width - dropdown_arrow_width, y=0,
            width=dropdown_arrow_width, height=21,
        )
        self.category_search_field_label.bind(
            "<Button-1>", lambda _event: self._open_category_search_field_popup()
        )
        self.category_search_field_popup = None

        self._integrated_separator(shell).pack(side="left", fill="y", pady=1)

        # 固定值区宽度；文本值和图标值切换时整个控件绝不改变尺寸。
        # 文本值与图标值继续共用同一固定宽度；只压缩内容两侧空白。
        # 82 px 仍可完整容纳事件数 placeholder，同时显著缩短图标值框。
        value_segment_width = self.category_search_value_base_width
        self.category_search_value_host = tk.Frame(
            shell, bg="white", width=value_segment_width, height=21
        )
        self.category_search_value_host.pack(side="left", fill="y", pady=1)
        self.category_search_value_host.pack_propagate(False)

        self.category_search_value_entry_box = self._integrated_entry(
            self.category_search_value_host,
            self.category_search_value_var,
            width=12,
            clear_command=self.clear_category_search,
        )
        # 分类筛选文本值框会被外层对齐逻辑压缩/扩展。tk.pack 在窄宽度下
        # 会优先保留 Entry 的请求宽度，导致最右侧清除按钮被裁掉。这里仅对
        # 这个值框改用显式几何布局：清除按钮始终固定在右缘，Entry 使用剩余
        # 宽度，因此无论字段/值段被重新分配到多宽，× 都会完整显示。
        self.category_search_value_entry_box.entry.pack_forget()
        if getattr(self.category_search_value_entry_box, "clear_button", None) is not None:
            self.category_search_value_entry_box.clear_button.pack_forget()
        self.category_search_value_entry_box.bind(
            "<Configure>", self._layout_category_search_text_value, add="+"
        )
        self.category_search_value_entry_box.entry.bind(
            "<Return>", lambda _event: self.execute_category_search()
        )
        self.category_search_value_entry_box.entry.bind(
            "<FocusIn>", self._on_category_search_value_focus_in, add="+"
        )
        self.category_search_value_entry_box.entry.bind(
            "<Button-1>", self._on_category_search_value_click, add="+"
        )
        self.category_search_value_entry_box.entry.bind(
            "<FocusOut>", self._on_category_search_value_focus_out, add="+"
        )

        # 保留原有图标选择逻辑，只去掉独立外框，使其成为整体值区的一部分。
        self.category_search_icon_shell = tk.Frame(
            self.category_search_value_host, bg="white", bd=0, highlightthickness=0
        )
        self.category_search_icon_inner = tk.Frame(
            self.category_search_icon_shell, bg="white"
        )
        self.category_search_icon_inner.pack(fill="both", expand=True)
        self.category_search_icon_canvas = self._category_search_icon_canvas(
            self.category_search_icon_inner,
            width=value_segment_width - dropdown_arrow_width,
            height=21,
        )
        self.category_search_icon_canvas.place(
            x=0, y=0,
            width=value_segment_width - dropdown_arrow_width,
            height=21,
        )
        self.category_search_icon_arrow = tk.Button(
            self.category_search_icon_inner,
            text="▼",
            font=("Microsoft YaHei", 7),
            bg="white", fg="#263247",
            activebackground="#edf2f7", activeforeground="#263247",
            relief="flat", bd=0, padx=4, pady=0,
            highlightthickness=0, takefocus=False,
            command=self._open_category_search_icon_popup,
        )
        self.category_search_icon_arrow.place(
            x=value_segment_width - dropdown_arrow_width, y=0,
            width=dropdown_arrow_width, height=21,
        )
        self.category_search_icon_canvas.bind(
            "<Button-1>", lambda _event: self._open_category_search_icon_popup()
        )
        self.category_search_icon_canvas.bind(
            "<Configure>", lambda _event: self._paint_category_search_icon_value(), add="+"
        )

        self.category_search_placeholder_active = False
        self.category_search_icon_popup = None
        self.category_search_icon_choices = []
        self._rebuild_category_search_value_control()

        # 两个手搓下拉框都采用与原生 Combobox 一致的收起行为：
        # 菜单展开后，再点触发区、选择任意项或点击页面其它位置都会关闭。
        if not getattr(self, "_category_search_popup_global_binding_installed", False):
            self.bind_all(
                "<Button-1>",
                self._on_category_search_global_click,
                add="+",
            )
            self._category_search_popup_global_binding_installed = True

        self._integrated_separator(shell).pack(side="left", fill="y", pady=1)
        self._integrated_icon_action(
            shell, "search", self.execute_category_search,
            tooltip_text="查找", width=25,
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(shell).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            shell, "↑", self.show_previous_category_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(shell).pack(side="left", fill="y", pady=1)
        self._integrated_action(
            shell, "↓", self.show_next_category_search_match, width=1
        ).pack(side="left", fill="y", pady=1)
        self._integrated_separator(shell).pack(side="left", fill="y", pady=1)

        self.category_search_counter_var = tk.StringVar(value="0/0")
        self._integrated_counter(
            shell, self.category_search_counter_var
        ).pack(side="left", fill="y", padx=(0, 1), pady=1)

        # 等下级分类控制区完成布局后，把整个筛选查找控件的右边界
        # 对齐到下级控制区的右边界。多出来的宽度只分给字段和值的
        # 内容区；两个箭头区及查找/上下/计数区保持现有尺寸。
        self.after_idle(self._align_category_search_control_to_legend)

    def _layout_category_search_text_value(self, event=None):
        """让分类筛选文本值框中的清除按钮始终完整贴在右缘。"""
        box = getattr(self, "category_search_value_entry_box", None)
        if box is None:
            return
        entry = getattr(box, "entry", None)
        clear = getattr(box, "clear_button", None)
        if entry is None:
            return
        try:
            width = max(1, int(getattr(event, "width", 0) or box.winfo_width()))
            height = max(1, int(getattr(event, "height", 0) or box.winfo_height()))
            clear_width = 17 if clear is not None else 0
            # Entry 左侧保留与其它一体式文本框一致的 4 px 呼吸空间；
            # 右侧只留 1 px，清除按钮自己占固定宽度。
            entry.place(
                x=4, y=0,
                width=max(1, width - clear_width - 5),
                height=height,
            )
            if clear is not None:
                clear.place(
                    x=max(0, width - clear_width), y=0,
                    width=clear_width, height=height,
                )
                clear.lift()
        except tk.TclError:
            pass

    def _align_category_search_control_to_legend(self, retry=0):
        shell = getattr(self, "category_search_shell", None)
        field = getattr(self, "category_search_field", None)
        value_host = getattr(self, "category_search_value_host", None)
        scrollbar = getattr(self, "legend_scrollbar", None)
        if any(widget is None for widget in (shell, field, value_host, scrollbar)):
            if retry < 8:
                self.after(20, lambda: self._align_category_search_control_to_legend(retry + 1))
            return

        try:
            self.update_idletasks()
            shell_width = shell.winfo_width()
            scrollbar_width = scrollbar.winfo_width()
            if shell_width <= 2 or scrollbar_width <= 2:
                if retry < 8:
                    self.after(20, lambda: self._align_category_search_control_to_legend(retry + 1))
                return

            target_right = scrollbar.winfo_rootx() + scrollbar_width
            shell_left = shell.winfo_rootx()
            current_right = shell_left + shell_width
            extra = target_right - current_right
            if extra <= 0:
                return

            field_width = self.category_search_field_base_width + extra // 2
            value_width = self.category_search_value_base_width + extra - extra // 2
            arrow_width = self.category_search_dropdown_arrow_width

            field.configure(width=field_width)
            self.category_search_field_label.place_configure(
                width=max(1, field_width - arrow_width)
            )
            self.category_search_field_arrow.place_configure(
                x=max(0, field_width - arrow_width)
            )

            value_host.configure(width=value_width)
            self.after_idle(self._layout_category_search_text_value)
            self.category_search_icon_canvas.place_configure(
                width=max(1, value_width - arrow_width)
            )
            self.category_search_icon_arrow.place_configure(
                x=max(0, value_width - arrow_width)
            )

            # _integrated_shell 会锁定外壳宽度，所以这里同步扩大外壳本身。
            shell.configure(width=max(1, target_right - shell_left))
            self.after_idle(self._paint_category_search_icon_value)
        except tk.TclError:
            pass

    @staticmethod
    def _category_search_is_descendant(widget, ancestor):
        """判断 widget 是否位于 ancestor 内；用于区分菜单内点击和外部点击。"""
        if widget is None or ancestor is None:
            return False
        current = widget
        while current is not None:
            if current is ancestor:
                return True
            try:
                parent_name = current.winfo_parent()
                if not parent_name:
                    break
                current = current.nametowidget(parent_name)
            except (tk.TclError, KeyError):
                break
        return False

    def _on_category_search_global_click(self, event):
        """点击两个分类筛选下拉框之外的位置时，收起当前展开菜单。"""
        field_popup = getattr(self, "category_search_field_popup", None)
        icon_popup = getattr(self, "category_search_icon_popup", None)
        if field_popup is None and icon_popup is None:
            return None

        widget = getattr(event, "widget", None)

        # 点击当前菜单本体时交给菜单项自己的绑定处理。
        if field_popup is not None and self._category_search_is_descendant(widget, field_popup):
            return None
        if icon_popup is not None and self._category_search_is_descendant(widget, icon_popup):
            return None

        # 点击对应触发区时也先不由全局绑定关闭；触发区自己的逻辑会负责
        # “已展开则关闭 / 未展开则打开”，这样再次点击值区或箭头即可切换。
        field_host = getattr(self, "category_search_field", None)
        value_host = getattr(self, "category_search_value_host", None)
        if field_popup is not None and self._category_search_is_descendant(widget, field_host):
            return None
        if icon_popup is not None and self._category_search_is_descendant(widget, value_host):
            return None

        self._close_category_search_field_popup()
        self._close_category_search_icon_popup()
        return None

    def _close_category_search_field_popup(self, _event=None):
        popup = getattr(self, "category_search_field_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        self.category_search_field_popup = None

    def _open_category_search_field_popup(self):
        # 再次点击字段值区或箭头时直接收起，不重新打开。
        existing = getattr(self, "category_search_field_popup", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    self._close_category_search_field_popup()
                    return
            except tk.TclError:
                pass
            self.category_search_field_popup = None

        # 字段菜单和值菜单互斥；同一时刻只允许一个展开。
        self._close_category_search_icon_popup()
        host = self.category_search_field
        choices = ("显示", "分类名", "事件数", "side")
        current = self.category_search_field_var.get()

        # 不再使用 overrideredirect Toplevel。Windows 在某些 DPI / 多窗口状态下
        # 会把那种临时窗重定位到整个屏幕左上角。改为主窗口内的覆盖层，坐标始终
        # 相对于当前应用窗口，位置因此稳定地跟在字段框正下方。
        popup = tk.Frame(self, bg="#8fa3b8", bd=0, highlightthickness=0)
        self.category_search_field_popup = popup
        inner = tk.Frame(popup, bg="white")
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        rows = []
        for value in choices:
            bg = "#dbeafe" if value == current else "white"
            row = tk.Label(
                inner, text=value, anchor="center",
                font=("Microsoft YaHei", 8),
                bg=bg, fg="#253044", padx=2, pady=2,
            )
            row.pack(fill="x")
            rows.append((row, value))

        def paint(active_value=None):
            for row, value in rows:
                row.configure(
                    bg="#dbeafe" if value == (active_value or current) else "white"
                )

        for row, value in rows:
            # 与其它下拉框保持一致：悬浮到哪里，高亮就停在哪里；
            # 鼠标离开菜单时不自动跳回当前已选项。
            row.bind("<Enter>", lambda _e, v=value: paint(v))
            row.bind(
                "<Button-1>",
                lambda _e, v=value: (
                    self._select_category_search_field(v),
                    self._close_category_search_field_popup(),
                ),
            )

        self.update_idletasks()
        host.update_idletasks()
        popup.update_idletasks()
        x = host.winfo_rootx() - self.winfo_rootx()
        y = host.winfo_rooty() - self.winfo_rooty() + host.winfo_height()
        width = max(host.winfo_width(), popup.winfo_reqwidth())
        height = popup.winfo_reqheight()
        popup.place(x=x, y=y, width=width, height=height)
        popup.lift()

    def _select_category_search_field(self, value):
        self.category_search_field_var.set(value)
        self._rebuild_category_search_value_control()
        self.after_idle(self.focus_set)

    def _show_category_search_placeholder(self):
        entry = self.category_search_value_entry_box.entry
        if self.category_search_field_var.get() != "事件数":
            return
        if self.category_search_value_var.get():
            return
        self.category_search_placeholder_active = True
        self.category_search_value_var.set("0, 1, >0...")
        entry.configure(fg="#94a3b8")

    def _clear_category_search_placeholder(self):
        if not getattr(self, "category_search_placeholder_active", False):
            return
        self.category_search_placeholder_active = False
        self.category_search_value_var.set("")
        self.category_search_value_entry_box.entry.configure(fg="#263247")

    def _on_category_search_value_focus_in(self, _event=None):
        self._clear_category_search_placeholder()

    def _on_category_search_value_click(self, event):
        self._clear_category_search_placeholder()
        try:
            self.after_idle(event.widget.focus_set)
        except tk.TclError:
            pass

    def _on_category_search_value_focus_out(self, _event=None):
        self._show_category_search_placeholder()

    def _paint_category_search_icon_value(self):
        canvas = self.category_search_icon_canvas
        field = self.category_search_field_var.get()
        value = self.category_search_value_var.get()
        if field == "显示":
            self._draw_search_eye(canvas, hidden=(value == "隐藏"))
        elif field == "side":
            state = {"上侧": "top", "下侧": "bottom", "无限制": "unrestricted"}.get(value, "top")
            self._draw_search_side(canvas, state)

    def _close_category_search_icon_popup(self, _event=None):
        popup = getattr(self, "category_search_icon_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        self.category_search_icon_popup = None

    def _select_category_search_icon_value(self, semantic_value):
        self.category_search_value_var.set(semantic_value)
        self._paint_category_search_icon_value()
        self._close_category_search_icon_popup()

    def _open_category_search_icon_popup(self):
        # 再次点击图标值区或箭头时直接收起，不重新打开。
        existing = getattr(self, "category_search_icon_popup", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    self._close_category_search_icon_popup()
                    return
            except tk.TclError:
                pass
            self.category_search_icon_popup = None

        # 字段菜单和值菜单互斥；同一时刻只允许一个展开。
        self._close_category_search_field_popup()
        choices = list(getattr(self, "category_search_icon_choices", []))
        if not choices:
            return

        shell = self.category_search_value_host
        shell.update_idletasks()
        popup = tk.Frame(self, bg="#8fa3b8", bd=0, highlightthickness=0)
        self.category_search_icon_popup = popup

        width = max(1, shell.winfo_width())
        row_h = 23
        body = tk.Frame(popup, bg="white")
        body.pack(fill="both", expand=True, padx=1, pady=1)
        current = self.category_search_value_var.get()
        rows = []

        def set_row_bg(row, canvas, bg):
            row.configure(bg=bg)
            canvas.configure(bg=bg)
            field = self.category_search_field_var.get()
            value = row._semantic_value
            if field == "显示":
                self._draw_search_eye(canvas, hidden=(value == "隐藏"), bg=bg)
            else:
                state = {"上侧": "top", "下侧": "bottom", "无限制": "unrestricted"}[value]
                self._draw_search_side(canvas, state, bg=bg)

        def highlight(target):
            for row, canvas in rows:
                set_row_bg(row, canvas, "#dbeafe" if row is target else "white")

        for value in choices:
            row = tk.Frame(body, bg="white", height=row_h, cursor="arrow")
            row.pack(fill="x")
            row.pack_propagate(False)
            row._semantic_value = value
            canvas = self._category_search_icon_canvas(row, width=max(1, width - 2), height=row_h)
            canvas.pack(fill="both", expand=True)
            rows.append((row, canvas))
            for widget in (row, canvas):
                widget.bind("<Enter>", lambda _e, r=row: highlight(r))
                widget.bind("<Button-1>", lambda _e, v=value: self._select_category_search_icon_value(v))
            canvas.bind(
                "<Configure>",
                lambda _e, r=row, c=canvas: set_row_bg(r, c, r.cget("bg")),
                add="+",
            )

        self.update_idletasks()
        popup.update_idletasks()
        for row, canvas in rows:
            set_row_bg(row, canvas, "#dbeafe" if row._semantic_value == current else "white")

        x = shell.winfo_rootx() - self.winfo_rootx()
        y = shell.winfo_rooty() - self.winfo_rooty() + shell.winfo_height()
        height = row_h * len(choices) + 2
        popup.place(x=x, y=y, width=width, height=height)
        popup.lift()

    def _configure_category_search_icon_values(self, field):
        if field == "显示":
            choices = ["显示", "隐藏"]
        else:
            choices = ["上侧", "下侧", "无限制"]
        self.category_search_icon_choices = choices
        self.category_search_value_var.set(choices[0])

    def _rebuild_category_search_value_control(self):
        host = getattr(self, "category_search_value_host", None)
        if host is None:
            return

        field = self.category_search_field_var.get()
        self._close_category_search_icon_popup()
        self._clear_category_search_placeholder()
        self.category_search_value_var.set("")

        icon_shell = self.category_search_icon_shell
        entry_box = self.category_search_value_entry_box
        icon_shell.pack_forget()
        entry_box.pack_forget()

        if field in {"显示", "side"}:
            self._configure_category_search_icon_values(field)
            icon_shell.pack(fill="both", expand=True)
            self.category_search_value_control = icon_shell
            self.after_idle(self._paint_category_search_icon_value)
            return

        entry_box.pack(fill="both", expand=True)
        self.category_search_value_control = entry_box
        # 字段切换本身不抢输入焦点；事件数 placeholder 因而会立即可见。
        if field == "事件数":
            self._show_category_search_placeholder()

    def _category_search_counts(self):
        counts = {category: 0 for category in self.categories}
        for row in getattr(self, "rows", []):
            category = row.get("category", "未分类")
            counts[category] = counts.get(category, 0) + 1
        return counts

    def execute_category_search(self):
        field = self.category_search_field_var.get()
        raw_value = (
            ""
            if getattr(self, "category_search_placeholder_active", False)
            else self.category_search_value_var.get()
        )
        value = raw_value.strip()

        if field == "分类名":
            if not value:
                messagebox.showinfo("分类查找", "请输入分类名关键词。")
                return
            needle = value.casefold()
            matches = [
                category for category in self.categories
                if needle in category.casefold()
            ]

        elif field == "事件数":
            counts = self._category_search_counts()
            if value == ">0":
                matches = [
                    category for category in self.categories
                    if counts.get(category, 0) > 0
                ]
            else:
                try:
                    number = int(value)
                except (TypeError, ValueError):
                    messagebox.showwarning(
                        "分类查找",
                        "事件数请输入 0 或正整数；筛选非空分类可输入 >0。",
                    )
                    return
                if number < 0 or str(number) != value:
                    messagebox.showwarning(
                        "分类查找",
                        "事件数请输入 0 或正整数；筛选非空分类可输入 >0。",
                    )
                    return
                matches = [
                    category for category in self.categories
                    if counts.get(category, 0) == number
                ]

        elif field == "显示":
            want_hidden = value == "隐藏"
            matches = [
                category for category in self.categories
                if (category in self.hidden_categories) == want_hidden
            ]

        elif field == "side":
            wanted = {
                "上侧": "top",
                "下侧": "bottom",
                "无限制": "unrestricted",
            }.get(value)
            if wanted is None:
                return
            matches = [
                category for category in self.categories
                if self.category_side_states.get(
                    category,
                    "unrestricted" if category == "未分类" else "top",
                ) == wanted
            ]
        else:
            matches = []

        # 新查找只保留本次结果的自动选择；“未分类”可匹配、可定位，但不可勾选。
        self._clear_category_search_focus()
        self._set_all_categories_selected(False)
        for category in matches:
            if category == "未分类":
                continue
            self.selected_categories.add(category)
            var = getattr(self, "legend_select_vars", {}).get(category)
            if var is not None:
                var.set(True)
        self._refresh_category_select_all_state()
        self._refresh_all_category_row_visuals()

        self.category_search_matches = matches
        self.category_search_index = 0 if matches else -1
        self._update_category_search_counter()

        if matches:
            self._locate_category_search_match(matches[0])
        else:
            messagebox.showinfo("分类查找", "没有找到符合条件的分类。")

    def clear_category_search(self):
        """清空分类筛选，并取消由本次筛选产生的选择与定位高亮。"""
        self.category_search_value_var.set("")
        self.category_search_matches = []
        self.category_search_index = -1

        # 分类查找会自动勾选匹配分类，因此清除查找时也要像 CSV / 时间轴
        # 的清除按钮一样撤掉本次结果状态，而不只清空输入文字。
        self._clear_category_search_focus()
        self._set_all_categories_selected(False)
        self._refresh_all_category_row_visuals()
        self._update_category_search_counter()

        # 文本筛选字段的 × 与 CSV 查找 × 保持一致：清除后焦点回到输入框。
        entry_box = getattr(self, "category_search_value_entry_box", None)
        entry = getattr(entry_box, "entry", None) if entry_box is not None else None
        if entry is not None:
            try:
                entry.focus_set()
            except tk.TclError:
                pass

    def _update_category_search_counter(self):
        matches = getattr(self, "category_search_matches", [])
        index = getattr(self, "category_search_index", -1)
        if not matches or index < 0:
            text = "0/0"
        else:
            text = f"{index + 1}/{len(matches)}"
        var = getattr(self, "category_search_counter_var", None)
        if var is not None:
            var.set(text)

    def _clear_category_search_focus(self):
        previous = getattr(self, "category_search_focus_category", None)
        self.category_search_focus_category = None
        self.category_search_focus_field = None
        if previous:
            self._refresh_category_row_visual(previous, reapply_focus=False)

    def _apply_category_search_field_highlight(self, category):
        field = getattr(self, "category_search_focus_field", None) or getattr(
            self, "category_search_field_var", tk.StringVar(value="分类名")
        ).get()
        field_key = {
            "显示": "display",
            "分类名": "name",
            "事件数": "count",
            "side": "side",
        }.get(field)
        if field_key is None:
            return
        cell = getattr(self, "legend_field_widgets", {}).get(category, {}).get(field_key)
        if cell is None:
            return
        self._set_category_row_background(cell, "#93c5fd")
        if field_key == "display":
            canvas = getattr(self, "legend_eye_canvases", {}).get(category)
            if canvas is not None:
                try:
                    self._draw_eye_icon(canvas, category in self.hidden_categories)
                except tk.TclError:
                    pass

    def _locate_category_search_match(self, category):
        row = getattr(self, "legend_row_widgets", {}).get(category)
        if row is None or not row.winfo_exists():
            return

        self.legend_frame.update_idletasks()
        row_top = row.winfo_y()
        row_bottom = row_top + row.winfo_height()
        viewport_top = self.legend_canvas.canvasy(0)
        viewport_height = max(1, self.legend_canvas.winfo_height())
        viewport_bottom = viewport_top + viewport_height

        if row_top < viewport_top:
            self.set_legend_top(row_top)
        elif row_bottom > viewport_bottom:
            self.set_legend_top(row_bottom - viewport_height)

        previous = getattr(self, "category_search_focus_category", None)
        if previous and previous != category:
            self.category_search_focus_category = None
            self.category_search_focus_field = None
            self._refresh_category_row_visual(previous, reapply_focus=False)

        self.category_search_focus_category = category
        self.category_search_focus_field = self.category_search_field_var.get()
        # 搜索结果本身已经通过勾选呈现浅蓝行高亮；“未分类”不可勾选，
        # 因而在被定位时临时给予同样的浅蓝底。
        if category == "未分类" or category not in self.selected_categories:
            self._set_category_row_background(row, "#dbeafe")
        else:
            self._refresh_category_row_visual(category, reapply_focus=False)
        self._apply_category_search_field_highlight(category)

    def _set_category_row_background(self, widget, color):
        try:
            widget.configure(bg=color)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            try:
                if child.winfo_class() in {"Frame", "Label", "Checkbutton", "Canvas"}:
                    child.configure(bg=color)
                    if child.winfo_class() == "Checkbutton":
                        child.configure(activebackground=color)
            except tk.TclError:
                pass
            self._set_category_row_background(child, color)

    def show_next_category_search_match(self):
        matches = getattr(self, "category_search_matches", [])
        if not matches:
            return
        self.category_search_index = (
            getattr(self, "category_search_index", -1) + 1
        ) % len(matches)
        self._update_category_search_counter()
        self._locate_category_search_match(
            matches[self.category_search_index]
        )

    def show_previous_category_search_match(self):
        matches = getattr(self, "category_search_matches", [])
        if not matches:
            return
        self.category_search_index = (
            getattr(self, "category_search_index", 0) - 1
        ) % len(matches)
        self._update_category_search_counter()
        self._locate_category_search_match(
            matches[self.category_search_index]
        )
