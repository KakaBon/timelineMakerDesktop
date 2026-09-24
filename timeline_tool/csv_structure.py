"""CSV 行列增删、分类删除与日期排序。"""

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
    infer_numeric_date_style,
    get_current_numeric_date_style_hint,
    serialize_csv_model,
    validate_date_style,
)
from .utils import resource_path


class CSVStructureMixin:
    def delete_categories_from_data(self, categories):
        """正式删除分类及其事件，并同步 CSV 表格、分类区和时间轴。"""
        targets = {
            str(category).strip()
            for category in categories
            if str(category).strip() and str(category).strip() != "未分类"
        }
        if not targets:
            return

        self._close_csv_cell_editor(commit=True)
        history_before = (
            self._capture_global_snapshot()
            if hasattr(self, "_capture_global_snapshot") else None
        )

        old_categories = list(getattr(self, "categories", []))
        old_states = dict(getattr(self, "category_side_states", {}))
        old_colors = dict(getattr(self, "category_colors", {}))
        remaining_categories = [
            category for category in old_categories
            if category not in targets and category != "未分类"
        ]

        category_field = self._csv_category_field()
        if category_field:
            self.csv_model_rows = [
                dict(row) for row in self.csv_model_rows
                if (str(row.get(category_field, "")).strip() or "未分类")
                not in targets
            ]
        else:
            # 理论上合法表格一定有 category/group；这里仍按正式 rows 兜底。
            surviving_ids = {
                row.get("_id") for row in getattr(self, "rows", [])
                if row.get("category") not in targets
            }
            self.csv_model_rows = [
                dict(row) for index, row in enumerate(self.csv_model_rows, start=1)
                if index in surviving_ids
            ]

        self._render_csv_grid()
        self._reset_csv_search_state()

        raw_rows = self._csv_model_as_raw_rows()
        remaining_states = {
            category: state
            for category, state in old_states.items()
            if category not in targets
        }
        remaining_states["未分类"] = "unrestricted"

        if raw_rows:
            self.load_rows(
                raw_rows,
                "已删除分类及其事件",
                csv_text=None,
                csv_format=self.current_csv_format,
                csv_fieldnames=self.csv_fieldnames,
                update_csv_model=False,
                category_side_states=remaining_states,
                refresh_legend=False,
            )

            # load_rows 会按事件重建分类；把仍存在的空分类补回当前会话。
            for category in remaining_categories:
                if category not in self.categories:
                    self.categories.append(category)
                if category in old_states:
                    self.category_side_states[category] = old_states[category]
                if category in old_colors:
                    self.category_colors[category] = old_colors[category]
            if "未分类" in old_colors:
                self.category_colors["未分类"] = old_colors["未分类"]
            if hasattr(self, "refresh_legend_incremental"):
                self.refresh_legend_incremental()
            else:
                self.render_legend()
            self.render()
        else:
            # 删除后允许当前文档暂时没有事件；CSV 表头和剩余空分类仍保留。
            self.rows = []
            self.categories = ["未分类"] + remaining_categories
            self.category_side_states = {
                category: remaining_states.get(category, "unrestricted")
                for category in self.categories
            }
            self.category_side_states["未分类"] = "unrestricted"
            self.category_colors = {
                category: old_colors.get(category, PALETTE[index % len(PALETTE)])
                for index, category in enumerate(self.categories)
            }
            self.hidden_categories.intersection_update(self.categories)
            self.timeline_search_matches = []
            self.timeline_search_index = -1
            self.timeline_search_query = ""
            self.selected_event_id = None
            self.update_timeline_search_counter()
            self.render_legend()
            self.render()

        self.selected_categories.difference_update(targets)
        if hasattr(self, "reset_event_migration_plan"):
            self.reset_event_migration_plan()
        self.has_unexported_csv_edits = True
        deleted_count = len(targets)
        self.status_var.set(
            f"已删除 {deleted_count} 个分类；CSV 与时间轴已同步更新"
        )
        if hasattr(self, "_commit_global_history"):
            names = "、".join(sorted(targets))
            self._commit_global_history(
                history_before,
                f"删除分类：{names}",
                clear_csv_local_history=True,
            )

    def _refresh_csv_grid_after_model_change(self):
        """结构性草稿修改后重建表格，同时保留查找/替换输入。"""
        current_query = (
            self.csv_text_search_var.get()
            if hasattr(self, "csv_text_search_var") else ""
        )
        current_replacement = (
            self.csv_text_replace_var.get()
            if hasattr(self, "csv_text_replace_var") else ""
        )

        self._render_csv_grid()
        self.csv_text_search_query = current_query
        self.csv_text_search_matches = (
            self.collect_csv_text_search_matches(current_query)
            if current_query else []
        )
        self.csv_text_search_index = -1
        self._clear_csv_grid_search_highlight()
        self.update_csv_text_search_counter()
        if hasattr(self, "csv_text_replace_var"):
            self.csv_text_replace_var.set(current_replacement)

    def add_csv_event_row(self):
        """在 CSV 草稿末尾新增一条事件，并直接进入 date 单元格编辑。"""
        self._close_csv_cell_editor(commit=True)

        if not self.csv_fieldnames:
            messagebox.showwarning("无法新增事件", "CSV 编辑区当前没有字段。")
            return

        self._push_csv_local_history()
        new_row = {field: "" for field in self.csv_fieldnames}

        # 新事件默认进入系统固定的“未分类”；side 使用当前文档的显示词形，
        # 其余字段留空，由用户直接补写。
        category_field = self._csv_category_field()
        if category_field:
            new_row[category_field] = "未分类"
        side_field = self._csv_side_field()
        if side_field:
            new_row[side_field] = self._default_side_display_value()

        self._ensure_csv_selection_state()
        new_row["__csv_uid__"] = self.csv_next_row_uid
        self.csv_next_row_uid += 1
        self.csv_model_rows.append(new_row)
        new_row_index = len(self.csv_model_rows) - 1
        new_row_id = f"row{new_row_index}"

        self._refresh_csv_grid_after_model_change()

        date_field = self._csv_field_name("date")
        if date_field in self.csv_fieldnames:
            column_index = self.csv_fieldnames.index(date_field)
        else:
            column_index = 0
        self.csv_active_column = column_index

        def focus_new_row():
            try:
                self.csv_editor.see(new_row_id)
                self.csv_editor.selection_set(new_row_id)
                self.csv_editor.focus(new_row_id)
                if hasattr(self, "csv_row_numbers"):
                    self.csv_row_numbers.selection_set(new_row_id)
                    self.csv_row_numbers.focus(new_row_id)
                self._begin_csv_cell_edit(new_row_id, f"#{column_index + 1}")
            except tk.TclError:
                pass

        self.after_idle(focus_new_row)
        self.status_var.set(
            f"已新增第 {new_row_index + 1} 条 CSV 事件；补全内容后点击“应用修改”正式生效"
        )

    def add_csv_field(self):
        """新增一个额外 CSV 字段；字段名通过小型对话框确定。"""
        self._close_csv_cell_editor(commit=True)

        if not self.csv_fieldnames:
            messagebox.showwarning("无法新增字段", "CSV 编辑区当前没有表格结构。")
            return

        dialog = tk.Toplevel(self)
        dialog.title("新增字段")
        dialog.transient(self)
        dialog.resizable(False, False)
        dialog.configure(bg="#f7f8fa")
        dialog.grab_set()

        body = tk.Frame(dialog, bg="#f7f8fa", padx=16, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(
            body, text="字段名", bg="#f7f8fa", fg="#30394c",
            font=("Microsoft YaHei", 9),
        ).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 10))

        field_var = tk.StringVar()
        entry = tk.Entry(
            body, textvariable=field_var, width=24,
            font=("Consolas", 10), relief="solid", bd=1,
        )
        entry.grid(row=0, column=1, sticky="ew", pady=(0, 10))

        buttons = tk.Frame(body, bg="#f7f8fa")
        buttons.grid(row=1, column=0, columnspan=2, sticky="e")

        def cancel(_event=None):
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.destroy()

        def submit(_event=None):
            name = field_var.get().strip()
            if not name:
                messagebox.showwarning(
                    "无法新增字段", "字段名不能为空。", parent=dialog
                )
                entry.focus_set()
                return
            normalized_name = name.casefold()
            if normalized_name == "__source_row__":
                messagebox.showwarning(
                    "无法新增字段", "该字段名为程序内部保留名称，请换一个名称。", parent=dialog
                )
                entry.focus_set()
                entry.selection_range(0, tk.END)
                return

            existing = {str(field).strip().casefold() for field in self.csv_fieldnames}
            if normalized_name in existing:
                messagebox.showwarning(
                    "无法新增字段", f"字段“{name}”已经存在。", parent=dialog
                )
                entry.focus_set()
                entry.selection_range(0, tk.END)
                return
            # category / group 在程序中属于同一个语义字段；不允许同时存在，
            # 否则应用时会出现到底以哪一列为准的歧义。
            if normalized_name in {"category", "group"} and ({"category", "group"} & existing):
                messagebox.showwarning(
                    "无法新增字段",
                    "category 与 group 在本工具中表示同一类字段，当前表格已经存在其中一个。",
                    parent=dialog,
                )
                entry.focus_set()
                entry.selection_range(0, tk.END)
                return

            self._push_csv_local_history()
            self.csv_fieldnames.append(name)
            for row in self.csv_model_rows:
                row[name] = ""

            self._refresh_csv_grid_after_model_change()
            self.csv_active_column = len(self.csv_fieldnames) - 1

            cancel()

            def show_new_field():
                try:
                    self.csv_editor.xview_moveto(1.0)
                    self._after_csv_grid_scroll()
                except tk.TclError:
                    pass

            self.after_idle(show_new_field)
            self.status_var.set(
                f"已新增 CSV 字段“{name}”；点击“应用修改”后正式生效"
            )

        tk.Button(
            buttons, text="取消", command=cancel,
            font=("Microsoft YaHei", 9), padx=10,
        ).pack(side="right", padx=(6, 0))
        tk.Button(
            buttons, text="新增", command=submit,
            font=("Microsoft YaHei", 9), padx=10,
        ).pack(side="right")

        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", cancel)
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - dialog.winfo_reqwidth()) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - dialog.winfo_reqheight()) // 3)
        dialog.geometry(f"+{x}+{y}")
        entry.focus_set()

    def mark_selected_csv_for_deletion(self):
        """把选中的行列标记为预删除；真正删除发生在“应用修改”。"""
        # 先记住当前正在编辑/聚焦的行。新增事件后这一行本来就以整行浅蓝色
        # 显示为当前项；若用户直接点垃圾桶，应把她眼前这个“已选中”的行
        # 当作删除目标，而不是再要求额外点击一次行头。
        active_target = getattr(self, "csv_cell_edit_target", None)
        focused_row = ""
        try:
            focused_row = self.csv_editor.focus()
        except tk.TclError:
            pass

        self._close_csv_cell_editor(commit=True)
        self._ensure_csv_selection_state()

        selected_rows = set(self.csv_selected_row_uids) - set(self.csv_pending_delete_row_uids)
        selected_fields = set(self.csv_selected_fields) - set(self.csv_pending_delete_fields)

        if not selected_rows and not selected_fields:
            candidate_row = active_target[0] if active_target and active_target[0] != "header" else focused_row
            if candidate_row and str(candidate_row).startswith("row"):
                try:
                    row_index = int(str(candidate_row)[3:])
                    if 0 <= row_index < len(self.csv_model_rows):
                        uid = self._csv_row_uid(self.csv_model_rows[row_index])
                        if uid not in self.csv_pending_delete_row_uids:
                            selected_rows.add(uid)
                except (TypeError, ValueError):
                    pass

        required_semantics = {"date", "title", "side", "category", "group"}
        blocked_fields = {
            field for field in selected_fields
            if field.strip().casefold() in required_semantics
        }

        # 关键字段删除是阻断操作，不是免责声明。
        # 只要本次删除目标中含关键字段，整次删除都不执行，
        # 关键字段也从头到尾不会进入灰色预删除状态。
        if blocked_fields:
            messagebox.showwarning(
                "关键字段不可删除",
                "以下关键字段是时间轴运行所必需的，不能删除：\n\n"
                + "、".join(sorted(blocked_fields))
                + "\n\n请取消这些字段的选择后，再删除其它行 / 字段。",
            )
            return

        deletable_fields = set(selected_fields)

        if not selected_rows and not deletable_fields:
            messagebox.showwarning(
                "删除行 / 列",
                "请先点击左侧行头或上方列头选择要删除的行 / 列。",
            )
            return

        self._push_csv_local_history()
        self.csv_pending_delete_row_uids.update(selected_rows)
        self.csv_pending_delete_fields.update(deletable_fields)
        self.csv_selected_row_uids.clear()
        self.csv_selected_fields.clear()

        # 预删除本身就是处理非法数据的一种合法方式。把已经被预删除行/列中的
        # 旧错误从引导队列中剔除；其它未处理错误继续保留。
        if getattr(self, "csv_validation_errors", []):
            kept_errors = []
            for row_index, column_index, message in self.csv_validation_errors:
                if not (0 <= row_index < len(self.csv_model_rows)):
                    continue
                row_uid = self._csv_row_uid(self.csv_model_rows[row_index])
                field = self.csv_fieldnames[column_index] if 0 <= column_index < len(self.csv_fieldnames) else None
                if row_uid in self.csv_pending_delete_row_uids:
                    continue
                if field in self.csv_pending_delete_fields:
                    continue
                kept_errors.append((row_index, column_index, message))
            self.csv_validation_errors = kept_errors
            self.csv_validation_guidance_active = bool(kept_errors)

        self._refresh_csv_grid_after_model_change()
        if getattr(self, "csv_validation_errors", []):
            self.after_idle(self._refresh_csv_validation_overlays)

        parts = []
        if selected_rows:
            parts.append(f"{len(selected_rows)} 行")
        if deletable_fields:
            parts.append(f"{len(deletable_fields)} 列")
        self.status_var.set(
            f"已预删除{'、'.join(parts)}；点击“应用修改”后正式删除"
        )

    def _materialize_csv_pending_deletions(self):
        """在校验通过后把预删除状态正式写入 CSV 草稿模型。"""
        self._ensure_csv_selection_state()
        pending_rows = set(self.csv_pending_delete_row_uids)
        pending_fields = set(self.csv_pending_delete_fields)
        if not pending_rows and not pending_fields:
            return 0, 0

        old_row_count = len(self.csv_model_rows)
        old_field_count = len(self.csv_fieldnames)
        self.csv_model_rows = [
            dict(row) for row in self.csv_model_rows
            if self._csv_row_uid(row) not in pending_rows
        ]
        self.csv_fieldnames = [
            field for field in self.csv_fieldnames
            if field not in pending_fields
        ]
        for row in self.csv_model_rows:
            for field in pending_fields:
                row.pop(field, None)

        self.csv_pending_delete_row_uids.clear()
        self.csv_pending_delete_fields.clear()
        self.csv_selected_row_uids.clear()
        self.csv_selected_fields.clear()
        self._render_csv_grid()
        return old_row_count - len(self.csv_model_rows), old_field_count - len(self.csv_fieldnames)

    def sort_csv_rows_by_date(self):
        """按 date 从早到晚稳定排序当前 CSV 草稿，不自动应用到时间轴。"""
        self._close_csv_cell_editor(commit=True)

        if not self.csv_fieldnames or not self.csv_model_rows:
            messagebox.showwarning("无法排序", "CSV 编辑区没有可排序的数据。")
            return

        date_field = self._csv_field_name("date")
        if not date_field:
            messagebox.showwarning("无法排序", "CSV 缺少 date 字段。")
            return

        date_column = self.csv_fieldnames.index(date_field)
        parsed_rows = []
        errors = []

        self._ensure_csv_selection_state()
        active_rows = [
            row for row in self.csv_model_rows
            if self._csv_row_uid(row) not in self.csv_pending_delete_row_uids
        ]
        date_style_hint = infer_numeric_date_style(
            str(row.get(date_field, "")).strip() for row in active_rows
        )
        if date_style_hint is None:
            date_style_hint = get_current_numeric_date_style_hint()

        pending_rows = []
        for row_index, row in enumerate(self.csv_model_rows):
            if self._csv_row_uid(row) in self.csv_pending_delete_row_uids:
                pending_rows.append((row_index, row))
                continue
            date_value = str(row.get(date_field, "")).strip()
            parsed_date, date_style = parse_flexible_date(
                date_value, preferred_numeric_style=date_style_hint
            )
            if not date_value:
                errors.append(
                    f"第 {row_index + 1} 行 date 为空"
                )
                continue
            if not parsed_date:
                if date_style == "ambiguous-numeric":
                    errors.append(
                        f"第 {row_index + 1} 行日期无法判断日/月顺序：{date_value}"
                    )
                else:
                    errors.append(
                        f"第 {row_index + 1} 行日期格式无法识别：{date_value}"
                    )
                continue
            parsed_rows.append((parsed_date, row_index, row))

        if errors:
            preview = "\n".join(errors[:12])
            if len(errors) > 12:
                preview += f"\n……另有 {len(errors) - 12} 项"
            messagebox.showwarning(
                "无法按日期排序",
                "请先修正以下日期，再执行排序：\n\n" + preview,
            )
            return

        sorted_rows = sorted(parsed_rows, key=lambda item: (item[0], item[1]))
        new_order = [original_index for _date, original_index, _row in sorted_rows]
        if new_order == list(range(len(self.csv_model_rows))):
            self.status_var.set("CSV 表格已经按日期从早到晚排列")
            return

        # 排序属于 CSV 草稿编辑：支持现有 Ctrl+Z / Ctrl+Y，
        # 但只有点击“应用修改”后才同步到正式 rows / 时间轴。
        self._push_csv_local_history()
        self.csv_model_rows = [dict(row) for _date, _index, row in sorted_rows] + [
            dict(row) for _index, row in pending_rows
        ]

        # 行号和 Treeview iid 都会变化，旧定位缓存必须重建。
        current_query = self.csv_text_search_var.get() if hasattr(self, "csv_text_search_var") else ""
        current_replacement = self.csv_text_replace_var.get() if hasattr(self, "csv_text_replace_var") else ""
        self._render_csv_grid()

        self.csv_text_search_query = current_query
        self.csv_text_search_matches = (
            self.collect_csv_text_search_matches(current_query)
            if current_query else []
        )
        self.csv_text_search_index = -1
        self._clear_csv_grid_search_highlight()
        self.update_csv_text_search_counter()
        if hasattr(self, "csv_text_replace_var"):
            self.csv_text_replace_var.set(current_replacement)

        self.status_var.set(
            "已按日期从早到晚排序 CSV 表格；点击“应用修改”后正式生效"
        )
