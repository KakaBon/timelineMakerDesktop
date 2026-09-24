"""主界面焦点、信息记录与 Tooltip 交互。"""

import tkinter as tk
from tkinter import ttk


class UIInteractionMixin:
    def _on_info_log_pointer_press(self, _event=None):
        """信息记录区不参与文本交互，但点击它会关闭当前浮层。"""
        for method_name in (
            "_close_category_search_field_popup",
            "_close_category_search_icon_popup",
            "_close_migration_popup",
        ):
            method = getattr(self, method_name, None)
            if callable(method):
                try:
                    method()
                except tk.TclError:
                    pass
        try:
            self.focus_set()
        except tk.TclError:
            pass
        return "break"

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

    def _release_non_table_text_focus(self, event):
        """点击普通文本框外部时释放其焦点；CSV 单元格编辑保持原逻辑。"""
        try:
            focused = self.focus_get()
        except (tk.TclError, KeyError):
            # ttk.Combobox 的下拉列表使用独立 popdown 窗口；焦点落在
            # 这个临时窗口时 focus_get() 可能无法映射回 Tkinter widget。
            # 这不属于需要释放的普通文本框焦点，直接忽略即可。
            return None

        if focused is None or focused is event.widget:
            return None

        try:
            if focused.winfo_toplevel() is not self:
                return None
        except tk.TclError:
            return None

        csv_editor = getattr(self, "csv_cell_editor", None)
        if focused is csv_editor:
            return None

        if isinstance(focused, (tk.Entry, ttk.Entry)):
            try:
                self.focus_set()
            except tk.TclError:
                pass
        return None

    def _bind_info_tooltip(self, widget, text, compact=False):
        """绑定即时 Tooltip；标题行图标按钮可使用更紧凑的 alt 提示。"""
        widget.bind(
            "<Enter>",
            lambda event, target=widget, content=text, small=compact: self.show_info_tooltip(
                event, target, content, compact=small
            ),
            add="+",
        )
        widget.bind("<Leave>", self.schedule_hide_info_tooltip, add="+")
        # 图标 alt 只是 hover 辅助信息。用户一旦按下图标，就立刻收起，
        # 不能让随后打开的对话框/长操作把提示框“冻结”在页面上。
        if compact:
            widget.bind(
                "<ButtonPress-1>",
                lambda _event: self.hide_info_tooltip(),
                add="+",
            )

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

    def show_info_tooltip(self, _event, widget, text, compact=False):
        """鼠标进入目标时立即显示；图标按钮提示使用紧凑尺寸。"""
        self._cancel_info_tooltip_hide_job()
        self._ensure_info_tooltip_window()

        self._info_tooltip_widget = widget
        self._info_tooltip_text = text
        if compact:
            self._info_tooltip_label.configure(
                text=text, padx=5, pady=2, font=("Microsoft YaHei", 7),
                wraplength=0,
            )
            offset = 5
        else:
            self._info_tooltip_label.configure(
                text=text, padx=12, pady=10, font=("Microsoft YaHei", 9),
                wraplength=520,
            )
            offset = 8

        self.help_tooltip.update_idletasks()

        # Tooltip 放在控件边界之外，避免遮挡目标本身。
        x = widget.winfo_rootx() + widget.winfo_width() + offset
        y = widget.winfo_rooty() + widget.winfo_height() + offset
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

    def show_help_tooltip(self, event=None):
        self.show_info_tooltip(
            event,
            self.help_hit_area,
            ("工作方式\n"
             "CSV 编辑器中的修改先保留为草稿，点击“应用修改”后才同步到分类区和时间轴。\n\n"
             "CSV 草稿使用 Ctrl+Z / Ctrl+Y 撤销、重做；已经应用的正式操作使用页面顶部的撤销 / 重做。\n\n"
             "查找、筛选、定位、滚动、缩放和显示 / 隐藏等浏览操作不进入全局撤销历史。\n\n"
             "“导出 CSV”用于把当前 CSV 内容保存为文件。"),
        )

    def hide_help_tooltip(self, event=None):
        self.schedule_hide_info_tooltip(event)
