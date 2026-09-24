"""分类行选择、显示状态与重命名。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendRowsMixin:
    def _draw_eye_icon(self, canvas, hidden=False):
        canvas.delete("all")
        fg = "#a7adb7" if hidden else "#526075"
        try:
            width = max(22, int(canvas.winfo_width()))
            height = max(20, int(canvas.winfo_height()))
        except tk.TclError:
            width, height = 22, 20
        cx, cy = width / 2, height / 2
        canvas.create_oval(
            cx - 8, cy - 5, cx + 8, cy + 5,
            outline=fg, width=1.5,
        )
        canvas.create_oval(
            cx - 2, cy - 2, cx + 2, cy + 2,
            fill=fg, outline=fg,
        )
        if hidden:
            canvas.create_line(
                cx - 8, cy + 7, cx + 8, cy - 7,
                fill=fg, width=1.8,
            )

    def _refresh_category_select_all_state(self):
        selectable = [name for name in self.categories if name != "未分类"]
        all_selected = bool(selectable) and all(
            name in self.selected_categories for name in selectable
        )
        var = getattr(self, "legend_select_all_var", None)
        if var is not None:
            var.set(all_selected)
        self._refresh_category_header_eye()

    def _category_row_background(self, category):
        if category in getattr(self, "selected_categories", set()):
            return "#dbeafe"
        counts = getattr(self, "legend_category_counts", {})
        if counts.get(category, 0) == 0:
            return "#f0f2f5"
        return "white"

    def _category_row_foregrounds(self, category):
        counts = getattr(self, "legend_category_counts", {})
        if counts.get(category, 0) == 0 and category not in getattr(self, "selected_categories", set()):
            return "#8b95a5", "#9aa4b2"
        return "#30394c", "#60708a"

    def _refresh_category_row_visual(self, category, reapply_focus=True):
        row = getattr(self, "legend_row_widgets", {}).get(category)
        if row is None:
            return
        try:
            if not row.winfo_exists():
                return
        except tk.TclError:
            return

        bg = self._category_row_background(category)
        self._set_category_row_background(row, bg)
        name_fg, count_fg = self._category_row_foregrounds(category)
        name_label = getattr(self, "legend_name_labels", {}).get(category)
        count_label = getattr(self, "legend_count_labels", {}).get(category)
        try:
            if name_label is not None and name_label.winfo_exists():
                name_label.configure(fg=name_fg)
            if count_label is not None and count_label.winfo_exists():
                count_label.configure(fg=count_fg)
        except tk.TclError:
            pass

        if reapply_focus and getattr(self, "category_search_focus_category", None) == category:
            self._apply_category_search_field_highlight(category)

    def _refresh_all_category_row_visuals(self):
        for category in getattr(self, "categories", []):
            self._refresh_category_row_visual(category, reapply_focus=False)
        focus = getattr(self, "category_search_focus_category", None)
        if focus:
            self._apply_category_search_field_highlight(focus)
        self._refresh_category_header_eye()

    def _category_visibility_targets(self):
        selected = [
            category for category in getattr(self, "categories", [])
            if category in getattr(self, "selected_categories", set())
        ]
        return selected if selected else list(getattr(self, "categories", []))

    def _refresh_category_header_eye(self):
        canvas = getattr(self, "legend_header_eye_canvas", None)
        if canvas is None:
            return
        try:
            if not canvas.winfo_exists():
                return
        except tk.TclError:
            return
        targets = self._category_visibility_targets()
        hidden = bool(targets) and all(
            category in getattr(self, "hidden_categories", set())
            for category in targets
        )
        canvas.configure(bg="#eef1f5")
        self._draw_eye_icon(canvas, hidden=hidden)

    def toggle_selected_category_visibility(self):
        """表头眼睛：有勾选时作用于勾选分类，否则作用于全部分类。"""
        targets = self._category_visibility_targets()
        if not targets:
            return
        should_hide = any(
            category not in self.hidden_categories for category in targets
        )
        if should_hide:
            self.hidden_categories.update(targets)
        else:
            self.hidden_categories.difference_update(targets)

        for category in targets:
            canvas = getattr(self, "legend_eye_canvases", {}).get(category)
            if canvas is not None:
                try:
                    self._draw_eye_icon(canvas, category in self.hidden_categories)
                except tk.TclError:
                    pass
        self._refresh_category_header_eye()
        self.render()

    def _set_category_selected(self, category, selected):
        if category == "未分类":
            return
        if selected:
            self.selected_categories.add(category)
        else:
            self.selected_categories.discard(category)
        self._refresh_category_select_all_state()
        self._refresh_category_row_visual(category)

    def _set_all_categories_selected(self, selected):
        selectable = [name for name in self.categories if name != "未分类"]
        if selected:
            self.selected_categories.update(selectable)
        else:
            self.selected_categories.difference_update(selectable)

        for category, var in getattr(self, "legend_select_vars", {}).items():
            if category != "未分类":
                var.set(selected)
        self._refresh_category_select_all_state()
        self._refresh_all_category_row_visuals()

    def _begin_category_rename(self, category):
        if category == "未分类":
            return
        cell = getattr(self, "legend_name_cells", {}).get(category)
        if cell is None:
            return

        self._cancel_category_rename()
        editor = tk.Entry(
            cell,
            font=("Microsoft YaHei", 8),
            relief="solid",
            bd=1,
            bg="white",
            fg="#253044",
            insertbackground="#253044",
        )
        editor.insert(0, category)
        editor.place(x=1, y=1, relwidth=1, width=-2, relheight=1, height=-2)
        editor.focus_set()
        editor.selection_range(0, tk.END)
        editor.lift()

        self.category_rename_editor = editor
        self.category_rename_old_name = category
        self._category_rename_committing = False
        editor.bind("<Return>", lambda _e: self._finish_category_rename(True))
        editor.bind("<Escape>", lambda _e: self._finish_category_rename(False))
        editor.bind(
            "<FocusOut>",
            lambda _e: self.after_idle(lambda: self._finish_category_rename(True)),
        )

    def _cancel_category_rename(self):
        editor = getattr(self, "category_rename_editor", None)
        if editor is not None:
            try:
                editor.destroy()
            except tk.TclError:
                pass
        self.category_rename_editor = None
        self.category_rename_old_name = None

    def _finish_category_rename(self, commit):
        if getattr(self, "_category_rename_committing", False):
            return "break"
        editor = getattr(self, "category_rename_editor", None)
        old_name = getattr(self, "category_rename_old_name", None)
        if editor is None or not old_name:
            return "break"
        try:
            if not editor.winfo_exists():
                self.category_rename_editor = None
                return "break"
        except tk.TclError:
            self.category_rename_editor = None
            return "break"

        if not commit:
            self._cancel_category_rename()
            return "break"

        new_name = editor.get().strip()
        if new_name == old_name:
            self._cancel_category_rename()
            return "break"

        self._category_rename_committing = True
        try:
            if not new_name:
                messagebox.showwarning("重命名分类", "分类名不能为空。")
                self._category_rename_committing = False
                self.after_idle(editor.focus_set)
                return "break"

            duplicate = any(
                str(category).casefold() == new_name.casefold()
                for category in self.categories
                if category != old_name
            )
            if duplicate:
                messagebox.showwarning(
                    "重命名分类",
                    f"分类“{new_name}”已经存在。",
                )
                self._category_rename_committing = False
                self.after_idle(editor.focus_set)
                return "break"

            confirmed = messagebox.askyesno(
                "重命名分类",
                f"是否将分类“{old_name}”更名为“{new_name}”？",
            )
            if not confirmed:
                self._cancel_category_rename()
                return "break"

            self._cancel_category_rename()
            self._apply_category_rename(old_name, new_name)
            return "break"
        finally:
            self._category_rename_committing = False

    def _apply_category_rename(self, old_name, new_name):
        history_before = (
            self._capture_global_snapshot()
            if hasattr(self, "_capture_global_snapshot") else None
        )
        self.categories = [
            new_name if category == old_name else category
            for category in self.categories
        ]
        for row in getattr(self, "rows", []):
            if row.get("category") == old_name:
                row["category"] = new_name

        category_field = self._csv_category_field()
        if category_field:
            for row in getattr(self, "csv_model_rows", []):
                value = str(row.get(category_field, "")).strip() or "未分类"
                if value == old_name:
                    row[category_field] = new_name

        if old_name in self.category_side_states:
            self.category_side_states[new_name] = self.category_side_states.pop(old_name)
        if old_name in self.category_colors:
            self.category_colors[new_name] = self.category_colors.pop(old_name)
        if old_name in self.hidden_categories:
            self.hidden_categories.discard(old_name)
            self.hidden_categories.add(new_name)
        if old_name in self.selected_categories:
            self.selected_categories.discard(old_name)
            self.selected_categories.add(new_name)
        if old_name in getattr(self, "category_vars", {}):
            self.category_vars[new_name] = self.category_vars.pop(old_name)

        self.category_search_matches = [
            new_name if category == old_name else category
            for category in getattr(self, "category_search_matches", [])
        ]
        if getattr(self, "category_search_focus_category", None) == old_name:
            self.category_search_focus_category = new_name

        for rule in getattr(self, "event_migration_rules", []):
            if rule.get("source") == old_name:
                rule["source"] = new_name
            if rule.get("target") == old_name:
                rule["target"] = new_name
            remembered = rule.get("selections_by_source", {})
            if old_name in remembered:
                remembered[new_name] = remembered.pop(old_name)

        if hasattr(self, "_render_csv_grid"):
            self._render_csv_grid()
        self.render_legend()
        if hasattr(self, "event_migration_body"):
            self._render_event_migration_plan()
        self.render()
        self.has_unexported_csv_edits = True
        self.status_var.set(f"已将分类“{old_name}”更名为“{new_name}”")
        if hasattr(self, "_commit_global_history"):
            self._commit_global_history(
                history_before,
                f"重命名分类：{old_name} → {new_name}",
                clear_csv_local_history=True,
            )
