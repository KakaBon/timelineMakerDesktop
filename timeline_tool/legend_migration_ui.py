"""事件迁移区界面与选择菜单。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendMigrationUIMixin:
    def build_event_migration_controls(self, parent):
        """建立统一事件迁移区；标题、列表表头固定，只有迁移行本体滚动。"""
        self.event_migration_rules = [self._new_event_migration_rule()]
        self._migration_popup = None
        self._migration_popup_trigger = None

        header = tk.Frame(parent, bg="#eef1f5", height=25)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="事件迁移",
            bg="#eef1f5",
            fg="#526075",
            anchor="w",
            padx=8,
            font=("Microsoft YaHei", 8, "bold"),
        ).pack(side="left", fill="y")

        add_shell = self._integrated_shell(header)
        add_shell.pack(side="left", padx=(2, 0), pady=1)
        self._integrated_icon_action(
            add_shell,
            "add",
            self._add_event_migration_rule,
            tooltip_text="添加迁移行",
            width=23,
        ).pack(side="left", fill="y", padx=1, pady=1)

        self._small_button(
            header,
            "事件迁移",
            self.execute_event_migration_plan,
        ).pack(side="right", padx=0, pady=1)

        # 下级区标题行与主体之间固定一条分隔线，与左侧分类控制区一致。
        tk.Frame(parent, bg="#cfd5df", height=1).pack(fill="x")

        self.event_migration_body = tk.Frame(parent, bg="white")
        self.event_migration_body.pack(fill="both", expand=True)
        self.event_migration_body.grid_rowconfigure(1, weight=1)
        self.event_migration_body.grid_columnconfigure(0, weight=1)

        # “源分类 | 事件 | 目标分类”固定在滚动内容之外。右侧留出 × 列，
        # 下沿再加一条与分类表表头相同的分隔线。
        column_header = tk.Frame(
            self.event_migration_body, bg="#eef1f5", height=29
        )
        column_header.grid(row=0, column=0, sticky="ew")
        column_header.grid_propagate(False)
        column_header.grid_columnconfigure(0, weight=1, uniform="migration_header")
        column_header.grid_columnconfigure(1, weight=1, uniform="migration_header")
        column_header.grid_columnconfigure(2, weight=1, uniform="migration_header")
        column_header.grid_columnconfigure(3, weight=0, minsize=22)

        for column, heading in enumerate(("源分类", "事件", "目标分类")):
            tk.Label(
                column_header,
                text=heading,
                bg="#eef1f5",
                fg="#60708a",
                font=("Microsoft YaHei", 8),
                anchor="center",
            ).grid(row=0, column=column, sticky="nsew", padx=2, pady=0)
        column_header.grid_rowconfigure(0, weight=1)
        tk.Frame(column_header, bg="#cfd5df", height=1).place(
            x=0, rely=1.0, relwidth=1.0, y=-1
        )

        self.event_migration_canvas = tk.Canvas(
            self.event_migration_body,
            bg="white",
            highlightthickness=0,
            bd=0,
            yscrollincrement=24,
        )
        self.event_migration_scrollbar = self._make_scrollbar(
            self.event_migration_body,
            orient="vertical",
            command=self.event_migration_canvas.yview,
        )
        self.event_migration_canvas.configure(
            yscrollcommand=self.event_migration_scrollbar.set
        )
        self.event_migration_canvas.grid(row=1, column=0, sticky="nsew")
        # 表头右侧只补同色轨道背景，不让真正滑块侵入表头。
        self.event_migration_scrollbar_cap = tk.Frame(
            self.event_migration_body,
            bg=getattr(self, "_scrollbar_trough_color", "#e6e9ef"),
            width=14,
            takefocus=0,
        )
        self.event_migration_scrollbar_cap.grid(row=0, column=1, sticky="nsew")
        # 真正滚动条固定在 × 列右侧，只覆盖迁移内容区。
        self.event_migration_scrollbar.grid(row=1, column=1, sticky="ns")

        self.event_migration_content = tk.Frame(
            self.event_migration_canvas, bg="white"
        )
        self.event_migration_window = self.event_migration_canvas.create_window(
            (0, 0), window=self.event_migration_content, anchor="nw"
        )
        self.event_migration_content.bind(
            "<Configure>", self._update_event_migration_scrollregion, add="+"
        )
        self.event_migration_canvas.bind(
            "<Configure>", self._resize_event_migration_window, add="+"
        )

        if not getattr(self, "_migration_popup_global_binding_installed", False):
            self.bind_all("<Button-1>", self._on_migration_global_click, add="+")
            self._migration_popup_global_binding_installed = True

        if not getattr(self, "_migration_plan_wheel_binding_installed", False):
            self.bind_all(
                "<MouseWheel>", self._on_event_migration_plan_mousewheel, add="+"
            )
            self.bind_all(
                "<Button-4>", self._on_event_migration_plan_mousewheel, add="+"
            )
            self.bind_all(
                "<Button-5>", self._on_event_migration_plan_mousewheel, add="+"
            )
            self._migration_plan_wheel_binding_installed = True

        self._render_event_migration_plan()

    def _resize_event_migration_window(self, event):
        canvas = getattr(self, "event_migration_canvas", None)
        window = getattr(self, "event_migration_window", None)
        if canvas is None or window is None:
            return
        try:
            canvas.itemconfigure(window, width=max(1, event.width))
        except tk.TclError:
            return
        self.after_idle(self._update_event_migration_scrollregion)

    def _update_event_migration_scrollregion(self, _event=None):
        canvas = getattr(self, "event_migration_canvas", None)
        content = getattr(self, "event_migration_content", None)
        if canvas is None or content is None:
            return
        try:
            content.update_idletasks()
            bounds = canvas.bbox(getattr(self, "event_migration_window", None))
            content_height = max(1, bounds[3] if bounds else content.winfo_reqheight())
            canvas_width = max(1, canvas.winfo_width())
            canvas.configure(scrollregion=(0, 0, canvas_width, content_height))
            if content_height <= max(1, canvas.winfo_height()) + 1:
                canvas.yview_moveto(0)
        except tk.TclError:
            pass

    def _pointer_over_event_migration_canvas(self):
        canvas = getattr(self, "event_migration_canvas", None)
        if canvas is None:
            return False
        try:
            px, py = self.winfo_pointerx(), self.winfo_pointery()
            left, top = canvas.winfo_rootx(), canvas.winfo_rooty()
            right = left + canvas.winfo_width()
            bottom = top + canvas.winfo_height()
            return left <= px < right and top <= py < bottom
        except tk.TclError:
            return False

    def _on_event_migration_plan_mousewheel(self, event):
        popup = getattr(self, "_migration_popup", None)
        if popup is not None:
            try:
                if popup.winfo_exists():
                    px, py = self.winfo_pointerx(), self.winfo_pointery()
                    left, top = popup.winfo_rootx(), popup.winfo_rooty()
                    right = left + popup.winfo_width()
                    bottom = top + popup.winfo_height()
                    if left <= px < right and top <= py < bottom:
                        return None
            except tk.TclError:
                pass

        if not self._pointer_over_event_migration_canvas():
            return None

        canvas = getattr(self, "event_migration_canvas", None)
        if canvas is None:
            return None
        if getattr(event, "num", None) == 4:
            direction = -1
        elif getattr(event, "num", None) == 5:
            direction = 1
        elif getattr(event, "delta", 0) > 0:
            direction = -1
        elif getattr(event, "delta", 0) < 0:
            direction = 1
        else:
            return "break"
        try:
            canvas.yview_scroll(direction, "units")
        except tk.TclError:
            pass
        return "break"

    @staticmethod
    def _new_event_migration_rule():
        return {
            "source": "",
            "target": "",
            "selections_by_source": {},
        }

    def reset_event_migration_plan(self):
        """外部数据整体变化后清空尚未执行的迁移计划，避免旧事件引用失效。"""
        if not hasattr(self, "event_migration_rules"):
            return
        self._close_migration_popup()
        self.event_migration_rules = [self._new_event_migration_rule()]
        if hasattr(self, "event_migration_body"):
            self._render_event_migration_plan()

    def _render_event_migration_plan(self):
        content = getattr(self, "event_migration_content", None)
        if content is None:
            return
        self._close_migration_popup()
        for child in content.winfo_children():
            child.destroy()

        table = tk.Frame(content, bg="white")
        table.pack(fill="x", expand=True, padx=6, pady=(5, 4))
        table.grid_columnconfigure(0, weight=1, uniform="migration")
        table.grid_columnconfigure(1, weight=1, uniform="migration")
        table.grid_columnconfigure(2, weight=1, uniform="migration")
        table.grid_columnconfigure(3, weight=0)

        for index, rule in enumerate(self.event_migration_rules):
            self._build_event_migration_rule_row(table, index, rule)

        self.after_idle(self._update_event_migration_scrollregion)

    def _render_event_migration_mode(self):
        self._render_event_migration_plan()

    def _build_event_migration_rule_row(self, parent, index, rule):
        row_number = index
        source = self._create_event_migration_choice(
            parent, rule, role="source", row_index=index
        )
        source.grid(row=row_number, column=0, sticky="ew", padx=(0, 2), pady=2)
        rule["source_control"] = source

        event_button = tk.Button(
            parent,
            text="",
            command=lambda r=rule: self._open_migration_event_popup(r),
            font=("Microsoft YaHei", 8),
            relief="solid",
            bd=1,
            padx=3,
            pady=0,
            height=1,
            bg="white",
            fg="#253044",
            activebackground="#edf2f7",
            activeforeground="#253044",
            highlightthickness=0,
            cursor="hand2",
            takefocus=False,
        )
        event_button.grid(row=row_number, column=1, sticky="ew", padx=2, pady=2)
        rule["event_button"] = event_button
        self._refresh_migration_event_button(rule)

        target = self._create_event_migration_choice(
            parent, rule, role="target", row_index=index
        )
        target.grid(row=row_number, column=2, sticky="ew", padx=2, pady=2)
        rule["target_control"] = target

        remove = tk.Button(
            parent,
            text="×",
            command=lambda i=index: self._remove_event_migration_rule(i),
            font=("Microsoft YaHei", 8),
            relief="flat",
            bd=0,
            padx=3,
            pady=0,
            bg="white",
            fg="#94a3b8",
            activebackground="#edf2f7",
            activeforeground="#475569",
            highlightthickness=0,
            cursor="hand2",
            takefocus=False,
        )
        remove.grid(row=row_number, column=3, padx=(2, 0), pady=2)

    def _create_event_migration_choice(self, parent, rule, role, row_index):
        source = str(rule.get("source", "")).strip()
        source_has_events = bool(source and self._migration_events_for_category(source))
        enabled = True
        if role == "target":
            enabled = source_has_events

        selected_value = str(rule.get(role, "")).strip()
        if selected_value:
            display_text = selected_value
        elif role == "target" and source and not source_has_events:
            display_text = "无事件"
        else:
            display_text = "请选择"

        border = "#8fa3b8" if enabled or role == "source" else "#d7dce5"
        bg = "white" if enabled or role == "source" else "#f4f5f7"
        if selected_value:
            fg = "#253044" if enabled or role == "source" else "#9aa4b2"
        else:
            fg = "#94a3b8" if enabled or role == "source" else "#b5bdc9"
        cursor = "hand2" if enabled or role == "source" else "arrow"

        control = tk.Frame(
            parent,
            bg=border,
            bd=0,
            highlightthickness=0,
            height=23,
        )
        control.grid_propagate(False)
        control.grid_columnconfigure(0, weight=1)
        control.grid_columnconfigure(1, weight=0)
        control.grid_rowconfigure(0, weight=1)

        label = tk.Label(
            control,
            text=display_text,
            anchor="center",
            font=("Microsoft YaHei", 8),
            bg=bg,
            fg=fg,
            padx=3,
            pady=0,
            cursor=cursor,
        )
        label.grid(row=0, column=0, sticky="nsew", padx=(1, 0), pady=1)
        arrow = tk.Label(
            control,
            text="▼",
            anchor="center",
            font=("Microsoft YaHei", 7),
            bg=bg,
            fg="#263247" if enabled or role == "source" else "#b5bdc9",
            padx=5,
            pady=0,
            cursor=cursor,
        )
        arrow.grid(row=0, column=1, sticky="ns", padx=(0, 1), pady=1)

        trigger = {
            "control": control,
            "label": label,
            "arrow": arrow,
            "rule": rule,
            "role": role,
            "row_index": row_index,
            "enabled": enabled or role == "source",
        }
        control._migration_trigger = trigger
        if trigger["enabled"]:
            for widget in (control, label, arrow):
                widget.bind(
                    "<Button-1>",
                    lambda _event, t=trigger: self._open_event_migration_choice_popup(t),
                )
        return control

    def _migration_is_descendant(self, widget, ancestor):
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

    def _on_migration_global_click(self, event):
        popup = getattr(self, "_migration_popup", None)
        if popup is None:
            return None
        try:
            if not popup.winfo_exists():
                self._migration_popup = None
                self._migration_popup_trigger = None
                return None
        except tk.TclError:
            self._migration_popup = None
            self._migration_popup_trigger = None
            return None

        widget = getattr(event, "widget", None)
        if self._migration_is_descendant(widget, popup):
            return None

        trigger = getattr(self, "_migration_popup_trigger", None)
        trigger_widget = trigger.get("control") if isinstance(trigger, dict) else trigger
        if trigger_widget is not None and self._migration_is_descendant(widget, trigger_widget):
            return None

        self._close_migration_popup()
        return None

    def _close_migration_popup(self):
        popup = getattr(self, "_migration_popup", None)
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:
                pass
        self._migration_popup = None
        self._migration_popup_trigger = None

    def _migration_used_sources_before(self, row_index):
        return {
            rule.get("source", "")
            for rule in self.event_migration_rules[:row_index]
            if rule.get("source", "")
        }

    def _open_event_migration_choice_popup(self, trigger):
        if not trigger.get("enabled", True):
            return

        current_popup = getattr(self, "_migration_popup", None)
        current_trigger = getattr(self, "_migration_popup_trigger", None)
        if current_popup is not None and current_trigger is trigger:
            self._close_migration_popup()
            return

        self._close_migration_popup()
        if hasattr(self, "_close_category_search_field_popup"):
            self._close_category_search_field_popup()
        if hasattr(self, "_close_category_search_icon_popup"):
            self._close_category_search_icon_popup()

        role = trigger["role"]
        row_index = trigger["row_index"]
        rule = trigger["rule"]
        categories = list(getattr(self, "categories", []))
        if not categories:
            return

        all_source = "所有分类"
        choices = ([all_source] + categories) if role == "source" else categories
        used_before = self._migration_used_sources_before(row_index)
        counts = {category: 0 for category in categories}
        for row in getattr(self, "rows", []):
            category = row.get("category", "未分类")
            counts[category] = counts.get(category, 0) + 1

        # 源/目标分类菜单也属于事件迁移区内部浮层：父容器直接使用
        # migration_panel，因此纵向尺寸不会越出该下级区。
        panel = getattr(self, "migration_panel", None)
        if panel is None:
            panel = self.event_migration_body
        popup = tk.Frame(panel, bg="#8fa3b8", bd=0, highlightthickness=0)
        self._migration_popup = popup
        self._migration_popup_trigger = trigger

        viewport = tk.Frame(popup, bg="white")
        viewport.pack(fill="both", expand=True, padx=1, pady=1)
        viewport.grid_rowconfigure(0, weight=1)
        viewport.grid_columnconfigure(0, weight=1)

        list_canvas = tk.Canvas(
            viewport, bg="white", highlightthickness=0, bd=0, yscrollincrement=22
        )
        list_scrollbar = self._make_scrollbar(
            viewport, orient="vertical", command=list_canvas.yview
        )
        list_canvas.configure(yscrollcommand=list_scrollbar.set)
        list_canvas.grid(row=0, column=0, sticky="nsew")

        body = tk.Frame(list_canvas, bg="white")
        body_window = list_canvas.create_window((0, 0), window=body, anchor="nw")

        rows = []
        current = rule.get(role, "")
        for value in choices:
            disabled_reason = None
            display_value = value
            if role == "source":
                if value == all_source:
                    if not getattr(self, "rows", []):
                        disabled_reason = "empty"
                        display_value = "所有分类（无事件）"
                    elif used_before:
                        disabled_reason = "used"
                else:
                    if counts.get(value, 0) == 0:
                        disabled_reason = "empty"
                        display_value = f"{value}（空）"
                    elif all_source in used_before or value in used_before:
                        disabled_reason = "used"
            else:
                source = rule.get("source", "")
                if source and source != all_source and value == source:
                    disabled_reason = "same"

            is_disabled = disabled_reason is not None
            bg = "#dbeafe" if value == current else "white"
            fg = "#b5bdc9" if is_disabled else "#253044"
            label = tk.Label(
                body,
                text=display_value,
                anchor="center",
                font=("Microsoft YaHei", 8),
                bg=bg,
                fg=fg,
                padx=5,
                pady=2,
                cursor="arrow" if is_disabled else "hand2",
            )
            label.pack(fill="x")
            rows.append((label, value, is_disabled))

        def highlight(target):
            for label, _value, is_disabled in rows:
                if is_disabled:
                    label.configure(bg="white")
                else:
                    label.configure(bg="#dbeafe" if label is target else "white")

        for label, value, is_disabled in rows:
            if is_disabled:
                continue
            label.bind("<Enter>", lambda _e, target=label: highlight(target))
            label.bind(
                "<Button-1>",
                lambda _e, v=value, t=trigger: self._select_event_migration_choice(t, v),
            )

        def sync_scrollregion(_event=None):
            try:
                body.update_idletasks()
                list_canvas.itemconfigure(body_window, width=max(1, list_canvas.winfo_width()))
                bbox = list_canvas.bbox(body_window)
                list_canvas.configure(scrollregion=bbox or (0, 0, 1, 1))
                need = body.winfo_reqheight() > max(1, list_canvas.winfo_height()) + 1
                if need:
                    list_scrollbar.grid(row=0, column=1, sticky="ns")
                else:
                    list_scrollbar.grid_remove()
                    list_canvas.yview_moveto(0)
            except tk.TclError:
                pass

        body.bind("<Configure>", sync_scrollregion, add="+")
        list_canvas.bind("<Configure>", sync_scrollregion, add="+")

        def on_wheel(event):
            if getattr(event, "num", None) == 4:
                direction = -1
            elif getattr(event, "num", None) == 5:
                direction = 1
            elif getattr(event, "delta", 0) > 0:
                direction = -1
            elif getattr(event, "delta", 0) < 0:
                direction = 1
            else:
                return "break"
            list_canvas.yview_scroll(direction, "units")
            return "break"

        for widget in (popup, viewport, list_canvas, body):
            widget.bind("<MouseWheel>", on_wheel, add="+")
            widget.bind("<Button-4>", on_wheel, add="+")
            widget.bind("<Button-5>", on_wheel, add="+")
        for label, _value, _disabled in rows:
            label.bind("<MouseWheel>", on_wheel, add="+")
            label.bind("<Button-4>", on_wheel, add="+")
            label.bind("<Button-5>", on_wheel, add="+")

        self.update_idletasks()
        panel.update_idletasks()
        control = trigger["control"]
        control.update_idletasks()
        popup.update_idletasks()

        panel_left = panel.winfo_rootx()
        panel_top = panel.winfo_rooty()
        panel_width = max(1, panel.winfo_width())
        panel_height = max(1, panel.winfo_height())
        control_left = control.winfo_rootx() - panel_left
        control_top = control.winfo_rooty() - panel_top
        control_bottom = control_top + control.winfo_height()

        # 仍保持普通下拉框的紧凑形态，但若“未分类（空）”之类注释文字
        # 比触发框更宽，就只把菜单扩到足够完整显示文字；绝不越出迁移区右沿。
        content_width = max(1, body.winfo_reqwidth())
        scrollbar_width = max(14, list_scrollbar.winfo_reqwidth())
        wanted_width = max(control.winfo_width(), content_width + scrollbar_width + 4)
        width = max(1, min(wanted_width, panel_width - control_left - 1))
        requested_height = max(24, body.winfo_reqheight() + 2)
        space_below = max(0, panel_height - control_bottom - 1)
        space_above = max(0, control_top - 1)

        # 优先像普通下拉框一样向下展开；只有下方连一项都容不下时才向上。
        if space_below >= 24 or space_below >= space_above:
            y = control_bottom
            height = min(requested_height, max(1, space_below))
        else:
            height = min(requested_height, max(1, space_above))
            y = max(1, control_top - height)

        # 只裁剪菜单整体高度，列表项本身绝不拉伸或变形。
        height = max(1, min(height, panel_height - y - 1))
        popup.place(x=control_left, y=y, width=width, height=height)
        popup.lift()
        self.after_idle(sync_scrollregion)

    def _select_event_migration_choice(self, trigger, value):
        rule = trigger["rule"]
        role = trigger["role"]
        row_index = trigger["row_index"]
        old_value = rule.get(role, "")
        rule[role] = value

        if role == "source":
            all_source = "所有分类"
            if rule.get("target") == value and value != all_source:
                rule["target"] = ""
            if old_value != value:
                rule.setdefault("selections_by_source", {}).setdefault(value, set())

            # “所有分类”与任何具体源分类都存在范围重叠，因此后续行不能继续
            # 保留会与当前源范围重叠的选择。
            for later in self.event_migration_rules[row_index + 1:]:
                later_source = later.get("source", "")
                if value == all_source or later_source in {value, all_source}:
                    later["source"] = ""
                    later["target"] = ""

        self._close_migration_popup()
        self._render_event_migration_plan()

    def _add_event_migration_rule(self):
        self.event_migration_rules.append(self._new_event_migration_rule())
        self._render_event_migration_plan()
        canvas = getattr(self, "event_migration_canvas", None)
        if canvas is not None:
            self.after_idle(lambda: canvas.yview_moveto(1.0))

    def _remove_event_migration_rule(self, index):
        if 0 <= index < len(self.event_migration_rules):
            self.event_migration_rules.pop(index)
        if not self.event_migration_rules:
            self.event_migration_rules.append(self._new_event_migration_rule())
        self._render_event_migration_plan()

    def _migration_events_for_category(self, category):
        if category == "所有分类":
            return list(getattr(self, "rows", []))
        return [
            row for row in getattr(self, "rows", [])
            if row.get("category") == category
        ]

    def _migration_event_label(self, row, include_category=False):
        title = str(row.get("title", "")).strip()
        date = str(row.get("date", "")).strip()
        label = f"{date}  {title}" if date else title
        if include_category:
            category = str(row.get("category", "未分类")).strip() or "未分类"
            label = f"[{category}]  {label}"
        return label

    def _refresh_migration_event_button(self, rule):
        button = rule.get("event_button")
        if button is None:
            return
        source = rule.get("source", "")
        if not source:
            button.configure(text="先选源分类", state="disabled", fg="#94a3b8")
            return

        events = self._migration_events_for_category(source)
        valid_ids = {row.get("_id") for row in events}
        selected = rule.setdefault("selections_by_source", {}).setdefault(source, set())
        selected.intersection_update(valid_ids)
        if not events:
            button.configure(text="无事件", state="disabled", fg="#94a3b8")
            return
        text = "所有事件" if selected == valid_ids else f"已选 {len(selected)}/{len(events)}"
        button.configure(text=text, state="normal", fg="#253044")

    def _open_migration_event_popup(self, rule):
        button = rule.get("event_button")
        source = rule.get("source", "")
        if button is None or not source:
            return

        trigger = button
        if getattr(self, "_migration_popup", None) is not None and getattr(
            self, "_migration_popup_trigger", None
        ) is trigger:
            self._close_migration_popup()
            return

        events = self._migration_events_for_category(source)
        if not events:
            return

        self._close_migration_popup()
        if hasattr(self, "_close_category_search_field_popup"):
            self._close_category_search_field_popup()
        if hasattr(self, "_close_category_search_icon_popup"):
            self._close_category_search_icon_popup()

        selected = rule.setdefault("selections_by_source", {}).setdefault(source, set())
        valid_ids = {row.get("_id") for row in events}
        selected.intersection_update(valid_ids)

        popup = tk.Frame(self, bg="#8fa3b8", bd=0, highlightthickness=0)
        self._migration_popup = popup
        self._migration_popup_trigger = trigger

        canvas = tk.Canvas(
            popup,
            bg="white",
            highlightthickness=0,
            bd=0,
            yscrollincrement=25,
            xscrollincrement=30,
        )
        vbar = self._make_scrollbar(
            popup, orient="vertical", command=canvas.yview
        )
        hbar = self._make_scrollbar(
            popup, orient="horizontal", command=canvas.xview
        )
        canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        popup.grid_rowconfigure(0, weight=1)
        popup.grid_columnconfigure(0, weight=1)

        inner = tk.Frame(canvas, bg="white")
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        event_vars = {}
        whole_var = tk.BooleanVar(value=bool(valid_ids) and selected == valid_ids)

        def refresh_scrollregion(_event=None):
            inner.update_idletasks()
            req_w = max(1, inner.winfo_reqwidth())
            req_h = max(1, inner.winfo_reqheight())
            canvas.itemconfigure(window, width=req_w, height=req_h)
            canvas.configure(scrollregion=(0, 0, req_w, req_h))

        def toggle_whole():
            if whole_var.get():
                selected.clear()
                selected.update(valid_ids)
            else:
                selected.clear()
            for event_id, var in event_vars.items():
                var.set(event_id in selected)
            self._refresh_migration_event_button(rule)

        def wheel_direction(event):
            if getattr(event, "num", None) == 4:
                return -1
            if getattr(event, "num", None) == 5:
                return 1
            delta = getattr(event, "delta", 0)
            if delta > 0:
                return -1
            if delta < 0:
                return 1
            return 0

        def on_vertical_wheel(event):
            direction = wheel_direction(event)
            if direction:
                canvas.yview_scroll(direction, "units")
            return "break"

        def on_horizontal_wheel(event):
            direction = wheel_direction(event)
            if direction:
                canvas.xview_scroll(direction, "units")
            return "break"

        def bind_wheel(widget):
            widget.bind("<MouseWheel>", on_vertical_wheel)
            widget.bind("<Shift-MouseWheel>", on_horizontal_wheel)
            widget.bind("<Button-4>", on_vertical_wheel)
            widget.bind("<Button-5>", on_vertical_wheel)

        whole = tk.Checkbutton(
            inner,
            text="所有事件",
            variable=whole_var,
            command=toggle_whole,
            anchor="w",
            justify="left",
            bg="white",
            activebackground="white",
            fg="#253044",
            font=("Microsoft YaHei", 8, "bold"),
            bd=0,
            highlightthickness=0,
            padx=5,
            pady=2,
        )
        whole.pack(fill="x")
        bind_wheel(whole)

        include_category = source == "所有分类"
        for event_row in events:
            event_id = event_row.get("_id")
            var = tk.BooleanVar(value=event_id in selected)
            event_vars[event_id] = var

            def toggle(eid=event_id, state=var):
                if state.get():
                    selected.add(eid)
                else:
                    selected.discard(eid)
                whole_var.set(bool(valid_ids) and selected == valid_ids)
                self._refresh_migration_event_button(rule)

            check = tk.Checkbutton(
                inner,
                text=self._migration_event_label(
                    event_row, include_category=include_category
                ),
                variable=var,
                command=toggle,
                anchor="w",
                justify="left",
                bg="white",
                activebackground="white",
                fg="#253044",
                font=("Microsoft YaHei", 8),
                bd=0,
                highlightthickness=0,
                padx=5,
                pady=2,
            )
            check.pack(fill="x")
            bind_wheel(check)

        bind_wheel(canvas)
        bind_wheel(inner)
        inner.bind("<Configure>", refresh_scrollregion)

        self.update_idletasks()
        inner.update_idletasks()
        button.update_idletasks()
        popup.update_idletasks()

        # 事件菜单横向范围固定为当前迁移行的“源分类”左边沿到
        # “目标分类”右边沿；纵向仍严格限制在事件迁移内容区内部。
        migration_body = getattr(self, "event_migration_body", None)
        if migration_body is None:
            migration_body = button.master
        migration_body.update_idletasks()

        body_top_root = migration_body.winfo_rooty()
        body_height = max(1, migration_body.winfo_height())
        body_bottom_root = body_top_root + body_height

        source_control = rule.get("source_control")
        target_control = rule.get("target_control")
        try:
            popup_left_root = source_control.winfo_rootx()
            popup_right_root = target_control.winfo_rootx() + target_control.winfo_width()
            width = max(1, popup_right_root - popup_left_root)
        except (AttributeError, tk.TclError):
            # 极端情况下控件已销毁，则退回事件按钮自身附近，避免菜单失效。
            popup_left_root = button.winfo_rootx()
            width = max(1, button.winfo_width())
        row_height = 25
        content_width = inner.winfo_reqwidth()
        # 先按整个迁移区宽度判断是否仍需要横向滚动条；极长标题仍可横滚。
        show_hbar = content_width > max(1, width - 4)
        hbar_height = 14 if show_hbar else 0

        desired_rows = min(7, len(events) + 1)
        desired_height = desired_rows * row_height + 2 + hbar_height

        button_top_root = button.winfo_rooty()
        button_bottom_root = button_top_root + button.winfo_height()
        space_below = max(0, body_bottom_root - button_bottom_root)
        space_above = max(0, button_top_root - body_top_root)

        # 正常优先向下展开；下方不够时，若上方空间更大则向上展开。
        if space_below >= desired_height or space_below >= space_above:
            popup_top_root = button_bottom_root
            available_height = space_below
        else:
            available_height = space_above
            popup_top_root = max(body_top_root, button_top_root - min(desired_height, available_height))

        # 最终高度硬限制在事件迁移区内部。即使只能显示很少几行，也用纵向滚动查看。
        height = max(1, min(desired_height, available_height))
        if popup_top_root + height > body_bottom_root:
            height = max(1, body_bottom_root - popup_top_root)

        usable_canvas_height = max(1, height - 2 - hbar_height)
        content_height = inner.winfo_reqheight()
        show_vbar = content_height > usable_canvas_height

        canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(1, 0 if show_vbar else 1),
            pady=(1, 0 if show_hbar else 1),
        )
        if show_vbar:
            vbar.grid(
                row=0,
                column=1,
                sticky="ns",
                pady=(1, 0 if show_hbar else 1),
                padx=(0, 1),
            )
        if show_hbar:
            hbar.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=1,
                pady=(0, 1),
            )

        x = popup_left_root - self.winfo_rootx()
        y = popup_top_root - self.winfo_rooty()
        popup.place(x=x, y=y, width=width, height=height)
        popup.lift()
        self.after_idle(refresh_scrollregion)
