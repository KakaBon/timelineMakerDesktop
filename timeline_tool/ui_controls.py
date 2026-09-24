"""通用一体式控件、图标与标题控件。"""

import tkinter as tk
from tkinter import ttk


class UIControlsMixin:
    def _entry_box(self, parent, variable, width=12, clear_command=None):
        """统一给值框：Entry/Combobox 共用白底、蓝灰边框与相同高度语言。"""
        box = tk.Frame(
            parent,
            bg="#8fa3b8",
            bd=0,
            highlightthickness=0,
        )
        inner = tk.Frame(box, bg="white")
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        entry = tk.Entry(
            inner,
            textvariable=variable,
            width=width,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            bg="white",
            fg="#253044",
            insertbackground="#253044",
            highlightthickness=0,
        )
        entry.pack(side="left", fill="y", padx=(3, 0), pady=1)
        box.entry = entry
        box.clear_button = None
        if clear_command is not None:
            box.clear_button = tk.Button(
                inner,
                text="×",
                command=clear_command,
                font=("Microsoft YaHei", 7),
                relief="flat",
                padx=2,
                pady=0,
                bg="white",
                fg="#64748b",
                activebackground="#edf2f7",
                activeforeground="#253044",
                bd=0,
                highlightthickness=0,
                takefocus=False,
            )
            box.clear_button.pack(side="right", fill="y", padx=1)
        return box

    def _integrated_shell(self, parent):
        """一体式控件外壳：所有标题行组合控件统一为 23 px 总高度。"""
        shell = tk.Frame(
            parent,
            bg="#8fa3b8",
            bd=0,
            highlightthickness=0,
        )

        # 先让内部各段完成宽度计算，再只锁定外壳高度。
        # 这样不会牺牲各控件原有的横向宽度，又能保证所有一体式控件
        # 的纵向尺寸完全一致，而不是仅仅顶边/底边对齐。
        def lock_geometry():
            try:
                if not shell.winfo_exists():
                    return
                shell.update_idletasks()
                width = max(1, shell.winfo_reqwidth())
                shell.configure(width=width, height=23)
                shell.pack_propagate(False)
            except tk.TclError:
                pass

        self.after_idle(lock_geometry)
        return shell

    def _integrated_cell(self, parent, bg="white"):
        cell = tk.Frame(parent, bg=bg, bd=0, highlightthickness=0)
        return cell

    def _integrated_separator(self, parent):
        # 21 px inner height + the caller's 1 px top/bottom packing margin makes
        # every integrated shell request the same 23 px total height.
        return tk.Frame(
            parent, bg="#8fa3b8", width=1, height=21,
            bd=0, highlightthickness=0,
        )

    def _integrated_entry(self, parent, variable, clear_command=None, width=12):
        """一体式控件中的统一值区；三个查找区使用完全相同宽度。"""
        cell = self._integrated_cell(parent)
        entry = tk.Entry(
            cell,
            textvariable=variable,
            width=width,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            bg="white",
            fg="#253044",
            insertbackground="#253044",
            highlightthickness=0,
        )
        entry.pack(side="left", fill="both", expand=True, padx=(4, 1), pady=0)
        cell.entry = entry
        if clear_command is not None:
            clear = tk.Button(
                cell, text="×", command=clear_command,
                font=("Microsoft YaHei", 7),
                relief="flat", bd=0, highlightthickness=0,
                padx=3, pady=0, bg="white", fg="#64748b",
                activebackground="#edf2f7", activeforeground="#253044",
                takefocus=False,
            )
            clear.pack(side="right", fill="y")
            cell.clear_button = clear
        return cell

    def _integrated_action(self, parent, text, command, width=None, primary=False):
        """一体式控件内部动作区：无独立外框，靠整体外框和分隔线组织。"""
        bg = "#2563eb" if primary else "white"
        fg = "white" if primary else "#253044"
        active_bg = "#1f57c5" if primary else "#edf2f7"
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei", 8),
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=4 if width is None else 2,
            pady=1,
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            takefocus=False,
            cursor="hand2",
        )
        if width is not None:
            button.configure(width=width)
        return button

    def _draw_toolbar_icon(self, canvas, icon, bg="white"):
        """在标题行小型 Canvas 内绘制统一的矢量图标。"""
        canvas.delete("all")
        canvas.configure(bg=bg)
        try:
            width = max(1, int(canvas.winfo_width()))
            height = max(1, int(canvas.winfo_height()))
        except tk.TclError:
            return

        cx = width / 2
        cy = height / 2
        fg = "white" if bg in {"#2563eb", "#1f57c5"} else "#253044"

        if icon in {"search", "zoom_in", "zoom_out"}:
            radius = 5.2
            lens_cx = cx - 1.5
            lens_cy = cy - 1.5
            canvas.create_oval(
                lens_cx - radius, lens_cy - radius,
                lens_cx + radius, lens_cy + radius,
                outline=fg, width=1.6,
            )
            canvas.create_line(
                lens_cx + 4.0, lens_cy + 4.0,
                lens_cx + 8.1, lens_cy + 8.1,
                fill=fg, width=1.6,
            )
            if icon in {"zoom_in", "zoom_out"}:
                canvas.create_line(
                    lens_cx - 2.5, lens_cy,
                    lens_cx + 2.5, lens_cy,
                    fill=fg, width=1.3,
                )
                if icon == "zoom_in":
                    canvas.create_line(
                        lens_cx, lens_cy - 2.5,
                        lens_cx, lens_cy + 2.5,
                        fill=fg, width=1.3,
                    )
            return

        if icon == "add":
            fg = "#159447"
            canvas.create_line(cx - 5, cy, cx + 5, cy, fill=fg, width=3.0)
            canvas.create_line(cx, cy - 5, cx, cy + 5, fill=fg, width=3.0)
            return

        if icon == "delete":
            fg = "#d92d20"
            canvas.create_rectangle(cx - 4.5, cy - 3, cx + 4.5, cy + 6, fill=fg, outline=fg)
            canvas.create_rectangle(cx - 6, cy - 6, cx + 6, cy - 4.3, fill=fg, outline=fg)
            canvas.create_rectangle(cx - 2.2, cy - 8, cx + 2.2, cy - 6, fill=fg, outline=fg)
            canvas.create_line(cx - 1.7, cy - 1, cx - 1.7, cy + 4, fill="white", width=1)
            canvas.create_line(cx + 1.7, cy - 1, cx + 1.7, cy + 4, fill="white", width=1)
            return

        if icon in {"replace", "replace_all"}:
            def draw_pair(offset_y=0, scale=1.0):
                x1, x2 = cx - 6.5 * scale, cx + 6.5 * scale
                y1 = cy - 3.0 * scale + offset_y
                y2 = cy + 3.0 * scale + offset_y
                canvas.create_line(x1, y1, x2 - 2, y1, fill=fg, width=1.4)
                canvas.create_line(x2 - 4, y1 - 2.3, x2, y1, x2 - 4, y1 + 2.3, fill=fg, width=1.4)
                canvas.create_line(x2, y2, x1 + 2, y2, fill=fg, width=1.4)
                canvas.create_line(x1 + 4, y2 - 2.3, x1, y2, x1 + 4, y2 + 2.3, fill=fg, width=1.4)

            if icon == "replace":
                draw_pair()
            else:
                draw_pair(offset_y=-2.4, scale=0.82)
                draw_pair(offset_y=3.2, scale=0.82)
            return

        if icon == "date_range":
            left = cx - 8
            right = cx + 8
            canvas.create_line(left, cy, right - 2, cy, fill=fg, width=1.5)
            canvas.create_line(right - 5, cy - 3, right, cy, right - 5, cy + 3, fill=fg, width=1.5)
            canvas.create_line(left, cy - 4, left, cy + 4, fill=fg, width=1.2)
            return

        if icon == "import":
            canvas.create_line(cx - 7, cy + 5, cx - 7, cy + 7, cx + 7, cy + 7, cx + 7, cy + 5, fill=fg, width=1.3)
            canvas.create_line(cx, cy - 7, cx, cy + 2.5, fill=fg, width=1.5)
            canvas.create_line(cx - 3.5, cy - 1, cx, cy + 2.5, cx + 3.5, cy - 1, fill=fg, width=1.5)
            return

        if icon == "apply":
            canvas.create_line(cx - 6, cy, cx - 1.5, cy + 4.5, cx + 7, cy - 5.5, fill=fg, width=2.0)
            return

        if icon == "load_sample":
            # 小文档 + 内容行：表示载入内置示例。
            left, top = cx - 6, cy - 7
            right, bottom = cx + 6, cy + 7
            canvas.create_rectangle(left, top, right, bottom, outline=fg, width=1.2)
            canvas.create_line(left + 2.5, top + 4, right - 2.5, top + 4, fill=fg, width=1.1)
            canvas.create_line(left + 2.5, top + 7, right - 4, top + 7, fill=fg, width=1.1)
            canvas.create_line(left + 2.5, top + 10, right - 3, top + 10, fill=fg, width=1.1)
            return

        if icon == "export":
            # 托盘 + 向外箭头。
            canvas.create_line(cx - 7, cy + 4, cx - 7, cy + 7, cx + 7, cy + 7, cx + 7, cy + 4,
                               fill=fg, width=1.3)
            canvas.create_line(cx, cy + 3, cx, cy - 7, fill=fg, width=1.5)
            canvas.create_line(cx - 3.5, cy - 3.5, cx, cy - 7, cx + 3.5, cy - 3.5,
                               fill=fg, width=1.5)
            return

        if icon == "add_event":
            # 横向事件行 + 绿色加号。
            row_left, row_right = cx - 8, cx + 3
            row_top, row_bottom = cy - 4, cy + 4
            canvas.create_rectangle(
                row_left, row_top, row_right, row_bottom,
                outline=fg, width=1.2,
            )
            canvas.create_line(
                row_left + 2, cy - 1.5, row_right - 2, cy - 1.5,
                fill=fg, width=1.0,
            )
            canvas.create_line(
                row_left + 2, cy + 1.5, row_right - 4, cy + 1.5,
                fill=fg, width=1.0,
            )
            plus_x = cx + 6.5
            plus_fg = "#159447"
            canvas.create_line(plus_x - 3.5, cy, plus_x + 3.5, cy, fill=plus_fg, width=1.8)
            canvas.create_line(plus_x, cy - 3.5, plus_x, cy + 3.5, fill=plus_fg, width=1.8)
            return

        if icon == "add_field":
            # 纵向字段列 + 绿色加号。
            col_left, col_right = cx - 5, cx + 1
            col_top, col_bottom = cy - 7, cy + 7
            canvas.create_rectangle(
                col_left, col_top, col_right, col_bottom,
                outline=fg, width=1.2,
            )
            canvas.create_line(col_left, cy - 2.2, col_right, cy - 2.2, fill=fg, width=1.0)
            canvas.create_line(col_left, cy + 2.2, col_right, cy + 2.2, fill=fg, width=1.0)
            plus_x = cx + 6.5
            plus_fg = "#159447"
            canvas.create_line(plus_x - 3.5, cy, plus_x + 3.5, cy, fill=plus_fg, width=1.8)
            canvas.create_line(plus_x, cy - 3.5, plus_x, cy + 3.5, fill=plus_fg, width=1.8)
            return

        if icon == "sort_date":
            # 简化日历 + 向下排序箭头。
            cal_left, cal_top = cx - 8, cy - 6
            cal_right, cal_bottom = cx + 2, cy + 6
            canvas.create_rectangle(cal_left, cal_top, cal_right, cal_bottom, outline=fg, width=1.2)
            canvas.create_line(cal_left, cal_top + 3, cal_right, cal_top + 3, fill=fg, width=1.0)
            canvas.create_line(cal_left + 2.5, cal_top - 1.5, cal_left + 2.5, cal_top + 1.5, fill=fg, width=1.2)
            canvas.create_line(cal_right - 2.5, cal_top - 1.5, cal_right - 2.5, cal_top + 1.5, fill=fg, width=1.2)
            arrow_x = cx + 6
            canvas.create_line(arrow_x, cy - 5, arrow_x, cy + 5, fill=fg, width=1.4)
            canvas.create_line(arrow_x - 3, cy + 2, arrow_x, cy + 5, arrow_x + 3, cy + 2,
                               fill=fg, width=1.4)
            return

    def _integrated_icon_action(
        self, parent, icon, command, tooltip_text="", width=25, primary=False
    ):
        """一体式控件中的可点击矢量图标区；primary 使用蓝底主动作样式。"""
        base_bg = "#2563eb" if primary else "white"
        active_bg = "#1f57c5" if primary else "#edf2f7"
        canvas = tk.Canvas(
            parent, width=width, height=21, bg=base_bg,
            highlightthickness=0, bd=0, cursor="hand2", takefocus=0,
        )

        def redraw(_event=None, bg=None):
            self._draw_toolbar_icon(canvas, icon, bg=bg or base_bg)

        def on_enter(_event=None):
            redraw(bg=active_bg)

        def on_leave(_event=None):
            redraw(bg=base_bg)

        def on_click(_event=None):
            # Tooltip 的显示发生在 hover 阶段。若 command 随后打开模态窗口，
            # Tk 会停在当前点击回调里，后续绑定直到模态窗口关闭才有机会执行。
            # 因此必须在进入 command 之前同步隐藏提示，而不能依赖另一个
            # <ButtonPress-1> 绑定来收尾。
            self.hide_info_tooltip()
            try:
                self.update_idletasks()
            except tk.TclError:
                pass
            return command()

        canvas.bind("<Configure>", redraw)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Button-1>", on_click)
        canvas.after_idle(redraw)
        if tooltip_text:
            self._bind_info_tooltip(canvas, tooltip_text, compact=True)
        canvas.accessible_text = tooltip_text
        # CSV 校验引导期间，“应用修改”和“删除所选行 / 列”仍必须能直接执行。
        # 用显式标记而不是读取 Canvas 文本（图标按钮没有 text 属性）。
        canvas._csv_validation_guard_bypass = tooltip_text in {
            "应用修改", "删除所选行 / 列"
        }
        return canvas

    def _integrated_icon_static(self, parent, icon, width=27):
        """一体式控件中的不可点击图标段。"""
        canvas = tk.Canvas(
            parent,
            width=width,
            height=21,
            bg="white",
            highlightthickness=0,
            bd=0,
            takefocus=0,
        )
        canvas.bind("<Configure>", lambda _event: self._draw_toolbar_icon(canvas, icon))
        canvas.after_idle(lambda: self._draw_toolbar_icon(canvas, icon))
        return canvas

    def _integrated_centered_value(self, parent, variable, pixel_width=42):
        """固定像素宽度并真正按几何中心放置的数值段。"""
        cell = tk.Frame(parent, bg="white", width=pixel_width, height=21)
        cell.pack_propagate(False)
        label = tk.Label(
            cell,
            textvariable=variable,
            anchor="center",
            font=("Consolas", 8, "bold"),
            bg="white",
            fg="#334155",
            bd=0,
            padx=0,
            pady=0,
        )
        label.place(relx=0.5, rely=0.5, anchor="center")
        cell.label = label
        return cell

    def _integrated_plain_entry_box(self, parent, width=10, inner_padx=7):
        """带白色内部留白的日期输入段；返回容器并通过 .entry 暴露 Entry。"""
        cell = self._integrated_cell(parent)
        entry = tk.Entry(
            cell,
            width=width,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            bg="white",
            fg="#253044",
            insertbackground="#253044",
            highlightthickness=0,
            justify="center",
        )
        entry.pack(fill="both", expand=True, padx=inner_padx, pady=0)
        cell.entry = entry
        return cell

    def _integrated_counter(self, parent, variable):
        """紧凑结果计数区；0/0 只保留必要的左右呼吸空间。"""
        return tk.Label(
            parent,
            textvariable=variable,
            width=3,
            anchor="center",
            font=("Microsoft YaHei", 7),
            bg="white",
            fg="#64748b",
            padx=0,
        )

    def _integrated_static_label(self, parent, text):
        """一体式控件中的静态文本段。"""
        return tk.Label(
            parent,
            text=text,
            anchor="center",
            font=("Microsoft YaHei", 8),
            bg="white",
            fg="#5f6879",
            padx=4,
            pady=1,
        )

    def _integrated_plain_entry(self, parent, width=10):
        """一体式控件中的纯输入段；无独立边框。"""
        return tk.Entry(
            parent,
            width=width,
            font=("Consolas", 9),
            relief="flat",
            bd=0,
            bg="white",
            fg="#253044",
            insertbackground="#253044",
            highlightthickness=0,
            justify="center",
        )

    def _toolbar_text_width(self, text):
        """按实际显示宽度计算：中文宽字符按 2，ASCII 按 1，只留极小横向余量。"""
        import unicodedata

        display_width = 0
        for char in str(text):
            display_width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        return max(1, display_width + 1)

    def _button(self, parent, text, command, primary=False):
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="Toolbar.Primary.TButton" if primary else "Toolbar.TButton",
            cursor="hand2",
            takefocus=False,
            width=self._toolbar_text_width(text),
        )

    def _small_button(self, parent, text, command, primary=False):
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="Toolbar.Primary.TButton" if primary else "Toolbar.TButton",
            cursor="hand2",
            takefocus=False,
            width=self._toolbar_text_width(text),
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
        button = ttk.Button(
            parent,
            text=f"⌕{symbol}",
            command=command,
            style="Toolbar.Nav.TButton",
            cursor="hand2",
            takefocus=False,
            width=3,
        )
        button.accessible_text = accessible_text
        return button

    def _compact_button(self, parent, text, command):
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="Toolbar.Nav.TButton",
            cursor="hand2",
            takefocus=False,
            width=1,
        )

    def _panel_title(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei", 11, "bold"),
            bg="#f7f8fa",
            fg="#172033",
        )
