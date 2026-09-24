"""UI 基础交互、样式与滚动条工厂。"""

import tkinter as tk
from tkinter import ttk

from .ui_scrollbar import UnifiedScrollbar


class UICoreMixin:
    def _normalize_csv_cursor(self, event):
        """Keep CSV heading separators visually non-interactive.

        ttk.Treeview's class-level <Motion> binding changes the cursor to the
        horizontal resize cursor whenever the pointer is over a heading
        separator.  Setting cursor="arrow" alone is not enough because the
        class binding runs afterwards and changes it back.  Returning
        "break" on separators stops that class binding for this motion event.
        """
        try:
            widget = event.widget
            widget.configure(cursor="arrow")
            if widget.identify_region(event.x, event.y) == "separator":
                return "break"
        except Exception:
            pass
        return None

    def _block_csv_separator_drag(self, event):
        widget = event.widget
        try:
            if widget.identify_region(event.x, event.y) == "separator":
                return "break"
        except Exception:
            pass

    def _sync_csv_active_row_from_editor(self, event=None):
        if not hasattr(self, "csv_editor") or not hasattr(self, "csv_row_numbers"):
            return
        item = self.csv_editor.identify_row(getattr(event, "y", 0)) if event else ""
        if not item:
            selection = self.csv_editor.selection()
            item = selection[0] if selection else ""
        if not item:
            return
        children = self.csv_editor.get_children("")
        try:
            index = children.index(item)
        except ValueError:
            return
        self.csv_editor.selection_set(item)
        self.csv_editor.focus(item)
        row_items = self.csv_row_numbers.get_children("")
        if index < len(row_items):
            self.csv_row_numbers.selection_set(row_items[index])
            self.csv_row_numbers.focus(row_items[index])

    def _sync_csv_active_row_from_row_number(self, event=None):
        if not hasattr(self, "csv_editor") or not hasattr(self, "csv_row_numbers"):
            return
        item = self.csv_row_numbers.identify_row(getattr(event, "y", 0)) if event else ""
        if not item:
            selection = self.csv_row_numbers.selection()
            item = selection[0] if selection else ""
        if not item:
            return
        row_items = self.csv_row_numbers.get_children("")
        try:
            index = row_items.index(item)
        except ValueError:
            return
        self.csv_row_numbers.selection_set(item)
        self.csv_row_numbers.focus(item)
        children = self.csv_editor.get_children("")
        if index < len(children):
            self.csv_editor.selection_set(children[index])
            self.csv_editor.focus(children[index])

    def _configure_toolbar_styles(self):
        """统一所有区标题行控件的视觉模板。"""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        font = ("Microsoft YaHei", 8)
        style.configure(
            "Toolbar.TButton",
            font=font,
            padding=(1, 1),
            background="#ffffff",
            foreground="#253044",
            bordercolor="#8fa3b8",
            lightcolor="#ffffff",
            darkcolor="#8fa3b8",
            relief="raised",
        )
        style.map(
            "Toolbar.TButton",
            background=[
                ("pressed", "#e5eaf0"),
                ("active", "#edf2f7"),
                ("disabled", "#f4f5f7"),
            ],
            foreground=[("disabled", "#9aa4b2")],
        )
        style.configure(
            "Toolbar.Primary.TButton",
            font=font,
            padding=(1, 1),
            background="#2968e8",
            foreground="#ffffff",
            bordercolor="#1f57c5",
            lightcolor="#4b82ef",
            darkcolor="#1f57c5",
            relief="raised",
        )
        style.map(
            "Toolbar.Primary.TButton",
            background=[("pressed", "#194cab"), ("active", "#1f57c5")],
            foreground=[("disabled", "#d8e3ff")],
        )
        style.configure(
            "Toolbar.Nav.TButton",
            font=("Microsoft YaHei", 9),
            padding=(1, 1),
            background="#ffffff",
            foreground="#253044",
            bordercolor="#8fa3b8",
            lightcolor="#ffffff",
            darkcolor="#8fa3b8",
            relief="raised",
        )
        style.map(
            "Toolbar.Nav.TButton",
            background=[("pressed", "#e5eaf0"), ("active", "#edf2f7")],
        )
        style.configure(
            "Toolbar.TCombobox",
            font=font,
            padding=(3, 1),
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground="#253044",
            arrowcolor="#263247",
            bordercolor="#8fa3b8",
            lightcolor="#ffffff",
            darkcolor="#8fa3b8",
        )
        style.map(
            "Toolbar.TCombobox",
            fieldbackground=[("readonly", "#ffffff"), ("focus", "#ffffff")],
            background=[("readonly", "#ffffff"), ("active", "#edf2f7")],
            foreground=[("readonly", "#253044")],
            selectbackground=[("readonly", "#dbeafe")],
            selectforeground=[("readonly", "#253044")],
        )
        style.configure(
            "Toolbar.TEntry",
            font=("Consolas", 9),
            padding=(3, 1),
            fieldbackground="#ffffff",
            foreground="#253044",
            bordercolor="#8fa3b8",
            lightcolor="#ffffff",
            darkcolor="#8fa3b8",
        )

        self.option_add("*TCombobox*Listbox.selectBackground", "#dbeafe")
        self.option_add("*TCombobox*Listbox.selectForeground", "#263247")

        # 全页滚动条使用同一个低对比度组件：颜色、宽度和三角显隐逻辑完全一致。
        # 静止时不显示两端三角；滚轮、拖动或点击滚动条时短暂显示，随后统一隐藏。
        self._scrollbar_trough_color = UnifiedScrollbar.TRACK_COLOR

    def _make_scrollbar(self, parent, orient, command, **kwargs):
        """建立全页统一滚动条。"""
        return UnifiedScrollbar(parent, orient=orient, command=command, **kwargs)

    def _show_scrollbar_arrows(self, scrollbar):
        """兼容旧调用，并统一触发滚动条三角的短暂显示。"""
        if hasattr(scrollbar, "show_arrows_temporarily"):
            scrollbar.show_arrows_temporarily()
        return None
