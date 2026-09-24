"""CSV 表格模型、单元格编辑与 category/side 语义。"""

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


class CSVModelMixin:
    def load_sample(self):
        sample_path = resource_path("assets/data/samples/test-data.csv")

        try:
            data = sample_path.read_bytes()
            csv_text, encoding = decode_csv_bytes(data)
            document = parse_csv_document(csv_text, encoding=encoding)
            self.current_csv_name = sample_path.name
            self.current_csv_directory = Path.cwd()
            self.load_rows(
                document.rows,
                "已载入示例数据",
                csv_text=document.editor_text,
                csv_format=document.format,
                csv_fieldnames=document.fieldnames,
            )
            self.has_unexported_csv_edits = False
            if hasattr(self, "reset_global_history"):
                self.reset_global_history()
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))

    def import_csv(self):
        path = filedialog.askopenfilename(
            title="选择 CSV 文件",
            filetypes=[("CSV/TSV 文件", "*.csv *.tsv"), ("所有文件", "*.*")],
        )
        if not path:
            return

        try:
            data = Path(path).read_bytes()
            csv_text, encoding = decode_csv_bytes(data)
            document = parse_csv_document(csv_text, encoding=encoding)
            selected_path = Path(path)
            self.current_csv_name = selected_path.name
            self.current_csv_directory = selected_path.parent
            self.load_rows(
                document.rows,
                f"已导入 {selected_path.name}",
                csv_text=document.editor_text,
                csv_format=document.format,
                csv_fieldnames=document.fieldnames,
            )
            self.has_unexported_csv_edits = False
            if hasattr(self, "reset_global_history"):
                self.reset_global_history()
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

    def parse_csv_text(self, csv_text):
        current_encoding = getattr(self, "current_csv_format", CsvFormat()).encoding
        return parse_csv_document(csv_text, encoding=current_encoding)

    @staticmethod
    def _spreadsheet_column_name(index):
        name = ""
        value = index + 1
        while value:
            value, remainder = divmod(value - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def set_csv_editor_model(self, fieldnames, raw_rows):
        """把解析结果写入 CSV 区唯一的内存表格模型。"""
        self.csv_fieldnames = [str(name) for name in fieldnames]
        self.csv_model_rows = []

        for source_row in raw_rows:
            row = {}
            for field in self.csv_fieldnames:
                value = source_row.get(field, "")
                row[field] = "" if value is None else str(value)
            self.csv_model_rows.append(row)

        self.csv_local_undo_stack = []
        self.csv_local_redo_stack = []
        self.csv_selected_row_uids = set()
        self.csv_selected_fields = set()
        self.csv_pending_delete_row_uids = set()
        self.csv_pending_delete_fields = set()
        self.csv_pending_delete_overlays = []
        self.csv_column_selection_overlays = []
        self.csv_next_row_uid = 1
        for row in self.csv_model_rows:
            row["__csv_uid__"] = self.csv_next_row_uid
            self.csv_next_row_uid += 1
        self._detect_csv_side_display_mode()
        self._clear_csv_validation_state()
        self._install_csv_validation_guard()
        self._render_csv_grid()
        self._reset_csv_search_state()
        if hasattr(self, "_mark_csv_committed_state"):
            self._mark_csv_committed_state()

    def _ensure_csv_selection_state(self):
        if not hasattr(self, "csv_selected_row_uids"):
            self.csv_selected_row_uids = set()
        if not hasattr(self, "csv_selected_fields"):
            self.csv_selected_fields = set()
        if not hasattr(self, "csv_pending_delete_row_uids"):
            self.csv_pending_delete_row_uids = set()
        if not hasattr(self, "csv_pending_delete_fields"):
            self.csv_pending_delete_fields = set()
        if not hasattr(self, "csv_pending_delete_overlays"):
            self.csv_pending_delete_overlays = []
        if not hasattr(self, "csv_column_selection_overlays"):
            self.csv_column_selection_overlays = []
        if not hasattr(self, "csv_next_row_uid"):
            uids = [int(row.get("__csv_uid__", 0) or 0) for row in self.csv_model_rows]
            self.csv_next_row_uid = max(uids, default=0) + 1
        for row in self.csv_model_rows:
            if "__csv_uid__" not in row:
                row["__csv_uid__"] = self.csv_next_row_uid
                self.csv_next_row_uid += 1

    def _csv_row_uid(self, row):
        self._ensure_csv_selection_state()
        if "__csv_uid__" not in row:
            row["__csv_uid__"] = self.csv_next_row_uid
            self.csv_next_row_uid += 1
        return row["__csv_uid__"]

    @staticmethod
    def _is_required_csv_field(field):
        return str(field or "").strip().casefold() in {
            "date", "title", "side", "category", "group"
        }

    def _csv_heading_text(self, column_index, field):
        """表头只显示字段本身与必要的关键字段星号。

        选择和预删除都用整行 / 整列的背景状态表达，不再往表头塞三角、叉号
        等额外符号，避免同一状态出现重复而零碎的视觉提示。
        """
        required_mark = "*" if self._is_required_csv_field(field) else ""
        return (
            f"{self._spreadsheet_column_name(column_index)}  "
            f"{field}{required_mark}"
        )

    def _clear_csv_column_selection_overlays(self):
        for overlay in getattr(self, "csv_column_selection_overlays", []):
            try:
                overlay.destroy()
            except tk.TclError:
                pass
        self.csv_column_selection_overlays = []

    def _selected_column_overlay_click(self, row_id, column_index):
        self.csv_active_column = column_index
        try:
            self.csv_editor.focus(row_id)
            self.csv_editor.selection_set(row_id)
        except tk.TclError:
            pass
        self._hide_csv_hover_tooltip()
        return "break"

    def _selected_column_overlay_double_click(self, row_id, column_index):
        self._selected_column_overlay_click(row_id, column_index)
        self._begin_csv_cell_edit(row_id, f"#{column_index + 1}")
        return "break"

    def _selected_column_header_overlay_click(self, field):
        self.csv_selected_fields.discard(field)
        self._refresh_csv_selection_visuals()
        return "break"

    def _refresh_csv_column_selection_overlays(self):
        """用淡蓝覆盖层表现整列选择；覆盖层仍转发单元格编辑和滚轮操作。"""
        self._clear_csv_column_selection_overlays()
        self._ensure_csv_selection_state()
        selected_fields = [
            field for field in self.csv_fieldnames
            if field in self.csv_selected_fields
            and field not in self.csv_pending_delete_fields
        ]
        if not selected_fields:
            return

        row_ids = list(self.csv_editor.get_children(""))
        if not row_ids:
            return

        for field in selected_fields:
            try:
                column_index = self.csv_fieldnames.index(field)
            except ValueError:
                continue
            column_ref = f"#{column_index + 1}"
            first_bbox = None
            for row_id in row_ids:
                bbox = self.csv_editor.bbox(row_id, column_ref)
                if bbox:
                    first_bbox = bbox
                    break
            if first_bbox:
                x, y, width, _height = first_bbox
                if y > 0 and width > 0:
                    header = tk.Label(
                        self.csv_editor,
                        text=self._csv_heading_text(column_index, field),
                        bg="#dbeafe", fg="#263247",
                        font=("Consolas", 9, "bold"),
                        bd=0, anchor="center", cursor="hand2",
                    )
                    header.place(x=x, y=0, width=width, height=y)
                    header.bind(
                        "<Button-1>",
                        lambda _e, f=field: self._selected_column_header_overlay_click(f),
                    )
                    self.csv_column_selection_overlays.append(header)

            for row_id in row_ids:
                bbox = self.csv_editor.bbox(row_id, column_ref)
                if not bbox:
                    continue
                x, y, width, height = bbox
                value = self.csv_editor.set(row_id, f"c{column_index}")
                cell = tk.Label(
                    self.csv_editor, text=value, anchor="w", padx=4,
                    bg="#dbeafe", fg="#263247", font=("Consolas", 10),
                    bd=0, cursor="arrow",
                )
                cell.place(x=x, y=y, width=width, height=height)
                cell.bind(
                    "<Button-1>",
                    lambda _e, r=row_id, c=column_index:
                        self._selected_column_overlay_click(r, c),
                )
                cell.bind(
                    "<Double-1>",
                    lambda _e, r=row_id, c=column_index:
                        self._selected_column_overlay_double_click(r, c),
                )
                cell.bind("<MouseWheel>", self.on_csv_grid_mousewheel)
                cell.bind("<Shift-MouseWheel>", self.on_csv_grid_shift_mousewheel)
                self.csv_column_selection_overlays.append(cell)

    def _render_csv_grid(self):
        self._ensure_csv_selection_state()
        self._close_csv_cell_editor(commit=True)
        self._hide_csv_search_overlay()
        self._clear_csv_pending_delete_overlays()
        self._clear_csv_column_selection_overlays()

        for item in self.csv_editor.get_children():
            self.csv_editor.delete(item)
        if hasattr(self, "csv_row_numbers"):
            for item in self.csv_row_numbers.get_children():
                self.csv_row_numbers.delete(item)

        self.csv_editor.tag_configure(
            "pending_delete_row", background="#eef0f2", foreground="#9aa2ad"
        )
        if hasattr(self, "csv_row_numbers"):
            self.csv_row_numbers.tag_configure(
                "pending_delete_row", background="#e6e8eb", foreground="#9aa2ad"
            )

        columns = [f"c{index}" for index in range(len(self.csv_fieldnames))]
        self.csv_editor.configure(columns=columns)

        for column_index, column_id in enumerate(columns):
            field = self.csv_fieldnames[column_index]
            self.csv_editor.heading(
                column_id,
                text=self._csv_heading_text(column_index, field),
                anchor="center",
            )

            max_chars = len(field)
            for row in self.csv_model_rows:
                max_chars = max(max_chars, len(str(row.get(field, ""))))

            self.csv_editor.column(
                column_id,
                width=min(320, max(90, max_chars * 9 + 20)),
                minwidth=70,
                stretch=False,
                anchor="w",
            )

        selected_row_ids = []
        for model_index, row in enumerate(self.csv_model_rows):
            row_id = f"row{model_index}"
            uid = self._csv_row_uid(row)
            tags = ("pending_delete_row",) if uid in self.csv_pending_delete_row_uids else ()
            if hasattr(self, "csv_row_numbers"):
                self.csv_row_numbers.insert(
                    "", "end", iid=row_id, values=(str(model_index + 1),), tags=tags
                )
            self.csv_editor.insert(
                "", "end", iid=row_id,
                values=[row.get(field, "") for field in self.csv_fieldnames],
                tags=tags,
            )
            if uid in self.csv_selected_row_uids and uid not in self.csv_pending_delete_row_uids:
                selected_row_ids.append(row_id)

        if selected_row_ids:
            self.csv_editor.selection_set(tuple(selected_row_ids))
            if hasattr(self, "csv_row_numbers"):
                self.csv_row_numbers.selection_set(tuple(selected_row_ids))

        self.after_idle(self._refresh_csv_column_selection_overlays)
        self.after_idle(self._refresh_csv_pending_delete_overlays)

    def _clear_csv_pending_delete_overlays(self):
        for overlay in getattr(self, "csv_pending_delete_overlays", []):
            try:
                overlay.destroy()
            except tk.TclError:
                pass
        self.csv_pending_delete_overlays = []

    def _refresh_csv_pending_delete_overlays(self):
        self._clear_csv_pending_delete_overlays()
        self._ensure_csv_selection_state()
        if not self.csv_pending_delete_fields:
            return

        for column_index, field in enumerate(self.csv_fieldnames):
            if field not in self.csv_pending_delete_fields:
                continue
            for row_index, row in enumerate(self.csv_model_rows):
                uid = self._csv_row_uid(row)
                if uid in self.csv_pending_delete_row_uids:
                    continue
                row_id = f"row{row_index}"
                bbox = self.csv_editor.bbox(row_id, f"#{column_index + 1}")
                if not bbox:
                    continue
                x, y, width, height = bbox
                overlay = tk.Label(
                    self.csv_editor, text=str(row.get(field, "")), anchor="w", padx=4,
                    bg="#eef0f2", fg="#9aa2ad", font=("Consolas", 10), bd=0,
                    cursor="arrow",
                )
                overlay.place(x=x, y=y, width=width, height=height)
                overlay.bind("<Button-1>", lambda _event: "break")
                overlay.bind("<Double-1>", lambda _event: "break")
                self.csv_pending_delete_overlays.append(overlay)

    def _refresh_csv_selection_visuals(self):
        self._ensure_csv_selection_state()
        row_ids = []
        for index, row in enumerate(self.csv_model_rows):
            uid = self._csv_row_uid(row)
            if uid in self.csv_selected_row_uids and uid not in self.csv_pending_delete_row_uids:
                row_ids.append(f"row{index}")
        try:
            self.csv_editor.selection_set(tuple(row_ids)) if row_ids else self.csv_editor.selection_remove(self.csv_editor.selection())
            if hasattr(self, "csv_row_numbers"):
                self.csv_row_numbers.selection_set(tuple(row_ids)) if row_ids else self.csv_row_numbers.selection_remove(self.csv_row_numbers.selection())
        except tk.TclError:
            pass
        for column_index, field in enumerate(self.csv_fieldnames):
            try:
                self.csv_editor.heading(
                    f"c{column_index}",
                    text=self._csv_heading_text(column_index, field),
                    anchor="center",
                )
            except tk.TclError:
                pass
        self.after_idle(self._refresh_csv_column_selection_overlays)
        if getattr(self, "csv_pending_delete_fields", set()):
            self.after_idle(self._refresh_csv_pending_delete_overlays)

    def _reset_csv_search_state(self):
        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self.csv_text_search_query = ""
        if hasattr(self, "csv_text_search_var"):
            self.csv_text_search_var.set("")
            self.csv_text_replace_var.set("")
            self.update_csv_text_search_counter()

    def on_csv_grid_double_click(self, event):
        row_id = self.csv_editor.identify_row(event.y)
        column_id = self.csv_editor.identify_column(event.x)
        if not row_id or column_id == "#0":
            return
        self._ensure_csv_selection_state()
        row_index = int(row_id[3:])
        column_index = int(column_id[1:]) - 1
        if self._csv_row_uid(self.csv_model_rows[row_index]) in self.csv_pending_delete_row_uids:
            return "break"
        if self.csv_fieldnames[column_index] in self.csv_pending_delete_fields:
            return "break"
        self._begin_csv_cell_edit(row_id, column_id)

    def on_csv_grid_keyboard_edit(self, _event=None):
        row_id = self.csv_editor.focus()
        if not row_id:
            return "break"

        column_index = getattr(self, "csv_active_column", 0)
        if column_index >= len(self.csv_fieldnames):
            column_index = 0

        self._begin_csv_cell_edit(row_id, f"#{column_index + 1}")
        return "break"

    def _begin_csv_cell_edit(self, row_id, column_id):
        self._close_csv_cell_editor(commit=True)
        self._ensure_csv_selection_state()
        if row_id != "header":
            row_index = int(row_id[3:])
            column_index = int(column_id[1:]) - 1
            if self._csv_row_uid(self.csv_model_rows[row_index]) in self.csv_pending_delete_row_uids:
                return
            if 0 <= column_index < len(self.csv_fieldnames) and self.csv_fieldnames[column_index] in self.csv_pending_delete_fields:
                return

        if row_id != "header":
            self.csv_editor.selection_set(row_id)
            self.csv_editor.focus(row_id)

        bbox = self.csv_editor.bbox(row_id, column_id)
        if not bbox:
            return

        column_index = int(column_id[1:]) - 1
        self.csv_active_column = column_index

        if row_id == "header":
            value = self.csv_fieldnames[column_index]
        else:
            row_index = int(row_id[3:])
            field = self.csv_fieldnames[column_index]
            value = self.csv_model_rows[row_index].get(field, "")

        x, y, width, height = bbox

        field_name = self.csv_fieldnames[column_index].strip().casefold()
        is_category_field = field_name in {"category", "group"}
        is_side_field = field_name == "side"

        if is_side_field and row_id != "header":
            editor = ttk.Combobox(
                self.csv_editor,
                values=self._csv_side_choices(),
                state="readonly",
                style="CsvCell.TCombobox",
                font=("Consolas", 10),
            )
            editor.set(value if value else self._default_side_display_value())
            editor.bind("<Button-1>", self._on_csv_combobox_button_press, add="+")
        elif is_category_field and row_id != "header":
            editor = ttk.Combobox(
                self.csv_editor,
                values=self._csv_category_choices(),
                state="normal",
                style="CsvCell.TCombobox",
                font=("Consolas", 10),
            )
            editor.set(value)
            editor.bind("<<ComboboxSelected>>", self._on_csv_category_selected, add="+")
            editor.bind("<Button-1>", self._on_csv_combobox_button_press, add="+")
        else:
            editor = tk.Entry(
                self.csv_editor,
                font=("Consolas", 10),
                relief="solid",
                bd=1,
            )
            editor.insert(0, value)
        editor._csv_original_value = value
        if isinstance(editor, tk.Entry):
            editor.select_range(0, tk.END)
        editor.place(x=x, y=y, width=width, height=height)
        editor.focus_set()

        self.csv_cell_editor = editor
        self.csv_cell_edit_target = (row_id, column_index)
        self.csv_cell_edit_original_value = value

        if row_id != "header" and getattr(self, "csv_validation_errors", []):
            self._refresh_csv_validation_overlays()

        editor.bind("<Return>", self._on_csv_editor_return)
        editor.bind(
            "<Escape>",
            lambda _event: self._close_csv_cell_editor(commit=False),
        )
        editor.bind("<FocusOut>", self._on_csv_cell_editor_focus_out)
        editor.bind("<Tab>", self._commit_csv_cell_and_move)
        editor.bind("<Control-z>", self.handle_contextual_undo_shortcut)
        editor.bind("<Control-y>", self.handle_contextual_redo_shortcut)

    def _on_csv_combobox_button_press(self, _event):
        self._csv_combobox_posting = True
        self.after(150, self._clear_csv_combobox_posting)

    def _clear_csv_combobox_posting(self):
        self._csv_combobox_posting = False

    def _on_csv_cell_editor_focus_out(self, _event):
        editor = getattr(self, "csv_cell_editor", None)
        if editor is None:
            return

        if isinstance(editor, ttk.Combobox):
            self.after_idle(self._finish_csv_combobox_focus_check)
            return

        self._close_csv_cell_editor(commit=True)

    def _finish_csv_combobox_focus_check(self):
        editor = getattr(self, "csv_cell_editor", None)
        if editor is None or not isinstance(editor, ttk.Combobox):
            return
        if getattr(self, "_csv_combobox_posting", False):
            return

        try:
            focus = self.focus_get()
        except tk.TclError:
            focus = None

        if focus is editor:
            return

        try:
            popdown = editor.tk.call("ttk::combobox::PopdownWindow", str(editor))
            mapped = bool(int(editor.tk.call("winfo", "ismapped", popdown)))
        except (tk.TclError, ValueError):
            mapped = False

        if not mapped:
            self._close_csv_cell_editor(commit=True)

    def _on_csv_category_selected(self, _event):
        self._csv_combobox_posting = False

    def _csv_category_choices(self):
        choices = []
        seen = set()

        def add(value):
            value = str(value).strip()
            if not value:
                return
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                choices.append(value)

        # “未分类”是固定系统分类：下拉框中永远置于第一项。
        add("未分类")

        for value in getattr(self, "categories", []):
            if str(value).strip() != "未分类":
                add(value)

        category_fields = [
            field for field in self.csv_fieldnames
            if field.strip().casefold() in {"category", "group"}
        ]
        for row in self.csv_model_rows:
            for field in category_fields:
                value = str(row.get(field, "")).strip()
                if value != "未分类":
                    add(value)

        return choices

    def _commit_csv_cell_and_move(self, _event):
        target = getattr(self, "csv_cell_edit_target", None)
        if target is None:
            return "break"

        row_id, column_index = target
        self._close_csv_cell_editor(commit=True)

        row_ids = [f"row{index}" for index in range(len(self.csv_model_rows))]
        row_position = row_ids.index(row_id)
        next_column = column_index + 1

        if next_column >= len(self.csv_fieldnames):
            next_column = 0
            row_position += 1

        if row_position < len(row_ids):
            self._begin_csv_cell_edit(
                row_ids[row_position],
                f"#{next_column + 1}",
            )
        return "break"

    def _close_csv_cell_editor(self, commit):
        editor = getattr(self, "csv_cell_editor", None)
        target = getattr(self, "csv_cell_edit_target", None)
        if editor is None:
            return

        try:
            if commit and target is not None and editor.winfo_exists():
                row_id, column_index = target
                value = editor.get()

                if row_id == "header":
                    if value != self.csv_fieldnames[column_index]:
                        self._push_csv_local_history()
                    self._rename_csv_field(column_index, value)
                else:
                    row_index = int(row_id[3:])
                    field = self.csv_fieldnames[column_index]
                    if field.strip().casefold() in {"category", "group"}:
                        value = value.strip() or "未分类"
                    old_value = self.csv_model_rows[row_index].get(field, "")
                    if value != old_value:
                        self._push_csv_local_history()
                    self.csv_model_rows[row_index][field] = value
                    self.csv_editor.set(row_id, f"c{column_index}", value)
                    if field.strip().casefold() in {"category", "group"} and value != old_value:
                        self._apply_category_side_default_to_csv_row(row_index, value)
                    if value != old_value:
                        self._mark_csv_validation_location_processed(row_index, column_index)
        finally:
            try:
                editor.destroy()
            except tk.TclError:
                pass
            self.csv_cell_editor = None
            self.csv_cell_edit_target = None
            if getattr(self, "csv_validation_errors", []):
                self.after_idle(self._refresh_csv_validation_overlays)
            try:
                self.csv_editor.focus_set()
            except tk.TclError:
                pass

    def _rename_csv_field(self, column_index, new_name):
        old_name = self.csv_fieldnames[column_index]
        if new_name == old_name:
            return

        existing = {
            name.strip().casefold()
            for index, name in enumerate(self.csv_fieldnames)
            if index != column_index
        }
        if new_name.strip().casefold() in existing:
            messagebox.showwarning(
                "无法修改表头",
                f"表头“{new_name}”已经存在。",
            )
            return

        self.csv_fieldnames[column_index] = new_name
        for row in self.csv_model_rows:
            value = row.pop(old_name, "")
            row[new_name] = value

        column_id = f"c{column_index}"
        self.csv_editor.heading(
            column_id,
            text=self._csv_heading_text(column_index, new_name),
            anchor="center",
        )

    @staticmethod
    def _normalize_side_value(value):
        value = str(value or "").strip().casefold()
        return {
            "top": "top", "上": "top", "上侧": "top", "上方": "top",
            "bottom": "bottom", "下": "bottom", "下侧": "bottom", "下方": "bottom",
        }.get(value)

    @staticmethod
    def _side_language(value):
        value = str(value or "").strip().casefold()
        if value in {"top", "bottom"}:
            return "en"
        if value in {"上", "上侧", "上方", "下", "下侧", "下方"}:
            return "zh"
        return None

    def _csv_field_name(self, semantic_name):
        for field in self.csv_fieldnames:
            if field.strip().casefold() == semantic_name:
                return field
        return None

    def _csv_category_field(self):
        return self._csv_field_name("category") or self._csv_field_name("group")

    def _csv_side_field(self):
        return self._csv_field_name("side")

    def _detect_csv_side_display_mode(self):
        side_field = self._csv_side_field()
        languages = set()
        chinese_values = []
        if side_field:
            for row in self.csv_model_rows:
                value = str(row.get(side_field, "")).strip()
                language = self._side_language(value)
                if language:
                    languages.add(language)
                if language == "zh":
                    chinese_values.append(value)

        # 中文也保留源文件自己的词形族：上/下、上侧/下侧、上方/下方。
        if chinese_values and all(value in {"上", "下"} for value in chinese_values):
            zh_pair = ("上", "下")
        elif chinese_values and all(value in {"上方", "下方"} for value in chinese_values):
            zh_pair = ("上方", "下方")
        else:
            zh_pair = ("上侧", "下侧")

        if languages == {"en"}:
            self.csv_side_display_mode = "en"
            self.csv_side_display_values = ("top", "bottom")
        elif languages == {"zh", "en"}:
            self.csv_side_display_mode = "mixed"
            self.csv_side_display_values = (zh_pair[0], "top", zh_pair[1], "bottom")
        else:
            self.csv_side_display_mode = "zh"
            self.csv_side_display_values = zh_pair

    def _csv_side_choices(self):
        return tuple(getattr(self, "csv_side_display_values", ("上侧", "下侧")))

    def _default_side_display_value(self):
        return self._csv_side_choices()[0]

    def _side_display_for_semantic(self, semantic, preferred=""):
        semantic = self._normalize_side_value(semantic)
        preferred = str(preferred or "").strip()
        pairs = {
            "上": {"top": "上", "bottom": "下"}, "下": {"top": "上", "bottom": "下"},
            "上侧": {"top": "上侧", "bottom": "下侧"}, "下侧": {"top": "上侧", "bottom": "下侧"},
            "上方": {"top": "上方", "bottom": "下方"}, "下方": {"top": "上方", "bottom": "下方"},
        }
        if preferred.casefold() in {"top", "bottom"}:
            return semantic
        if preferred in pairs:
            return pairs[preferred][semantic]
        for value in self._csv_side_choices():
            if self._normalize_side_value(value) == semantic:
                return value
        return "上侧" if semantic == "top" else "下侧"

    def _derive_category_side_states(self, normalized_rows):
        states = {}
        sides = {}
        for row in normalized_rows:
            sides.setdefault(row["category"], set()).add(row["side"])
        for category, values in sides.items():
            states[category] = next(iter(values)) if len(values) == 1 else "unrestricted"
        return states

    def _category_preferred_display(self, category, semantic, exclude_index=None):
        category_field, side_field = self._csv_category_field(), self._csv_side_field()
        candidates = []
        if category_field and side_field:
            for index, row in enumerate(self.csv_model_rows):
                if index == exclude_index:
                    continue
                if (str(row.get(category_field, "")).strip() or "未分类") != category:
                    continue
                value = str(row.get(side_field, "")).strip()
                if self._normalize_side_value(value) == semantic:
                    candidates.append(value)
        if candidates and all(value == candidates[0] for value in candidates):
            return candidates[0]
        return self._side_display_for_semantic(semantic)

    def _apply_category_side_default_to_csv_row(self, row_index, category):
        side_field = self._csv_side_field()
        if not side_field:
            return
        state = getattr(self, "category_side_states", {}).get(category)
        if state in {"top", "bottom"}:
            value = self._category_preferred_display(category, state, exclude_index=row_index)
        else:
            value = self._default_side_display_value()
        old = self.csv_model_rows[row_index].get(side_field, "")
        self.csv_model_rows[row_index][side_field] = value
        side_index = self.csv_fieldnames.index(side_field)
        self.csv_editor.set(f"row{row_index}", f"c{side_index}", value)
        if old != value:
            self.status_var.set("已根据分类自动设置事件 side；点击“应用修改”后正式生效")
