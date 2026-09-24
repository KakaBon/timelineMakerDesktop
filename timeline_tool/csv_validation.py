"""CSV 校验、错误引导与应用前 side 协调。"""

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


class CSVValidationMixin:
    def _collect_csv_model_validation_errors(self):
        self._ensure_csv_selection_state()
        errors = []
        date_styles = []
        active_fields = [
            field for field in self.csv_fieldnames
            if field not in self.csv_pending_delete_fields
        ]

        def active_semantic(name):
            for field in active_fields:
                if field.strip().casefold() == name:
                    return field
            return None

        date_field = active_semantic("date")
        title_field = active_semantic("title")
        side_field = active_semantic("side")
        if not (date_field and title_field and side_field):
            return errors

        active_rows = [
            row for row in self.csv_model_rows
            if self._csv_row_uid(row) not in self.csv_pending_delete_row_uids
        ]
        date_style_hint = infer_numeric_date_style(
            str(row.get(date_field, "")).strip() for row in active_rows
        )
        if date_style_hint is None:
            date_style_hint = get_current_numeric_date_style_hint()

        for row_index, row in enumerate(self.csv_model_rows):
            if self._csv_row_uid(row) in self.csv_pending_delete_row_uids:
                continue
            source_row = row_index + 1
            date_value = str(row.get(date_field, "")).strip()
            title = str(row.get(title_field, "")).strip()
            side_value = str(row.get(side_field, "")).strip()
            parsed_date, date_style = parse_flexible_date(
                date_value, preferred_numeric_style=date_style_hint
            )
            if not date_value:
                errors.append((row_index, self.csv_fieldnames.index(date_field), f"第 {source_row} 行 date 为空"))
            elif not parsed_date:
                text = (f"第 {source_row} 行日期无法判断日/月顺序：{date_value}" if date_style == "ambiguous-numeric"
                        else f"第 {source_row} 行日期格式无法识别：{date_value}")
                errors.append((row_index, self.csv_fieldnames.index(date_field), text))
            else:
                date_styles.append(date_style)
            if not title:
                errors.append((row_index, self.csv_fieldnames.index(title_field), f"第 {source_row} 行 title 为空"))
            if not self._normalize_side_value(side_value):
                errors.append((row_index, self.csv_fieldnames.index(side_field), f"第 {source_row} 行 side 值无法识别：{side_value or '空'}"))
        try:
            validate_date_style(date_styles)
        except Exception as exc:
            first_active = next(
                (i for i, row in enumerate(self.csv_model_rows)
                 if self._csv_row_uid(row) not in self.csv_pending_delete_row_uids),
                0,
            )
            errors.append((first_active, self.csv_fieldnames.index(date_field), str(exc)))
        return sorted(errors, key=lambda item: (item[0], item[1]))

    def _clear_csv_validation_state(self):
        for overlay in getattr(self, "csv_validation_error_overlays", []):
            try: overlay.destroy()
            except tk.TclError: pass
        self.csv_validation_error_overlays = []
        self.csv_validation_errors = []
        self.csv_validation_guidance_active = False

    def _refresh_csv_validation_overlays(self):
        for overlay in getattr(self, "csv_validation_error_overlays", []):
            try: overlay.destroy()
            except tk.TclError: pass
        self.csv_validation_error_overlays = []
        edit_target = getattr(self, "csv_cell_edit_target", None)
        for row_index, column_index, _message in getattr(self, "csv_validation_errors", []):
            row_id = f"row{row_index}"
            if edit_target == (row_id, column_index):
                continue
            bbox = self.csv_editor.bbox(row_id, f"#{column_index + 1}")
            if not bbox:
                continue
            x, y, width, height = bbox
            field = self.csv_fieldnames[column_index]
            text = str(self.csv_model_rows[row_index].get(field, ""))
            label = tk.Label(
                self.csv_editor, text=text, anchor="w", padx=3,
                bg="#ffb3b3", bd=2, relief="solid", font=("Consolas", 10),
            )
            label.place(x=x, y=y, width=width, height=height)
            label.bind(
                "<Button-1>",
                lambda _event, rid=row_id, col=column_index: self._begin_csv_cell_edit(rid, f"#{col + 1}"),
            )
            self.csv_validation_error_overlays.append(label)

    def _start_csv_validation_guidance(self, errors):
        self._clear_csv_validation_state()
        self.csv_validation_errors = list(errors)
        self.csv_validation_guidance_active = True
        self._refresh_csv_validation_overlays()

        # 这里必须暂时挂起全局“未处理错误”点击守卫。
        # 否则用户点击“应用修改”触发本弹窗后，同一次鼠标事件还会继续冒泡到
        # bind_all，紧接着又弹“CSV 数据尚未处理完”，破坏连续引导。
        self._csv_validation_guard_suspended = True
        preview = "\n".join(error[2] for error in errors[:12])
        if len(errors) > 12:
            preview += f"\n……另有 {len(errors) - 12} 项"
        try:
            messagebox.showerror("应用失败", "本次没有正式应用任何修改。\n\n" + preview)
        finally:
            # 对话框关闭后直接进入第一个错误单元格；等本轮点击事件完全结束后
            # 再恢复守卫，避免“确认弹窗 -> 又弹警告”的连环弹框。
            self.after_idle(self._begin_csv_validation_guidance_after_dialog)

    def _begin_csv_validation_guidance_after_dialog(self):
        self._focus_next_csv_validation_error()
        self.after(120, self._resume_csv_validation_guard)

    def _resume_csv_validation_guard(self):
        self._csv_validation_guard_suspended = False

    def _focus_next_csv_validation_error(self):
        if not self.csv_validation_errors:
            self.csv_validation_guidance_active = False
            return
        row_index, column_index, _ = self.csv_validation_errors[0]
        row_id = f"row{row_index}"
        self.csv_editor.see(row_id)
        self.csv_editor.selection_set(row_id)
        self.csv_editor.focus(row_id)
        self.csv_editor.update_idletasks()

        def begin_after_scroll():
            self.csv_editor.see(row_id)
            self.csv_editor.update_idletasks()
            self._begin_csv_cell_edit(row_id, f"#{column_index + 1}")
            self.after_idle(self._reposition_csv_cell_editor)
            self.after(25, self._reposition_csv_cell_editor)

        self.after_idle(begin_after_scroll)

    def _mark_csv_validation_location_processed(self, row_index, column_index):
        before = len(getattr(self, "csv_validation_errors", []))
        self.csv_validation_errors = [item for item in self.csv_validation_errors
                                      if not (item[0] == row_index and item[1] == column_index)]
        if len(self.csv_validation_errors) != before:
            self._refresh_csv_validation_overlays()
            if not self.csv_validation_errors:
                self.csv_validation_guidance_active = False

    def _on_csv_editor_return(self, _event=None):
        target = getattr(self, "csv_cell_edit_target", None)
        was_guided = bool(getattr(self, "csv_validation_guidance_active", False) and target)
        self._close_csv_cell_editor(commit=True)
        if was_guided and self.csv_validation_errors:
            self.after_idle(self._focus_next_csv_validation_error)
        elif not self.csv_validation_errors:
            self.csv_validation_guidance_active = False
        return "break"

    def _install_csv_validation_guard(self):
        if getattr(self, "csv_validation_guard_installed", False):
            return
        self.csv_validation_guard_installed = True
        self.bind_all("<Button-1>", self._guard_unresolved_csv_errors, add="+")

    def _is_csv_widget(self, widget):
        current = widget
        while current is not None:
            if current in {getattr(self, "csv_editor", None), getattr(self, "csv_row_numbers", None)}:
                return True
            try:
                parent = current.nametowidget(current.winfo_parent())
            except (tk.TclError, KeyError):
                break
            if parent is current:
                break
            current = parent
        return False

    def _guard_unresolved_csv_errors(self, event):
        if getattr(self, "_csv_validation_guard_suspended", False):
            return

        if not getattr(self, "csv_validation_errors", []):
            self.csv_validation_guidance_active = False
            return

        # “应用修改”和“删除所选行 / 列”是错误状态下仍允许执行的动作。
        # 图标按钮没有 text，所以由 UI 给它们打显式 bypass 标记。
        if getattr(event.widget, "_csv_validation_guard_bypass", False):
            return

        # 滚动条与滚轮完全同类：只改变视窗，不属于“离开 CSV 编辑区”。
        try:
            if (
                isinstance(event.widget, (tk.Scrollbar, ttk.Scrollbar))
                or getattr(event.widget, "_is_timeline_scrollbar", False)
            ):
                return
        except (tk.TclError, AttributeError):
            pass

        # “应用修改”始终具有最高优先级：先让当前编辑值提交到草稿，
        # 随后由按钮自身执行完整 Apply / 全表重新校验。
        try:
            if str(event.widget.cget("text")).strip() == "应用修改":
                return
        except (tk.TclError, AttributeError):
            pass

        if self._is_csv_widget(event.widget):
            # 用户主动点击表格内部即中断自动连续引导，但错误高亮仍保留。
            self.csv_validation_guidance_active = False
            return
        messagebox.showwarning("CSV 数据尚未处理完", "CSV 编辑区仍有未处理的不合法单元格，请先处理完这些位置。")
        self.csv_validation_guidance_active = True
        self.after_idle(self._focus_next_csv_validation_error)
        return "break"

    def _reconcile_category_side_on_apply(self):
        category_field, side_field = self._csv_category_field(), self._csv_side_field()
        old_states = dict(getattr(self, "category_side_states", {}))
        old_counts = {}
        for row in self.rows:
            old_counts.setdefault(row["category"], {"top": 0, "bottom": 0})[row["side"]] += 1

        working = [dict(row) for row in self.csv_model_rows]
        new_counts = {}
        for row in working:
            category = str(row.get(category_field, "")).strip() or "未分类"
            side = self._normalize_side_value(row.get(side_field, ""))
            new_counts.setdefault(category, {"top": 0, "bottom": 0})[side] += 1

        new_states = dict(old_states)
        for category, counts in new_counts.items():
            state = old_states.get(category)
            if state is None:
                state = "top" if counts["top"] and not counts["bottom"] else "bottom" if counts["bottom"] and not counts["top"] else "unrestricted"
                new_states[category] = state
                continue
            opposite = "bottom" if state == "top" else "top"

            # 单侧分类应用后若已经完全位于另一侧，就只是“换侧”，
            # 并没有同时包含上下两侧事件，因此不应弹“改为无限制”的冲突框。
            if (
                state in {"top", "bottom"}
                and counts[opposite]
                and not counts[state]
            ):
                new_states[category] = opposite
                continue

            if state in {"top", "bottom"} and counts[opposite]:
                conflict_indices = [
                    index for index, row in enumerate(working)
                    if (str(row.get(category_field, "")).strip() or "未分类") == category
                    and self._normalize_side_value(row.get(side_field, "")) == opposite
                ]
                conflict_index = conflict_indices[0]
                conflict_row = working[conflict_index]
                title_field = self._csv_field_name("title")
                event_title = str(conflict_row.get(title_field, "")).strip()
                source_row = conflict_index + 1
                state_label = "上侧" if state == "top" else "下侧"
                opposite_label = "下侧" if opposite == "bottom" else "上侧"

                # 若这是同一分类中既有事件的 side 修改，“否”表示原 side 保持不变；
                # 若事件是新增或从其他分类移入，则“否”表示遵循目标分类的 side。
                old_row = self.rows[conflict_index] if conflict_index < len(self.rows) else None
                same_existing_event = bool(
                    old_row
                    and old_row.get("category") == category
                    and old_row.get("side") == state
                )
                if same_existing_event:
                    no_text = (
                        f"否：分类“{category}”的 side 保持{state_label}；"
                        f"第 {source_row} 行事件“{event_title}”的 side 保持{state_label}不变。"
                    )
                else:
                    no_text = (
                        f"否：分类“{category}”的 side 保持{state_label}；"
                        f"第 {source_row} 行事件“{event_title}”的 side "
                        f"遵循分类“{category}”的 side，设为{state_label}。"
                    )

                answer = messagebox.askyesno(
                    "分类 side 冲突",
                    f"分类“{category}”当前 side 为{state_label}。"
                    f"若要使分类“{category}”同时包含{state_label}和{opposite_label}事件，"
                    "需要将该分类的 side 改为“无限制”。是否更改？\n\n"
                    f"是：分类“{category}”的 side 从{state_label}改为“无限制”；"
                    f"第 {source_row} 行事件“{event_title}”的 side 为{opposite_label}，"
                    "分类内其它事件保留原 side。\n"
                    + no_text,
                )
                if answer:
                    new_states[category] = "unrestricted"
                else:
                    for row in working:
                        row_category = str(row.get(category_field, "")).strip() or "未分类"
                        if row_category == category and self._normalize_side_value(row.get(side_field, "")) != state:
                            row[side_field] = self._side_display_for_semantic(state, row.get(side_field, ""))
                    counts[opposite] = 0
                    counts[state] = sum(
                        1 for row in working
                        if (str(row.get(category_field, "")).strip() or "未分类") == category
                    )

        # 原本无限制且某一侧由“有事件”变为 0：只询问是否收紧，不静默改变。
        for category, state in old_states.items():
            if state != "unrestricted" or category not in new_counts:
                continue
            before = old_counts.get(category, {"top": 0, "bottom": 0})
            after = new_counts[category]
            remaining = None
            if before["top"] and before["bottom"]:
                if after["top"] and not after["bottom"]:
                    remaining = "top"
                elif after["bottom"] and not after["top"]:
                    remaining = "bottom"
            if remaining:
                tighten = messagebox.askyesno(
                    "分类 side 状态",
                    f"分类“{category}”的{'下侧' if remaining == 'top' else '上侧'}现在已经没有事件。\n"
                    f"是否将分类 side 设为“{'上侧' if remaining == 'top' else '下侧'}”？\n\n"
                    "选择“否”将继续保持“无限制”。",
                )
                new_states[category] = remaining if tighten else "unrestricted"

        # 把 reconciliation 后的显示值同步回草稿，保证“表格显示什么就导出什么”。
        self.csv_model_rows = working
        self._render_csv_grid()
        return self._csv_model_as_raw_rows(), new_states

    def _csv_model_as_raw_rows(self):
        raw_rows = []
        for row_index, model_row in enumerate(self.csv_model_rows, start=2):
            raw = {
                field: model_row.get(field, "")
                for field in self.csv_fieldnames
            }
            raw["__source_row__"] = str(row_index)
            raw_rows.append(raw)
        return raw_rows

    def _validate_csv_model_headers(self):
        self._ensure_csv_selection_state()
        active_fields = [
            name for name in self.csv_fieldnames
            if name not in self.csv_pending_delete_fields
        ]
        normalized = [
            str(name).strip().lstrip("\ufeff").lower()
            for name in active_fields
        ]

        duplicates = sorted({
            name for name in normalized
            if name and normalized.count(name) > 1
        })
        if duplicates:
            raise ValueError("表头字段重复：" + "、".join(duplicates))

        missing = sorted({"date", "title", "side"} - set(normalized))
        if not ({"category", "group"} & set(normalized)):
            missing.append("category/group")
        if missing:
            raise ValueError("CSV 缺少必要表头：" + "、".join(missing))
