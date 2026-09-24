"""CSV 应用、导出、关闭确认与正式数据载入。"""

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


class CSVApplyMixin:
    @staticmethod
    def _migration_structure_signature(rows, raw=False):
        """Return the event structure that matters to migration controls.

        side/note/platform changes do not affect the source/event/target controls,
        while row order, date, title or category changes do.
        """
        result = []
        for row in rows:
            category = str(row.get("category", "") or row.get("group", "")).strip() or "未分类"
            result.append((
                str(row.get("date", "")).strip(),
                str(row.get("title", "")).strip(),
                category,
            ))
        return tuple(result)

    def apply_csv_editor_changes(self):
        """直接校验内存表格模型并应用到时间轴，不经过 CSV 文本。"""
        self._close_csv_cell_editor(commit=True)

        if not self.csv_fieldnames:
            messagebox.showwarning("无法应用", "CSV 编辑区没有内容。")
            return

        history_before = None
        rollback_snapshot = None
        try:
            self._validate_csv_model_headers()
            errors = self._collect_csv_model_validation_errors()
            if errors:
                self._start_csv_validation_guidance(errors)
                return

            rollback_snapshot = (
                self._capture_global_snapshot()
                if hasattr(self, "_capture_global_snapshot") else None
            )
            history_before = (
                self._capture_csv_apply_history_snapshot()
                if hasattr(self, "_capture_csv_apply_history_snapshot")
                else rollback_snapshot
            )

            deleted_rows, deleted_fields = self._materialize_csv_pending_deletions()
            reconciled = self._reconcile_category_side_on_apply()
            if reconciled is None:
                self.status_var.set("已取消应用 CSV 修改")
                return

            raw_rows, new_states = reconciled
            migration_structure_changed = (
                self._migration_structure_signature(getattr(self, "rows", []))
                != self._migration_structure_signature(raw_rows, raw=True)
            )

            # 分类是独立于事件存在的对象：已有分类即使因为本次应用失去
            # 最后一个事件，也必须继续作为 0 事件分类保留，直到用户明确删除。
            old_categories = list(getattr(self, "categories", []))
            old_colors = dict(getattr(self, "category_colors", {}))
            old_hidden = set(getattr(self, "hidden_categories", set()))

            if not raw_rows:
                self.rows = []
                self.categories = ["未分类"] + [
                    category for category in old_categories if category != "未分类"
                ]
                self.category_side_states = {
                    category: getattr(self, "category_side_states", {}).get(category, "unrestricted")
                    for category in self.categories
                }
                self.category_side_states["未分类"] = "unrestricted"
                self.category_colors = {
                    category: old_colors.get(category, PALETTE[index % len(PALETTE)])
                    for index, category in enumerate(self.categories)
                }
                self.hidden_categories = old_hidden.intersection(self.categories)
                self.timeline_search_matches = []
                self.timeline_search_index = -1
                self.timeline_search_query = ""
                self.selected_event_id = None
                self.update_timeline_search_counter()
                self.render_legend()
                self.render()
                self._clear_csv_validation_state()
                self.has_unexported_csv_edits = True
                self.status_var.set("已应用 CSV 编辑区修改；当前没有事件")
                if hasattr(self, "_commit_global_history"):
                    committed = self._commit_global_history(
                        history_before,
                        "应用 CSV 修改",
                        clear_csv_local_history=True,
                    )
                    if not committed and history_before is not None:
                        self.has_unexported_csv_edits = bool(
                            history_before.get("has_unexported_csv_edits", False)
                        )
                # “应用修改”本身就是 CSV 草稿边界。即使净结果与正式数据
                # 相同，也结束这一轮局部撤销历史，不把旧草稿步骤留到应用后。
                self.csv_local_undo_stack = []
                self.csv_local_redo_stack = []
                if hasattr(self, "_mark_csv_committed_state"):
                    self._mark_csv_committed_state()
                return

            self.load_rows(
                raw_rows,
                "已应用 CSV 编辑区修改",
                csv_text=None,
                csv_format=self.current_csv_format,
                csv_fieldnames=self.csv_fieldnames,
                update_csv_model=False,
                category_side_states=new_states,
                refresh_legend=False,
                refresh_timeline=False,
                reset_migration_plan=migration_structure_changed,
            )

            # 已有分类保持原顺序。即使失去最后一个事件，也只变为 0，
            # 不移动到分类列表底部；真正新出现的分类才按首次出现顺序追加。
            event_categories = [
                category for category in self.categories
                if category != "未分类"
            ]
            preserved_existing = [
                category for category in old_categories
                if category != "未分类"
            ]
            newly_seen = [
                category for category in event_categories
                if category not in preserved_existing
            ]
            self.categories = ["未分类"] + preserved_existing + newly_seen

            # 保留已有分类的 side / 颜色 / 显示状态；新分类沿用本次应用算出的状态。
            for category in preserved_existing:
                if category not in self.category_side_states:
                    self.category_side_states[category] = new_states.get(
                        category, "unrestricted"
                    )
            self.category_side_states["未分类"] = "unrestricted"

            rebuilt_colors = {}
            for index, category in enumerate(self.categories):
                rebuilt_colors[category] = old_colors.get(
                    category,
                    self.category_colors.get(
                        category, PALETTE[index % len(PALETTE)]
                    ),
                )
            self.category_colors = rebuilt_colors
            self.hidden_categories = old_hidden.intersection(self.categories)

            # CSV 应用可能改变分类的 side 状态。必须完整重绘分类控制区，
            # 不能只刷新事件数，否则三联 side 控件会继续显示旧高亮。
            self.render_legend()
            self.render()
            self._clear_csv_validation_state()
            self.has_unexported_csv_edits = True
            if hasattr(self, "_commit_global_history"):
                committed = self._commit_global_history(
                    history_before,
                    "应用 CSV 修改",
                    clear_csv_local_history=True,
                )
                if not committed and history_before is not None:
                    self.has_unexported_csv_edits = bool(
                        history_before.get("has_unexported_csv_edits", False)
                    )
            self.csv_local_undo_stack = []
            self.csv_local_redo_stack = []
            if hasattr(self, "_mark_csv_committed_state"):
                self._mark_csv_committed_state()
        except Exception as exc:
            # Apply 中途若发生异常，不留下半应用状态；这里必须恢复用户
            # 点击“应用修改”那一刻的草稿，而不是全局撤销使用的旧基线。
            if rollback_snapshot is not None and hasattr(self, "_restore_global_snapshot"):
                try:
                    self._restore_global_snapshot(rollback_snapshot)
                except Exception:
                    pass
            messagebox.showerror("应用失败", str(exc))

    def export_csv(self):
        """仅在导出时，把当前表格模型转换为 CSV 文本并写入文件。"""
        self._close_csv_cell_editor(commit=True)

        if not self.csv_fieldnames:
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
            self._validate_csv_model_headers()
            export_text = serialize_csv_model(
                self.csv_fieldnames,
                self.csv_model_rows,
                self.current_csv_format,
            )
            with Path(path).open(
                "w",
                encoding=self.current_csv_format.encoding,
                newline="",
            ) as export_file:
                export_file.write(export_text)
            self.has_unexported_csv_edits = False
            exported_path = str(Path(path))
            exported_name = Path(path).name
            self.status_var.set(f"已导出 CSV：{exported_path}")
            messagebox.showinfo(
                "导出完成",
                f"CSV 导出成功。\n\n文件：{exported_path}",
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

    def load_rows(
        self,
        raw_rows,
        message,
        csv_text=None,
        csv_format=None,
        csv_fieldnames=None,
        update_csv_model=True,
        category_side_states=None,
        refresh_legend=True,
        refresh_timeline=None,
        reset_migration_plan=True,
    ):
        if refresh_timeline is None:
            # 结构性调用通常会在补回空分类/颜色等状态后统一重绘。
            # 因此 refresh_legend=False 时默认也暂缓时间轴重绘，避免同一次
            # 操作先画一次半成品、随后又画一次最终状态造成闪烁。
            refresh_timeline = bool(refresh_legend)

        normalized = []
        date_styles = []
        errors = []

        for fallback_index, row in enumerate(raw_rows, start=2):
            source_row = int(row.get("__source_row__", fallback_index))
            cleaned = {
                str(key).strip().lower(): ("" if value is None else str(value).strip())
                for key, value in row.items()
                if key is not None and key != "__source_row__"
            }
            if not cleaned or not any(cleaned.values()):
                continue

            date_value = cleaned.get("date", "")
            title = cleaned.get("title", "")
            category = cleaned.get("category", "") or cleaned.get("group", "")
            side_value = cleaned.get("side", "").strip().casefold()

            parsed_date, date_style = parse_flexible_date(date_value)
            if not date_value:
                errors.append(f"第 {source_row} 行 date 为空")
            elif not parsed_date:
                if date_style == "ambiguous-numeric":
                    errors.append(f"第 {source_row} 行日期无法判断日/月顺序：{date_value}")
                else:
                    errors.append(f"第 {source_row} 行日期格式无法识别：{date_value}")
            else:
                date_styles.append(date_style)

            if not title:
                errors.append(f"第 {source_row} 行 title 为空")

            side_map = {
                "top": "top", "上": "top", "上侧": "top", "上方": "top",
                "bottom": "bottom", "下": "bottom", "下侧": "bottom", "下方": "bottom",
            }
            side = side_map.get(side_value)
            if not side:
                errors.append(f"第 {source_row} 行 side 必须为 top/bottom 或 上/下")

            if errors and any(item.startswith(f"第 {source_row} 行") for item in errors):
                continue

            cleaned["date"] = date_value
            cleaned["title"] = title
            cleaned["category"] = category or "未分类"
            cleaned["side"] = side
            cleaned["_id"] = len(normalized) + 1
            cleaned["_source_row"] = source_row
            normalized.append(cleaned)

        if errors:
            preview = "\n".join(errors[:12])
            if len(errors) > 12:
                preview += f"\n……另有 {len(errors) - 12} 项"
            raise ValueError(preview)

        validate_date_style(date_styles)

        if not normalized:
            raise ValueError("没有读到有效事件。每条事件至少需要 date、title 和 side。")

        self.rows = normalized

        if csv_format is not None:
            self.current_csv_format = csv_format

        if update_csv_model and csv_fieldnames is not None:
            self.set_csv_editor_model(csv_fieldnames, raw_rows)
            self.current_csv_text = csv_text or ""

        # “未分类”是固定系统分类：即使当前事件数为 0 也必须存在并永久置顶。
        event_categories = list(dict.fromkeys(row["category"] for row in self.rows))
        self.categories = ["未分类"] + [
            name for name in event_categories if name != "未分类"
        ]
        if category_side_states is None:
            self.category_side_states = self._derive_category_side_states(self.rows)
        else:
            self.category_side_states = dict(category_side_states)
        self.category_side_states["未分类"] = "unrestricted"
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
        if refresh_legend:
            self.render_legend()
        if refresh_timeline:
            self.render()
        if reset_migration_plan and hasattr(self, "reset_event_migration_plan"):
            self.reset_event_migration_plan()
        self.status_var.set(f"{message}，共 {len(self.rows)} 个事件")
