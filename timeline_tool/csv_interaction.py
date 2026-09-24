"""CSV 局部历史、滚动、选择与悬浮交互。"""

import copy
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .config import PALETTE
from .csv_document import (
    CsvFormat,
    decode_csv_bytes,
    parse_csv_document,
    parse_flexible_date,
    serialize_csv_model,
    validate_date_style,
)
from .utils import resource_path


class CSVInteractionMixin:
    def _widget_is_inside_csv_panel(self, widget):
        panel = getattr(self, "csv_panel", None)
        if panel is None or widget is None:
            return False
        try:
            current = widget
            while current is not None:
                if current is panel:
                    return True
                parent_name = current.winfo_parent()
                if not parent_name:
                    break
                current = current.nametowidget(parent_name)
        except (tk.TclError, KeyError, AttributeError):
            return False
        return False

    def update_undo_context_from_event(self, event=None):
        """只按最近一次左键点击决定 Ctrl+Z / Ctrl+Y 属于哪个区域。

        焦点变化本身不改变撤销上下文：例如点击 CSV 区外以后，即使某个
        Entry 因程序逻辑重新获得键盘焦点，也仍按“最近一次点击在 CSV 区外”
        处理。这样这里的“聚焦”与界面其它地方的“点一下外部退出编辑”一致。
        """
        if event is None or getattr(event, "num", None) != 1:
            return None
        widget = getattr(event, "widget", None)
        self.undo_context = "csv" if self._widget_is_inside_csv_panel(widget) else "global"
        return None

    def handle_contextual_undo_shortcut(self, event=None):
        if getattr(self, "undo_context", "global") == "csv":
            return self.undo_csv_local_edit(event)
        return self.undo_global_action()

    def handle_contextual_redo_shortcut(self, event=None):
        if getattr(self, "undo_context", "global") == "csv":
            return self.redo_csv_local_edit(event)
        return self.redo_global_action()

    @staticmethod
    def _snapshot_rows_by_uid(rows):
        return {
            int(row.get("__csv_uid__", index + 1) or index + 1): row
            for index, row in enumerate(rows)
        }

    def _describe_csv_local_delta(self, before, after):
        """描述一段 CSV 草稿变化，供信息记录和撤销/重做使用。"""
        before_fields, after_fields = list(before[0]), list(after[0])
        before_rows, after_rows = list(before[1]), list(after[1])
        before_pending_rows = set(before[2]) if len(before) > 2 else set()
        after_pending_rows = set(after[2]) if len(after) > 2 else set()
        before_pending_fields = set(before[3]) if len(before) > 3 else set()
        after_pending_fields = set(after[3]) if len(after) > 3 else set()
        parts = []

        added_fields = [f for f in after_fields if f not in before_fields]
        removed_fields = [f for f in before_fields if f not in after_fields]
        if added_fields:
            parts.append("新增字段：" + "、".join(added_fields))
        if removed_fields:
            parts.append("删除字段：" + "、".join(removed_fields))

        bmap = self._snapshot_rows_by_uid(before_rows)
        amap = self._snapshot_rows_by_uid(after_rows)
        added = [uid for uid in amap if uid not in bmap]
        removed = [uid for uid in bmap if uid not in amap]
        if added:
            parts.append(f"新增 {len(added)} 行事件")
        if removed:
            parts.append(f"删除 {len(removed)} 行事件")

        common = [uid for uid in amap if uid in bmap]
        changed = []
        changed_fields = set()
        fields = list(dict.fromkeys(before_fields + after_fields))
        for uid in common:
            for field in fields:
                if str(bmap[uid].get(field, "")) != str(amap[uid].get(field, "")):
                    changed.append((uid, field))
                    changed_fields.add(field)
        if changed:
            field_text = "、".join(f for f in fields if f in changed_fields)
            parts.append(
                f"修改 {len(changed)} 个单元格"
                + (f"（字段：{field_text}）" if field_text else "")
            )

        border = [int(r.get("__csv_uid__", i + 1) or i + 1) for i, r in enumerate(before_rows)]
        aorder = [int(r.get("__csv_uid__", i + 1) or i + 1) for i, r in enumerate(after_rows)]
        if len(border) == len(aorder) and set(border) == set(aorder) and border != aorder:
            parts.append("调整事件行顺序")

        newly_pending_rows = after_pending_rows - before_pending_rows
        restored_rows = before_pending_rows - after_pending_rows
        newly_pending_fields = after_pending_fields - before_pending_fields
        restored_fields = before_pending_fields - after_pending_fields
        if newly_pending_rows:
            parts.append(f"预删除 {len(newly_pending_rows)} 行")
        if restored_rows:
            parts.append(f"取消 {len(restored_rows)} 行预删除")
        if newly_pending_fields:
            parts.append("预删除字段：" + "、".join(sorted(newly_pending_fields)))
        if restored_fields:
            parts.append("取消字段预删除：" + "、".join(sorted(restored_fields)))

        return "；".join(parts) or "CSV 草稿状态发生变化"

    def _mark_csv_committed_state(self):
        """把当前 CSV 表格标记为最近一次已经正式生效的版本。"""
        self.csv_committed_snapshot = copy.deepcopy(self._csv_snapshot())

    def _csv_has_unapplied_changes(self):
        """判断当前 CSV 表格是否偏离最近一次正式生效的版本。"""
        committed = getattr(self, "csv_committed_snapshot", None)
        if committed is None:
            return bool(
                getattr(self, "csv_local_undo_stack", [])
                or getattr(self, "csv_local_redo_stack", [])
            )
        try:
            return self._csv_snapshot() != committed
        except Exception:
            return True

    def _focus_is_text_input(self):
        """普通输入框保留自己的键盘行为，不截获为 CSV Ctrl+Z/Y。"""
        try:
            focused = self.focus_get()
        except (tk.TclError, KeyError):
            return False
        if focused is None:
            return False
        if focused is getattr(self, "csv_cell_editor", None):
            return False
        return isinstance(focused, (tk.Entry, ttk.Entry, ttk.Combobox, tk.Text))

    def handle_csv_local_undo_shortcut(self, event=None):
        """应用级 Ctrl+Z：只负责 CSV 未应用草稿，不下沉到全局撤销。"""
        if self._focus_is_text_input():
            return None
        return self.undo_csv_local_edit(event)

    def handle_csv_local_redo_shortcut(self, event=None):
        """应用级 Ctrl+Y：只负责 CSV 未应用草稿，不下沉到全局重做。"""
        if self._focus_is_text_input():
            return None
        return self.redo_csv_local_edit(event)

    def _csv_snapshot(self):
        self._ensure_csv_selection_state()
        return (
            list(self.csv_fieldnames),
            [dict(row) for row in self.csv_model_rows],
            set(self.csv_pending_delete_row_uids),
            set(self.csv_pending_delete_fields),
        )

    def _restore_csv_snapshot(self, snapshot):
        self.csv_local_history_suspended = True
        try:
            self.csv_fieldnames = list(snapshot[0])
            self.csv_model_rows = [dict(row) for row in snapshot[1]]
            self.csv_pending_delete_row_uids = set(snapshot[2]) if len(snapshot) > 2 else set()
            self.csv_pending_delete_fields = set(snapshot[3]) if len(snapshot) > 3 else set()
            self.csv_selected_row_uids = set()
            self.csv_selected_fields = set()
            self.csv_next_row_uid = max(
                [int(row.get("__csv_uid__", 0) or 0) for row in self.csv_model_rows],
                default=0,
            ) + 1
            self._render_csv_grid()
            self._reset_csv_search_state()
        finally:
            self.csv_local_history_suspended = False

    def _push_csv_local_history(self):
        if getattr(self, "csv_local_history_suspended", False):
            return
        snapshot = self._csv_snapshot()
        if self.csv_local_undo_stack and self.csv_local_undo_stack[-1] == snapshot:
            return
        self.csv_local_undo_stack.append(snapshot)
        if len(self.csv_local_undo_stack) > 100:
            self.csv_local_undo_stack.pop(0)
        self.csv_local_redo_stack.clear()

    def undo_csv_local_edit(self, _event=None):
        if getattr(self, "csv_cell_editor", None) is not None:
            editor = self.csv_cell_editor
            original = getattr(editor, "_csv_original_value", editor.get())
            current_value = editor.get()
            if current_value != original:
                editor.delete(0, tk.END)
                editor.insert(0, original)
                editor.select_range(0, tk.END)
                self.status_var.set("已撤销 CSV 当前单元格尚未提交的编辑")
            else:
                try:
                    self.bell()
                except tk.TclError:
                    pass
                self.status_var.set("CSV 草稿：当前单元格没有可撤销的编辑")
            return "break"
        if not self.csv_local_undo_stack:
            try:
                self.bell()
            except tk.TclError:
                pass
            self.status_var.set("CSV 草稿：没有可撤销的未应用修改")
            return "break"
        current = self._csv_snapshot()
        snapshot = self.csv_local_undo_stack.pop()
        detail = self._describe_csv_local_delta(snapshot, current)
        self.csv_local_redo_stack.append(current)
        self._restore_csv_snapshot(snapshot)
        self.status_var.set(f"已撤销 CSV 草稿操作：{detail}")
        return "break"

    def redo_csv_local_edit(self, _event=None):
        if getattr(self, "csv_cell_editor", None) is not None:
            try:
                self.bell()
            except tk.TclError:
                pass
            self.status_var.set("CSV 草稿：当前单元格编辑中没有可重做步骤")
            return "break"
        if not self.csv_local_redo_stack:
            try:
                self.bell()
            except tk.TclError:
                pass
            self.status_var.set("CSV 草稿：没有可重做的未应用修改")
            return "break"
        current = self._csv_snapshot()
        snapshot = self.csv_local_redo_stack.pop()
        detail = self._describe_csv_local_delta(current, snapshot)
        self.csv_local_undo_stack.append(current)
        self._restore_csv_snapshot(snapshot)
        self.status_var.set(f"已重做 CSV 草稿操作：{detail}")
        return "break"

    def on_csv_editor_yview_changed(self, first, last):
        """数据区纵向滚动时同步固定行号列。"""
        self.csv_editor_scrollbar.set(first, last)
        if hasattr(self, "csv_row_numbers"):
            self.csv_row_numbers.yview_moveto(first)
        if getattr(self, "csv_validation_errors", []):
            self.after_idle(self._refresh_csv_validation_overlays)
        if getattr(self, "csv_pending_delete_fields", set()):
            self.after_idle(self._refresh_csv_pending_delete_overlays)
        if hasattr(self, "_refresh_csv_column_selection_overlays"):
            self.after_idle(self._refresh_csv_column_selection_overlays)

    def on_csv_row_numbers_yview_changed(self, first, last):
        """行号列自身滚动时反向同步数据区。"""
        if hasattr(self, "csv_editor"):
            current = self.csv_editor.yview()
            if current and abs(current[0] - float(first)) > 1e-9:
                self.csv_editor.yview_moveto(first)

    def on_csv_editor_xview_changed(self, first, last):
        self.csv_editor_hscrollbar.set(first, last)
        if getattr(self, "csv_pending_delete_fields", set()):
            self.after_idle(self._refresh_csv_pending_delete_overlays)
        if hasattr(self, "_refresh_csv_column_selection_overlays"):
            self.after_idle(self._refresh_csv_column_selection_overlays)

    def on_csv_row_number_click(self, event):
        self._ensure_csv_selection_state()
        region = self.csv_row_numbers.identify_region(event.x, event.y)
        if region == "heading":
            active_uids = {
                self._csv_row_uid(row) for row in self.csv_model_rows
                if self._csv_row_uid(row) not in self.csv_pending_delete_row_uids
            }
            if active_uids and active_uids.issubset(self.csv_selected_row_uids):
                self.csv_selected_row_uids.difference_update(active_uids)
            else:
                self.csv_selected_row_uids.update(active_uids)
            self._refresh_csv_selection_visuals()
            self._hide_csv_hover_tooltip()
            return "break"

        row_id = self.csv_row_numbers.identify_row(event.y)
        if row_id:
            row_index = int(row_id[3:])
            if 0 <= row_index < len(self.csv_model_rows):
                uid = self._csv_row_uid(self.csv_model_rows[row_index])
                if uid in self.csv_pending_delete_row_uids:
                    self._push_csv_local_history()
                    self.csv_pending_delete_row_uids.discard(uid)
                    self.csv_selected_row_uids.discard(uid)
                    self._refresh_csv_grid_after_model_change()
                    self.status_var.set(f"已取消第 {row_index + 1} 行的预删除状态")
                else:
                    if uid in self.csv_selected_row_uids:
                        self.csv_selected_row_uids.discard(uid)
                    else:
                        self.csv_selected_row_uids.add(uid)
                    self._refresh_csv_selection_visuals()
        self._hide_csv_hover_tooltip()
        return "break"

    def on_csv_grid_click(self, event):
        self._ensure_csv_selection_state()
        region = self.csv_editor.identify_region(event.x, event.y)
        column_id = self.csv_editor.identify_column(event.x)
        if region == "heading" and column_id and column_id != "#0":
            column_index = int(column_id[1:]) - 1
            if 0 <= column_index < len(self.csv_fieldnames):
                field = self.csv_fieldnames[column_index]
                if field in self.csv_pending_delete_fields:
                    self._push_csv_local_history()
                    self.csv_pending_delete_fields.discard(field)
                    self.csv_selected_fields.discard(field)
                    self._refresh_csv_grid_after_model_change()
                    self.status_var.set(f"已取消字段“{field}”的预删除状态")
                else:
                    if field in self.csv_selected_fields:
                        self.csv_selected_fields.discard(field)
                    else:
                        self.csv_selected_fields.add(field)
                    self._refresh_csv_selection_visuals()
            self._hide_csv_hover_tooltip()
            return "break"

        if column_id and column_id != "#0":
            self.csv_active_column = int(column_id[1:]) - 1
        self._hide_csv_hover_tooltip()

    def _reposition_csv_cell_editor(self):
        editor = getattr(self, "csv_cell_editor", None)
        target = getattr(self, "csv_cell_edit_target", None)
        if editor is None or target is None:
            return
        row_id, column_index = target
        bbox = self.csv_editor.bbox(row_id, f"#{column_index + 1}")
        if not bbox:
            editor.place_forget()
            return
        x, y, width, height = bbox
        editor.place(x=x, y=y, width=width, height=height)
        editor.lift()
        try:
            editor.focus_set()
        except tk.TclError:
            pass

    def _after_csv_grid_scroll(self):
        self.csv_editor.update_idletasks()
        self._reposition_csv_cell_editor()
        if getattr(self, "csv_validation_errors", []):
            self._refresh_csv_validation_overlays()
        self._refresh_csv_search_overlay()
        self._refresh_csv_pending_delete_overlays()
        if hasattr(self, "_refresh_csv_column_selection_overlays"):
            self._refresh_csv_column_selection_overlays()
        self._hide_csv_hover_tooltip()
        if getattr(self, "csv_cell_editor", None) is not None:
            self.after_idle(self._reposition_csv_cell_editor)
            self.after(25, self._reposition_csv_cell_editor)
        if getattr(self, "csv_validation_errors", []):
            self.after_idle(self._refresh_csv_validation_overlays)

    def on_csv_vertical_scrollbar(self, *args):
        self.csv_editor.yview(*args)
        if hasattr(self, "csv_row_numbers"):
            self.csv_row_numbers.yview(*args)
        self.after_idle(self._after_csv_grid_scroll)

    def on_csv_horizontal_scrollbar(self, *args):
        self.csv_editor.xview(*args)
        self.after_idle(self._after_csv_grid_scroll)

    @staticmethod
    def _csv_wheel_steps(event):
        if getattr(event, "num", None) == 4:
            return -1
        if getattr(event, "num", None) == 5:
            return 1
        delta = getattr(event, "delta", 0)
        if not delta:
            return 0
        return -1 if delta > 0 else 1

    def on_csv_grid_mousewheel(self, event):
        # Shift 交给横向滚动处理，避免与普通纵向滚动重复。
        if getattr(event, "state", 0) & 0x0001:
            return self.on_csv_grid_shift_mousewheel(event)
        steps = self._csv_wheel_steps(event)
        if steps:
            self.csv_editor.yview_scroll(steps * 3, "units")
            self.after_idle(self._after_csv_grid_scroll)
        return "break"

    def on_csv_grid_shift_mousewheel(self, event):
        steps = self._csv_wheel_steps(event)
        if steps:
            # Treeview 的横向 unit 很细；放大步长以接近文件表格的手感。
            self.csv_editor.xview_scroll(steps * 8, "units")
            self.after_idle(self._after_csv_grid_scroll)
        return "break"

    def _hide_csv_search_overlay(self):
        overlay = getattr(self, "csv_search_overlay", None)
        if overlay is not None:
            try:
                overlay.destroy()
            except tk.TclError:
                pass
        self.csv_search_overlay = None

    def _refresh_csv_search_overlay(self):
        self._hide_csv_search_overlay()
        if not self.csv_text_search_matches or self.csv_text_search_index < 0:
            return
        row_id, column_index, _start, _end = self.csv_text_search_matches[
            self.csv_text_search_index
        ]
        # 表头现在位于固定 heading 中，不再作为滚动数据行；表头匹配只定位列。
        if row_id == "header":
            return
        bbox = self.csv_editor.bbox(row_id, f"#{column_index + 1}")
        if not bbox:
            return
        x, y, width, height = bbox
        field = self.csv_fieldnames[column_index]
        row_index = int(row_id[3:])
        value = str(self.csv_model_rows[row_index].get(field, ""))
        overlay = tk.Label(
            self.csv_editor,
            text=value,
            anchor="w",
            padx=4,
            bg="#0b79d0",
            fg="white",
            font=("Consolas", 10),
            bd=0,
        )
        overlay.place(x=x, y=y, width=width, height=height)
        overlay.bind("<Double-1>", lambda _e: self._begin_csv_cell_edit(row_id, f"#{column_index + 1}"))
        self.csv_search_overlay = overlay

    def _hide_csv_hover_tooltip(self):
        tip = getattr(self, "csv_hover_tooltip", None)
        if tip is not None:
            try:
                tip.destroy()
            except tk.TclError:
                pass
        self.csv_hover_tooltip = None
        self.csv_hover_target = None

    def on_csv_grid_leave(self, _event=None):
        self._hide_csv_hover_tooltip()

    def on_csv_grid_motion(self, event):
        row_id = self.csv_editor.identify_row(event.y)
        column_id = self.csv_editor.identify_column(event.x)
        if not row_id or column_id == "#0":
            self._hide_csv_hover_tooltip()
            return
        column_index = int(column_id[1:]) - 1
        if not (0 <= column_index < len(self.csv_fieldnames)):
            self._hide_csv_hover_tooltip()
            return
        target = (row_id, column_index)
        if target == getattr(self, "csv_hover_target", None):
            return
        self._hide_csv_hover_tooltip()
        if row_id == "header":
            return
        row_index = int(row_id[3:])
        field = self.csv_fieldnames[column_index]
        value = str(self.csv_model_rows[row_index].get(field, ""))
        if not value:
            return
        bbox = self.csv_editor.bbox(row_id, column_id)
        if not bbox:
            return
        import tkinter.font as tkfont
        font = tkfont.Font(font=("Consolas", 10))
        if font.measure(value) <= max(0, bbox[2] - 10):
            return
        self.csv_hover_target = target
        tip = tk.Toplevel(self)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        label = tk.Label(
            tip,
            text=value,
            justify="left",
            anchor="w",
            bg="#fffbe8",
            fg="#1f2937",
            relief="solid",
            bd=1,
            padx=6,
            pady=4,
            wraplength=650,
            font=("Microsoft YaHei UI", 9),
        )
        label.pack()
        tip.update_idletasks()
        x = self.csv_editor.winfo_rootx() + event.x + 14
        y = self.csv_editor.winfo_rooty() + event.y + 18
        tip.geometry(f"+{x}+{y}")
        self.csv_hover_tooltip = tip
