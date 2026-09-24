"""事件迁移计划校验与执行。"""

import tkinter as tk
from tkinter import messagebox, ttk

from .config import PALETTE


class LegendMigrationActionsMixin:
    def _collect_event_migration_plan(self):
        plan = []
        current_categories = set(getattr(self, "categories", []))
        all_source = "所有分类"
        claimed_ids = set()

        for index, rule in enumerate(self.event_migration_rules, start=1):
            source = str(rule.get("source", "")).strip()
            target = str(rule.get("target", "")).strip()
            selected = set(
                rule.get("selections_by_source", {}).get(source, set())
            ) if source else set()
            active = bool(source or target or selected)
            if not active:
                continue
            if not source or not target:
                raise ValueError(f"第 {index} 行迁移计划需要同时选择源分类和目标分类。")
            if source != all_source and source == target:
                raise ValueError(f"第 {index} 行的源分类和目标分类不能相同。")
            if source != all_source and source not in current_categories:
                raise ValueError(f"第 {index} 行的源分类“{source}”已经不存在，请重新选择。")
            if target not in current_categories:
                raise ValueError(f"第 {index} 行的目标分类“{target}”已经不存在，请重新选择。")

            valid_ids = {
                row.get("_id")
                for row in self._migration_events_for_category(source)
            }
            selected.intersection_update(valid_ids)
            if not selected:
                raise ValueError(f"第 {index} 行还没有勾选要迁移的事件。")
            overlap = claimed_ids.intersection(selected)
            if overlap:
                raise ValueError(
                    f"第 {index} 行包含已经在前序迁移行中选择过的事件，请调整源分类或事件选择。"
                )
            claimed_ids.update(selected)
            plan.append((source, target, selected))

        return plan

    def execute_event_migration_plan(self):
        """执行当前迁移计划，并同步正式 rows、CSV 表格、分类区和时间轴。"""
        self._close_migration_popup()
        if hasattr(self, "_close_csv_cell_editor"):
            self._close_csv_cell_editor(commit=True)

        try:
            plan = self._collect_event_migration_plan()
        except ValueError as exc:
            messagebox.showwarning("事件迁移", str(exc))
            return

        if not plan:
            messagebox.showinfo("事件迁移", "请先在事件迁移区设置至少一条迁移计划。")
            return

        migration_targets = {}
        for _source, target, selected_ids in plan:
            for event_id in selected_ids:
                migration_targets[event_id] = target

        if not migration_targets:
            messagebox.showinfo("事件迁移", "当前迁移计划中没有可迁移的事件。")
            return

        history_before = (
            self._capture_global_snapshot()
            if hasattr(self, "_capture_global_snapshot") else None
        )

        category_field = self._csv_category_field()
        side_field = self._csv_side_field()
        moved = 0
        moved_source_categories = set()

        for row in self.rows:
            event_id = row.get("_id")
            target = migration_targets.get(event_id)
            if not target:
                continue

            old_category = row.get("category")
            row["category"] = target
            target_state = getattr(self, "category_side_states", {}).get(
                target, "unrestricted"
            )
            if target == "未分类":
                target_state = "unrestricted"
            if target_state in {"top", "bottom"}:
                row["side"] = target_state

            source_row = int(row.get("_source_row", event_id + 1))
            model_index = source_row - 2
            if 0 <= model_index < len(getattr(self, "csv_model_rows", [])):
                model_row = self.csv_model_rows[model_index]
                if category_field:
                    model_row[category_field] = target
                if side_field and target_state in {"top", "bottom"}:
                    old_display = model_row.get(side_field, "")
                    model_row[side_field] = self._side_display_for_semantic(
                        target_state, old_display
                    )
            if old_category != target:
                moved += 1
                moved_source_categories.add(old_category)

        if hasattr(self, "_render_csv_grid"):
            self._render_csv_grid()
        if hasattr(self, "_reset_csv_search_state"):
            self._reset_csv_search_state()
        if hasattr(self, "_clear_csv_validation_state"):
            self._clear_csv_validation_state()

        # 迁移只移动事件。空分类继续保留；删除分类仍只有分类区一个入口。
        self.render_legend()
        self.render()

        self.has_unexported_csv_edits = True
        self.event_migration_rules = [self._new_event_migration_rule()]
        self._render_event_migration_plan()

        source_count = len(moved_source_categories)
        self.status_var.set(
            f"已迁移 {moved} 个事件，涉及 {source_count} 个源分类；"
            "CSV、分类区与时间轴已同步更新"
        )
        if moved and hasattr(self, "_commit_global_history"):
            self._commit_global_history(
                history_before,
                f"事件迁移：{moved} 个事件",
                clear_csv_local_history=True,
            )
