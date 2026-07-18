"""CSVManagerMixin：按功能拆分自原始桌面时间轴工具。"""

import csv
import io
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from .config import PALETTE
from .utils import parse_date, resource_path


class CSVManagerMixin:
    def load_sample(self):
        sample_path = resource_path("test-data.csv")

        try:
            csv_text = sample_path.read_text(encoding="utf-8-sig")
            rows = self.parse_csv_text(csv_text)
            self.current_csv_name = sample_path.name
            self.current_csv_directory = Path.cwd()
            self.load_rows(
                rows,
                "已载入示例数据",
                csv_text=csv_text,
            )
            self.has_unexported_csv_edits = False
        except Exception as exc:
            messagebox.showerror("读取失败", str(exc))

    def import_csv(self):
        path = filedialog.askopenfilename(
            title="选择 CSV 文件",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return

        last_error = None

        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                csv_text = Path(path).read_text(encoding=encoding)
                rows = self.parse_csv_text(csv_text)
                selected_path = Path(path)
                self.current_csv_name = selected_path.name
                self.current_csv_directory = selected_path.parent
                self.load_rows(
                    rows,
                    f"已导入 {Path(path).name}",
                    csv_text=csv_text,
                )
                self.has_unexported_csv_edits = False
                return
            except Exception as exc:
                last_error = exc

        messagebox.showerror("导入失败", str(last_error))

    def parse_csv_text(self, csv_text):
        if not csv_text.strip():
            raise ValueError("CSV 文本为空。")

        reader = csv.DictReader(io.StringIO(csv_text))

        if not reader.fieldnames:
            raise ValueError("CSV 缺少表头。")

        return list(reader)

    def set_csv_editor_text(self, csv_text):
        self.current_csv_text = csv_text
        self.csv_editor.delete("1.0", tk.END)
        self.csv_editor.insert("1.0", csv_text)
        self.csv_editor.edit_reset()

        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self.csv_text_search_query = ""

        if hasattr(self, "csv_text_search_var"):
            self.csv_text_search_var.set("")
            self.csv_text_replace_var.set("")
            self.update_csv_text_search_counter()

    def collect_csv_text_search_matches(self, query):
        text = self.csv_editor.get("1.0", "end-1c")
        lower_text = text.lower()
        lower_query = query.lower()

        matches = []
        search_from = 0

        while search_from <= len(lower_text):
            found_at = lower_text.find(lower_query, search_from)

            if found_at < 0:
                break

            matches.append(
                (found_at, found_at + len(query))
            )
            search_from = found_at + max(1, len(query))

        return matches

    def execute_csv_text_search(self):
        query = self.csv_text_search_var.get()

        if not query:
            self.clear_csv_text_search()
            self.status_var.set("请输入 CSV 文本查找关键词")
            return

        self.csv_text_search_query = query
        self.csv_text_search_matches = (
            self.collect_csv_text_search_matches(query)
        )
        self.csv_text_search_index = -1
        self.update_csv_text_search_counter()

        if not self.csv_text_search_matches:
            self.csv_editor.tag_remove(tk.SEL, "1.0", tk.END)
            self.status_var.set("没有找到匹配的 CSV 文本")
            return

        self.show_csv_text_search_match(0)

    def show_csv_text_search_match(self, index):
        if not self.csv_text_search_matches:
            return

        self.csv_text_search_index = (
            index % len(self.csv_text_search_matches)
        )

        start_offset, end_offset = self.csv_text_search_matches[
            self.csv_text_search_index
        ]
        start_index = f"1.0+{start_offset}c"
        end_index = f"1.0+{end_offset}c"

        self.csv_editor.tag_remove(tk.SEL, "1.0", tk.END)
        self.csv_editor.tag_add(tk.SEL, start_index, end_index)
        self.csv_editor.mark_set(tk.INSERT, end_index)
        self.csv_editor.see(start_index)
        self.csv_editor.focus_set()

        self.update_csv_text_search_counter()
        self.status_var.set(
            f"已定位 CSV 文本匹配结果 "
            f"{self.csv_text_search_index + 1} / "
            f"{len(self.csv_text_search_matches)}"
        )

    def show_next_csv_text_search_match(self):
        current_query = self.csv_text_search_var.get()

        if (
            not self.csv_text_search_matches
            or current_query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()
            return

        self.show_csv_text_search_match(
            self.csv_text_search_index + 1
        )

    def show_previous_csv_text_search_match(self):
        current_query = self.csv_text_search_var.get()

        if (
            not self.csv_text_search_matches
            or current_query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()
            return

        self.show_csv_text_search_match(
            self.csv_text_search_index - 1
        )

    def clear_csv_text_search(self):
        self.csv_text_search_var.set("")
        self.csv_text_search_query = ""
        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self.csv_editor.tag_remove(tk.SEL, "1.0", tk.END)
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
            messagebox.showwarning(
                "无法替换",
                "请先输入要查找的文本。",
            )
            return

        if (
            not self.csv_text_search_matches
            or query != self.csv_text_search_query
        ):
            self.execute_csv_text_search()

        if not self.csv_text_search_matches:
            return

        active_index = (
            self.csv_text_search_index
            if self.csv_text_search_index >= 0
            else 0
        )
        start_offset, end_offset = (
            self.csv_text_search_matches[active_index]
        )
        start_index = f"1.0+{start_offset}c"
        end_index = f"1.0+{end_offset}c"
        replacement = self.csv_text_replace_var.get()

        self.csv_editor.delete(start_index, end_index)
        self.csv_editor.insert(start_index, replacement)

        self.csv_text_search_query = query
        self.csv_text_search_matches = (
            self.collect_csv_text_search_matches(query)
        )
        self.csv_text_search_index = -1
        self.update_csv_text_search_counter()

        if self.csv_text_search_matches:
            next_index = min(
                active_index,
                len(self.csv_text_search_matches) - 1,
            )
            self.show_csv_text_search_match(next_index)
        else:
            self.csv_editor.tag_remove(
                tk.SEL,
                "1.0",
                tk.END,
            )

        self.status_var.set(
            "已替换当前匹配文本；点击“应用修改”后时间轴才会更新"
        )

    def replace_all_csv_text_matches(self):
        query = self.csv_text_search_var.get()

        if not query:
            messagebox.showwarning(
                "无法替换",
                "请先输入要查找的文本。",
            )
            return

        replacement = self.csv_text_replace_var.get()
        original_text = self.csv_editor.get(
            "1.0",
            "end-1c",
        )

        replaced_text, count = re.subn(
            re.escape(query),
            lambda _match: replacement,
            original_text,
            flags=re.IGNORECASE,
        )

        if count == 0:
            self.status_var.set("没有找到可替换的 CSV 文本")
            return

        self.csv_editor.delete("1.0", tk.END)
        self.csv_editor.insert("1.0", replaced_text)

        self.csv_text_search_query = query
        self.csv_text_search_matches = (
            self.collect_csv_text_search_matches(query)
        )
        self.csv_text_search_index = -1
        self.csv_editor.tag_remove(tk.SEL, "1.0", tk.END)
        self.update_csv_text_search_counter()

        self.status_var.set(
            f"已完成全部替换，共替换 {count} 处；"
            "点击“应用修改”后时间轴才会更新"
        )

    def apply_csv_editor_changes(self):
        csv_text = self.csv_editor.get("1.0", "end-1c")

        if not csv_text.strip():
            messagebox.showwarning("无法应用", "CSV 编辑区没有内容。")
            return

        try:
            rows = self.parse_csv_text(csv_text)
            self.load_rows(
                rows,
                "已应用 CSV 编辑区修改",
                csv_text=csv_text,
            )
            self.has_unexported_csv_edits = True
        except Exception as exc:
            messagebox.showerror("应用失败", str(exc))

    def export_csv(self):
        """导出最近一次成功应用的 CSV 文本。成功后清除未导出状态。"""
        csv_text = self.current_csv_text

        if not csv_text.strip():
            messagebox.showwarning("无法导出", "当前没有可导出的 CSV 内容。")
            return False

        source_name = Path(self.current_csv_name or "timeline.csv")
        default_name = f"{source_name.stem}_副本.csv"

        path = filedialog.asksaveasfilename(
            title="导出 CSV",
            defaultextension=".csv",
            initialdir=str(self.current_csv_directory),
            initialfile=default_name,
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")],
        )
        if not path:
            return False

        try:
            # 使用 UTF-8 BOM，便于 Windows 与表格软件直接识别中文。
            Path(path).write_text(csv_text, encoding="utf-8-sig")
            self.has_unexported_csv_edits = False
            exported_path = str(Path(path))
            exported_name = Path(path).name
            self.status_var.set(f"已导出 CSV：{exported_path}")
            messagebox.showinfo(
                "导出完成",
                f"CSV 导出成功。\n\n文件：{exported_name}",
            )
            return True
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))
            return False

    def on_close_request(self):
        """关闭窗口时，仅对已经应用但尚未导出的编辑进行确认。"""
        if not self.has_unexported_csv_edits:
            self.destroy()
            return

        choice = messagebox.askyesnocancel(
            "CSV 尚未导出",
            "CSV 内容有新的编辑，是否导出 CSV？",
            icon="warning",
        )

        if choice is None:
            # 取消：保持关闭前的全部页面和数据状态。
            return

        if choice is False:
            self.destroy()
            return

        # 选择“是”后调用与顶部按钮完全相同的导出流程。
        # 只有实际保存成功才关闭；取消保存窗口或导出失败都继续留在工具中。
        if self.export_csv():
            self.destroy()

    def load_rows(self, raw_rows, message, csv_text=None):
        normalized = []

        for row in raw_rows:
            cleaned = {
                str(key).strip().lower(): ("" if value is None else str(value).strip())
                for key, value in row.items()
                if key is not None
            }

            if not cleaned:
                continue

            date_value = cleaned.get("date", "")
            title = cleaned.get("title", "")
            category = cleaned.get("category", "") or cleaned.get("group", "")
            side = cleaned.get("side", "top").lower()
            side = "bottom" if side in ("下方", "bottom") else "top"

            if not parse_date(date_value) or not title or not category:
                continue

            cleaned["date"] = date_value
            cleaned["title"] = title
            cleaned["category"] = category
            cleaned["side"] = side
            cleaned["_id"] = len(normalized) + 1
            normalized.append(cleaned)

        if not normalized:
            raise ValueError("没有读到有效事件。请确认存在 date、title、category/group、side 列。")

        self.rows = normalized

        if csv_text is not None:
            self.set_csv_editor_text(csv_text)

        self.categories = list(dict.fromkeys(row["category"] for row in self.rows))
        self.category_colors = {
            name: PALETTE[index % len(PALETTE)]
            for index, name in enumerate(self.categories)
        }

        self.hidden_categories.clear()
        self.timeline_search_matches = []
        self.timeline_search_index = -1
        self.timeline_search_query = ""
        self.selected_event_id = None
        self.update_timeline_search_counter()
        self.fit_to_data()
        self.render_legend()
        self.render()
        self.status_var.set(f"{message}，共 {len(self.rows)} 个事件")
