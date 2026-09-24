"""CSV 查找与替换。"""

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


class CSVSearchMixin:
    def collect_csv_text_search_matches(self, query):
        """只搜索数据单元格；表头行与左侧行号列都不参与匹配。"""
        lower_query = query.casefold()
        matches = []

        self._ensure_csv_selection_state()
        for row_index, row in enumerate(self.csv_model_rows):
            if self._csv_row_uid(row) in self.csv_pending_delete_row_uids:
                continue
            for column_index, field in enumerate(self.csv_fieldnames):
                if field in self.csv_pending_delete_fields:
                    continue
                text = str(row.get(field, ""))
                lower_text = text.casefold()
                search_from = 0
                while search_from <= len(lower_text):
                    found_at = lower_text.find(lower_query, search_from)
                    if found_at < 0:
                        break
                    matches.append(
                        (
                            f"row{row_index}",
                            column_index,
                            found_at,
                            found_at + len(query),
                        )
                    )
                    search_from = found_at + max(1, len(query))

        return matches

    def execute_csv_text_search(self):
        query = self.csv_text_search_var.get()
        if not query:
            self.clear_csv_text_search()
            self.status_var.set("请输入 CSV 表格查找关键词")
            return

        self.csv_text_search_query = query
        self.csv_text_search_matches = self.collect_csv_text_search_matches(query)
        self.csv_text_search_index = -1
        self.update_csv_text_search_counter()

        if not self.csv_text_search_matches:
            self._clear_csv_grid_search_highlight()
            self.status_var.set("没有找到匹配的 CSV 内容")
            return

        self.show_csv_text_search_match(0)

    def _clear_csv_grid_search_highlight(self):
        self._hide_csv_search_overlay()
        for item in self.csv_editor.get_children():
            tags = list(self.csv_editor.item(item, "tags"))
            tags = [tag for tag in tags if tag != "search_match"]
            if item == "header" and "header" not in tags:
                tags.append("header")
            self.csv_editor.item(item, tags=tuple(tags))

    def show_csv_text_search_match(self, index):
        if not self.csv_text_search_matches:
            return

        self.csv_text_search_index = index % len(self.csv_text_search_matches)
        row_id, column_index, _start, _end = self.csv_text_search_matches[
            self.csv_text_search_index
        ]

        self._clear_csv_grid_search_highlight()
        if row_id != "header":
            self.csv_editor.focus(row_id)
            self.csv_editor.selection_set(row_id)
            if hasattr(self, "csv_row_numbers"):
                self.csv_row_numbers.selection_set(row_id)
            self.csv_editor.see(row_id)
        self.csv_active_column = column_index
        self.after_idle(self._refresh_csv_search_overlay)

        visible_row = "表头" if row_id == "header" else int(row_id[3:]) + 1
        self.update_csv_text_search_counter()
        self.status_var.set(
            f"已定位 CSV 表格匹配结果 "
            f"{self.csv_text_search_index + 1} / "
            f"{len(self.csv_text_search_matches)}；"
            f"{('第 ' + str(visible_row) + ' 行') if visible_row != '表头' else '表头'}，"
            f"{self._spreadsheet_column_name(column_index)} 列"
        )

    def show_next_csv_text_search_match(self):
        current_query = self.csv_text_search_var.get()
        if (
            not self.csv_text_search_matches
            or current_query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()
            return
        self.show_csv_text_search_match(self.csv_text_search_index + 1)

    def show_previous_csv_text_search_match(self):
        current_query = self.csv_text_search_var.get()
        if (
            not self.csv_text_search_matches
            or current_query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()
            return
        self.show_csv_text_search_match(self.csv_text_search_index - 1)

    def clear_csv_text_search(self):
        self.csv_text_search_var.set("")
        self.csv_text_search_query = ""
        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self._clear_csv_grid_search_highlight()
        self.update_csv_text_search_counter()
        self.csv_text_search_entry.focus_set()

    def clear_csv_text_replacement(self):
        self.csv_text_replace_var.set("")
        self.csv_text_replace_entry.focus_set()

    def update_csv_text_search_counter(self):
        current = (
            self.csv_text_search_index + 1
            if self.csv_text_search_index >= 0
            else 0
        )
        self.csv_text_search_counter_var.set(
            f"{current}/{len(self.csv_text_search_matches)}"
        )

    def replace_current_csv_text_match(self):
        query = self.csv_text_search_var.get()
        if not query:
            messagebox.showwarning("无法替换", "请先输入要查找的文本。")
            return

        if (
            not self.csv_text_search_matches
            or query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()
        if not self.csv_text_search_matches:
            return

        match_index = max(self.csv_text_search_index, 0)
        row_id, column_index, start, end = self.csv_text_search_matches[
            match_index
        ]
        replacement = self.csv_text_replace_var.get()
        self._push_csv_local_history()

        if row_id == "header":
            original = self.csv_fieldnames[column_index]
            changed = original[:start] + replacement + original[end:]
            self._rename_csv_field(column_index, changed)
        else:
            row_index = int(row_id[3:])
            field = self.csv_fieldnames[column_index]
            original = self.csv_model_rows[row_index].get(field, "")
            changed = original[:start] + replacement + original[end:]
            self.csv_model_rows[row_index][field] = changed
            self.csv_editor.set(row_id, f"c{column_index}", changed)

        self.csv_text_search_matches = self.collect_csv_text_search_matches(query)
        self.csv_text_search_index = -1
        self.update_csv_text_search_counter()

        if self.csv_text_search_matches:
            self.show_csv_text_search_match(
                min(match_index, len(self.csv_text_search_matches) - 1)
            )
        else:
            self._clear_csv_grid_search_highlight()

        self.status_var.set(
            "已替换当前匹配内容；点击“应用修改”后时间轴才会更新"
        )

    def replace_all_csv_text_matches(self):
        self._close_csv_cell_editor(commit=True)
        query = self.csv_text_search_var.get()
        if not query:
            messagebox.showwarning("无法替换", "请先输入要查找的文本。")
            return

        replacement = self.csv_text_replace_var.get()
        before_snapshot = self._csv_snapshot()
        pattern = re.compile(re.escape(query), flags=re.IGNORECASE)
        count = 0

        # 与查找范围一致：只处理仍然有效的数据单元格，不修改表头字段名。
        self._ensure_csv_selection_state()
        for row in self.csv_model_rows:
            if self._csv_row_uid(row) in self.csv_pending_delete_row_uids:
                continue
            for field in list(self.csv_fieldnames):
                if field in self.csv_pending_delete_fields:
                    continue
                original = str(row.get(field, ""))
                changed, cell_count = pattern.subn(replacement, original)
                if cell_count:
                    row[field] = changed
                    count += cell_count

        if count == 0:
            self.status_var.set("没有找到可替换的 CSV 内容")
            return

        if not self.csv_local_undo_stack or self.csv_local_undo_stack[-1] != before_snapshot:
            self.csv_local_undo_stack.append(before_snapshot)
            self.csv_local_redo_stack.clear()
        self._render_csv_grid()
        self.csv_text_search_query = query
        self.csv_text_search_matches = self.collect_csv_text_search_matches(query)
        self.csv_text_search_index = -1
        self.update_csv_text_search_counter()

        self.status_var.set(
            f"已完成全部替换，共替换 {count} 处；"
            "点击“应用修改”后时间轴才会更新"
        )
