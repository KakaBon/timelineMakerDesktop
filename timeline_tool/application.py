"""主窗口：只负责应用状态初始化和组合各功能模块。"""

import copy
import tkinter as tk
from datetime import datetime
from pathlib import Path

from .csv_manager import CSVManagerMixin
from .csv_document import (
    CsvFormat,
    get_current_numeric_date_style_hint,
    set_current_numeric_date_style_hint,
)
from .exporters import ExportMixin
from .legend import LegendMixin
from .search import TimelineSearchMixin
from .timeline import TimelineMixin
from .ui import UIMixin
from .utils import resource_path


class TimelineApp(
    UIMixin,
    CSVManagerMixin,
    LegendMixin,
    TimelineSearchMixin,
    TimelineMixin,
    ExportMixin,
    tk.Tk,
):
    def __init__(self):
        super().__init__()
        self.title("时间轴制作工具")

        try:
            self.iconbitmap(
                str(resource_path("assets/images/icon.ico"))
            )
        except tk.TclError:
            pass

        self.geometry("1500x900")
        self.minsize(1050, 700)

        # 数据与分类状态
        self.rows = []
        self.categories = ["未分类"]
        self.category_colors = {}
        self.category_vars = {}
        self.hidden_categories = set()

        # 当前时间范围
        self.view_start = datetime(2013, 1, 1)
        self.view_end = datetime(2028, 1, 1)

        # 时间轴布局参数
        self.label_column_width = 118
        self.clip_start = 126
        self.plot_start = 136
        self.right_margin = 42
        self.top_margin = 70
        self.bottom_margin = 70
        self.axis_gap = 45
        self.box_height = 46
        self.item_gap = 12
        self.lane_gap = 26

        # 画布交互与悬浮提示状态
        self.drag_start_x = None
        self.drag_start_view = None
        self.tooltip = None
        self.help_tooltip = None
        self.last_layout = None

        # 时间轴搜索状态
        self.timeline_search_matches = []
        self.timeline_search_index = -1
        self.timeline_search_query = ""
        self.selected_event_id = None

        # 当前 CSV 与导出状态
        self.current_csv_text = ""
        self.current_csv_format = CsvFormat()
        self.current_numeric_date_style_hint = None
        self.current_csv_name = "test-data.csv"
        self.current_csv_directory = Path.cwd()
        self.has_unexported_csv_edits = False

        # CSV 编辑区搜索状态
        self.csv_text_search_matches = []
        self.csv_text_search_index = -1
        self.csv_text_search_query = ""
        self.csv_fieldnames = []
        self.csv_model_rows = []
        self.csv_cell_editor = None
        self.csv_cell_edit_target = None
        self.csv_active_column = 0
        self.csv_search_overlay = None
        self.csv_hover_tooltip = None
        self.csv_hover_target = None
        self.csv_local_undo_stack = []
        self.csv_local_redo_stack = []
        self.csv_local_history_suspended = False
        self.category_side_states = {"未分类": "unrestricted"}
        self.selected_categories = set()
        self.csv_side_display_mode = "zh"
        self.csv_side_display_values = ("上侧", "下侧")
        self.csv_validation_errors = []
        self.csv_validation_guidance_active = False
        self.csv_validation_error_overlays = []
        self.csv_validation_guard_installed = False

        # 全局正式数据历史：只记录已经正式作用到数据上的操作。
        # CSV 表格尚未“应用修改”的编辑继续由 CSV 自己的局部历史负责。
        self.global_undo_stack = []
        self.global_redo_stack = []
        self.global_history_suspended = False
        self.global_history_limit = 100

        # CSV 草稿与正式数据的边界：
        # - csv_committed_snapshot 始终表示最近一次已经正式生效的 CSV 状态；
        # - csv_local_undo_stack / redo_stack 只负责尚未应用的草稿。
        # 两套历史完全独立，不再互相“下沉”或串联。
        self.csv_committed_snapshot = None

        self._build_ui()

        # 撤销 / 重做采用“最近一次鼠标点击区域”分流：
        # - 最近一次左键点击发生在 CSV 区：Ctrl+Z / Ctrl+Y 只操作 CSV 未应用草稿；
        # - 最近一次左键点击发生在 CSV 区外：Ctrl+Z / Ctrl+Y 只操作全局正式历史。
        # 键盘焦点变化本身绝不改变这个上下文。
        self.undo_context = "global"
        self.bind_all("<ButtonPress-1>", self.update_undo_context_from_event, add="+")
        self.bind_all("<Control-z>", self.handle_contextual_undo_shortcut, add="+")
        self.bind_all("<Control-y>", self.handle_contextual_redo_shortcut, add="+")

        self.protocol("WM_DELETE_WINDOW", self.on_close_request)
        self.load_sample()

    # ── 全局正式数据撤销 / 重做 ────────────────────────────────
    def _snapshot_event_migration_rules(self):
        rules = []
        for rule in getattr(self, "event_migration_rules", []):
            remembered = {}
            for source, selected in rule.get("selections_by_source", {}).items():
                remembered[str(source)] = set(selected)
            rules.append({
                "source": str(rule.get("source", "")),
                "target": str(rule.get("target", "")),
                "selections_by_source": remembered,
            })
        if not rules and hasattr(self, "_new_event_migration_rule"):
            rules = [self._new_event_migration_rule()]
        return rules

    def _capture_global_snapshot(self, use_committed_csv=False):
        """捕获正式数据状态。

        use_committed_csv=True 时，CSV 部分使用最近正式版本而不是当前未应用草稿，
        用于全局撤销 / 重做在存在 CSV 草稿时仍保持两套历史独立。
        """
        if hasattr(self, "_ensure_csv_selection_state"):
            self._ensure_csv_selection_state()

        snapshot = {
            "rows": copy.deepcopy(getattr(self, "rows", [])),
            "categories": list(getattr(self, "categories", ["未分类"])),
            "category_side_states": dict(getattr(self, "category_side_states", {})),
            "category_colors": dict(getattr(self, "category_colors", {})),
            "hidden_categories": set(getattr(self, "hidden_categories", set())),
            "selected_categories": set(getattr(self, "selected_categories", set())),
            "csv_fieldnames": list(getattr(self, "csv_fieldnames", [])),
            "csv_model_rows": copy.deepcopy(getattr(self, "csv_model_rows", [])),
            "csv_pending_delete_row_uids": set(getattr(self, "csv_pending_delete_row_uids", set())),
            "csv_pending_delete_fields": set(getattr(self, "csv_pending_delete_fields", set())),
            "csv_selected_row_uids": set(getattr(self, "csv_selected_row_uids", set())),
            "csv_selected_fields": set(getattr(self, "csv_selected_fields", set())),
            "csv_next_row_uid": int(getattr(self, "csv_next_row_uid", 1)),
            "csv_side_display_mode": getattr(self, "csv_side_display_mode", "zh"),
            "csv_side_display_values": tuple(getattr(self, "csv_side_display_values", ("上侧", "下侧"))),
            "current_csv_text": getattr(self, "current_csv_text", ""),
            "current_csv_format": copy.deepcopy(getattr(self, "current_csv_format", CsvFormat())),
            "current_numeric_date_style_hint": get_current_numeric_date_style_hint(),
            "has_unexported_csv_edits": bool(getattr(self, "has_unexported_csv_edits", False)),
            "event_migration_rules": self._snapshot_event_migration_rules(),
        }
        if use_committed_csv and getattr(self, "csv_committed_snapshot", None) is not None:
            committed = self.csv_committed_snapshot
            snapshot["csv_fieldnames"] = list(committed[0])
            snapshot["csv_model_rows"] = copy.deepcopy(committed[1])
            snapshot["csv_pending_delete_row_uids"] = set(committed[2]) if len(committed) > 2 else set()
            snapshot["csv_pending_delete_fields"] = set(committed[3]) if len(committed) > 3 else set()
            snapshot["csv_selected_row_uids"] = set()
            snapshot["csv_selected_fields"] = set()
            snapshot["csv_next_row_uid"] = max(
                [int(row.get("__csv_uid__", 0) or 0) for row in snapshot["csv_model_rows"]],
                default=0,
            ) + 1
        return snapshot

    def _capture_csv_apply_history_snapshot(self):
        """捕获一次“应用修改”之前的正式状态。

        这里绝不能从 CSV 局部撤销栈推导全局历史。局部历史只描述
        “当前草稿怎么一步步编辑过来”，而全局历史描述“正式数据从哪
        个版本应用到哪个版本”。二者必须各管各的。

        因此，全局 before 快照中的 CSV 部分直接取最近一次已经正式
        生效的 ``csv_committed_snapshot``。这样无论草稿经历过排序、
        改 side、增删行列多少步，一次“应用修改”在全局层面始终只是
        一个完整版本切换。
        """
        snapshot = self._capture_global_snapshot()
        committed = getattr(self, "csv_committed_snapshot", None)
        if committed is None:
            return snapshot

        snapshot["csv_fieldnames"] = list(committed[0])
        snapshot["csv_model_rows"] = copy.deepcopy(committed[1])
        snapshot["csv_pending_delete_row_uids"] = (
            set(committed[2]) if len(committed) > 2 else set()
        )
        snapshot["csv_pending_delete_fields"] = (
            set(committed[3]) if len(committed) > 3 else set()
        )
        snapshot["csv_selected_row_uids"] = set()
        snapshot["csv_selected_fields"] = set()
        snapshot["csv_next_row_uid"] = max(
            [
                int(row.get("__csv_uid__", 0) or 0)
                for row in snapshot["csv_model_rows"]
            ],
            default=0,
        ) + 1
        return snapshot

    @staticmethod
    def _global_snapshot_data_key(snapshot):
        """只比较会改变数据/草稿内容的部分，忽略局部历史栈本身。"""
        return (
            snapshot["rows"],
            snapshot["categories"],
            snapshot["category_side_states"],
            snapshot["category_colors"],
            snapshot["csv_fieldnames"],
            snapshot["csv_model_rows"],
            snapshot["csv_pending_delete_row_uids"],
            snapshot["csv_pending_delete_fields"],
            snapshot["current_csv_text"],
            snapshot["current_csv_format"],
        )

    @staticmethod
    def _csv_snapshot_from_global_snapshot(snapshot):
        """把全局快照中的 CSV 正式版本转换为 CSV 局部快照结构。"""
        return (
            list(snapshot.get("csv_fieldnames", [])),
            copy.deepcopy(snapshot.get("csv_model_rows", [])),
            set(snapshot.get("csv_pending_delete_row_uids", set())),
            set(snapshot.get("csv_pending_delete_fields", set())),
        )

    def _rebase_csv_draft_snapshot(self, draft_snapshot, old_committed, new_committed):
        """把一份未应用 CSV 草稿重新挂到新的正式版本上。

        全局撤销 / 重做只切换“正式版本”；CSV 草稿里的未应用操作必须保留。
        但“保留草稿”不能简单地把整张旧表原封不动留着，否则正式版本里
        已经被撤销的事件属性（例如 side）会继续残留在 CSV 表格中。

        这里按稳定的 ``__csv_uid__`` 做三方合并：
        - old_committed：执行全局撤销前的正式 CSV 版本；
        - draft_snapshot：当前某个未应用草稿状态；
        - new_committed：全局撤销 / 重做后要恢复的正式 CSV 版本。

        只保留 draft_snapshot 相对 old_committed 真正做过的本地修改；
        没有被本地改过的单元格则跟随 new_committed。这样“仅排序”的草稿
        会继续保持排序顺序，但事件 side 等正式属性会同步回被撤销后的版本。
        """
        if draft_snapshot is None:
            return copy.deepcopy(new_committed)
        if old_committed is None:
            return copy.deepcopy(draft_snapshot)

        old_fields = list(old_committed[0])
        old_rows = copy.deepcopy(old_committed[1])
        draft_fields = list(draft_snapshot[0])
        draft_rows = copy.deepcopy(draft_snapshot[1])
        new_fields = list(new_committed[0])
        new_rows = copy.deepcopy(new_committed[1])

        old_map = self._csv_rows_by_uid(old_rows)
        draft_map = self._csv_rows_by_uid(draft_rows)
        new_map = self._csv_rows_by_uid(new_rows)

        old_order = [
            int(row.get("__csv_uid__", index + 1) or index + 1)
            for index, row in enumerate(old_rows)
        ]
        draft_order = [
            int(row.get("__csv_uid__", index + 1) or index + 1)
            for index, row in enumerate(draft_rows)
        ]
        new_order = [
            int(row.get("__csv_uid__", index + 1) or index + 1)
            for index, row in enumerate(new_rows)
        ]

        # 字段层面的未应用改动（新增 / 重命名）继续保留；正式版本已经
        # 不存在且草稿也没有新增出来的字段则跟随新的正式版本消失。
        local_added_fields = [field for field in draft_fields if field not in old_fields]
        result_fields = []
        for field in draft_fields:
            if field in new_fields or field in local_added_fields:
                if field not in result_fields:
                    result_fields.append(field)
        for field in new_fields:
            if field not in result_fields:
                result_fields.append(field)

        # 如果草稿只是把既有事件重新排序，就继续沿用草稿顺序；
        # 新正式版本中新出现、草稿从未见过的事件再按正式顺序补入。
        local_added_uids = [uid for uid in draft_order if uid not in old_map]
        old_projection = [uid for uid in old_order if uid in draft_map]
        draft_old_projection = [uid for uid in draft_order if uid in old_map]
        local_order_changed = (draft_old_projection != old_projection) or bool(local_added_uids)

        if local_order_changed:
            result_order = [
                uid for uid in draft_order
                if uid in new_map or uid in local_added_uids
            ]
            result_order.extend(uid for uid in new_order if uid not in result_order)
        else:
            result_order = list(new_order)
            result_order.extend(uid for uid in local_added_uids if uid not in result_order)

        result_rows = []
        for uid in result_order:
            # 草稿中新建、尚未应用的事件没有旧正式基线，完整保留。
            if uid not in old_map:
                if uid in draft_map:
                    source = copy.deepcopy(draft_map[uid])
                    row = {field: str(source.get(field, "")) for field in result_fields}
                    row["__csv_uid__"] = uid
                    result_rows.append(row)
                continue

            # 该事件在新的正式版本里已经不存在时，说明全局版本切换本身
            # 删除了它；若它不是本地新增事件，则不应继续残留在草稿中。
            if uid not in new_map:
                continue

            old_row = old_map[uid]
            draft_row = draft_map.get(uid, old_row)
            new_row = new_map[uid]
            row = {}
            for field in result_fields:
                if field in local_added_fields:
                    row[field] = str(draft_row.get(field, ""))
                    continue

                # 只有“草稿相对旧正式版本确实改过”的单元格才覆盖新正式值。
                if (
                    field in old_fields
                    and field in draft_fields
                    and str(draft_row.get(field, "")) != str(old_row.get(field, ""))
                ):
                    row[field] = str(draft_row.get(field, ""))
                else:
                    row[field] = str(new_row.get(field, ""))
            row["__csv_uid__"] = uid
            result_rows.append(row)

        result_uids = {
            int(row.get("__csv_uid__", 0) or 0) for row in result_rows
        }
        pending_rows = set(draft_snapshot[2]) if len(draft_snapshot) > 2 else set()
        pending_fields = set(draft_snapshot[3]) if len(draft_snapshot) > 3 else set()
        pending_rows.intersection_update(result_uids)
        pending_fields.intersection_update(result_fields)
        return (result_fields, result_rows, pending_rows, pending_fields)

    @staticmethod
    def _csv_rows_by_uid(rows):
        return {
            int(row.get("__csv_uid__", index + 1) or index + 1): row
            for index, row in enumerate(rows)
        }

    def _describe_global_change(self, before_snapshot, after_snapshot):
        """生成适合信息记录区的正式版本差异摘要。"""
        parts = []
        before_fields = list(before_snapshot.get("csv_fieldnames", []))
        after_fields = list(after_snapshot.get("csv_fieldnames", []))
        added_fields = [f for f in after_fields if f not in before_fields]
        removed_fields = [f for f in before_fields if f not in after_fields]
        if added_fields:
            parts.append("新增字段：" + "、".join(added_fields))
        if removed_fields:
            parts.append("删除字段：" + "、".join(removed_fields))

        before_rows = list(before_snapshot.get("csv_model_rows", []))
        after_rows = list(after_snapshot.get("csv_model_rows", []))
        before_by_uid = self._csv_rows_by_uid(before_rows)
        after_by_uid = self._csv_rows_by_uid(after_rows)
        added_uids = [uid for uid in after_by_uid if uid not in before_by_uid]
        removed_uids = [uid for uid in before_by_uid if uid not in after_by_uid]
        if added_uids:
            parts.append(f"新增 {len(added_uids)} 个事件")
        if removed_uids:
            parts.append(f"删除 {len(removed_uids)} 个事件")

        common_uids = [uid for uid in after_by_uid if uid in before_by_uid]
        changed_cells = []
        changed_fields = set()
        all_fields = list(dict.fromkeys(before_fields + after_fields))
        for uid in common_uids:
            b_row, a_row = before_by_uid[uid], after_by_uid[uid]
            for field in all_fields:
                if str(b_row.get(field, "")) != str(a_row.get(field, "")):
                    changed_cells.append((uid, field))
                    changed_fields.add(field)
        if changed_cells:
            field_text = "、".join(
                field for field in all_fields if field in changed_fields
            )
            parts.append(
                f"修改 {len(changed_cells)} 个单元格"
                + (f"（字段：{field_text}）" if field_text else "")
            )

        before_order = [
            int(row.get("__csv_uid__", i + 1) or i + 1)
            for i, row in enumerate(before_rows)
        ]
        after_order = [
            int(row.get("__csv_uid__", i + 1) or i + 1)
            for i, row in enumerate(after_rows)
        ]
        if (
            len(before_order) == len(after_order)
            and set(before_order) == set(after_order)
            and before_order != after_order
        ):
            parts.append("调整事件行顺序")

        before_sides = dict(before_snapshot.get("category_side_states", {}))
        after_sides = dict(after_snapshot.get("category_side_states", {}))
        side_changes = [
            name for name in set(before_sides) | set(after_sides)
            if before_sides.get(name) != after_sides.get(name)
        ]
        if side_changes:
            parts.append(
                "分类 side 变化："
                + "、".join(
                    f"{name} {before_sides.get(name, '—')}→{after_sides.get(name, '—')}"
                    for name in sorted(side_changes)
                )
            )

        before_count = len(before_snapshot.get("rows", []))
        after_count = len(after_snapshot.get("rows", []))
        if not parts and before_count != after_count:
            parts.append(f"事件总数 {before_count}→{after_count}")
        return "；".join(parts) or "正式数据状态发生变化"

    def _commit_global_history(self, before_snapshot, label, clear_csv_local_history=False):
        if getattr(self, "global_history_suspended", False) or before_snapshot is None:
            return False
        after_snapshot = self._capture_global_snapshot()
        if self._global_snapshot_data_key(before_snapshot) == self._global_snapshot_data_key(after_snapshot):
            return False

        detail = self._describe_global_change(before_snapshot, after_snapshot)
        self.global_undo_stack.append({
            "label": str(label),
            "detail": detail,
            "snapshot": before_snapshot,
        })
        if len(self.global_undo_stack) > self.global_history_limit:
            self.global_undo_stack.pop(0)
        self.global_redo_stack.clear()

        if clear_csv_local_history:
            # 一旦某次操作已经正式生效，CSV 草稿历史到此结束。
            # 后续 Ctrl+Z / Ctrl+Y 不能再跨过“应用修改”去碰全局历史。
            self.csv_local_undo_stack = []
            self.csv_local_redo_stack = []
            if hasattr(self, "_mark_csv_committed_state"):
                self._mark_csv_committed_state()

        self._update_global_history_buttons()
        if str(label) == "应用 CSV 修改" and hasattr(self, "status_var"):
            self.status_var.set(
                f"已应用 CSV 修改：当前正式版本共 {len(getattr(self, 'rows', []))} 个事件；{detail}"
            )
        return True

    def reset_global_history(self):
        self.global_undo_stack = []
        self.global_redo_stack = []
        self._update_global_history_buttons()

    def _update_global_history_buttons(self):
        undo = getattr(self, "undo_button", None)
        redo = getattr(self, "redo_button", None)
        if undo is not None:
            try:
                undo.configure(state="normal" if self.global_undo_stack else "disabled")
            except tk.TclError:
                pass
        if redo is not None:
            try:
                redo.configure(state="normal" if self.global_redo_stack else "disabled")
            except tk.TclError:
                pass

    def _restore_global_snapshot(self, snapshot, preserve_csv_draft=False):
        """恢复正式版本。

        preserve_csv_draft=True 时，保留的是“CSV 尚未应用的操作”，而不是把
        旧草稿整张冻结。当前草稿和它的局部撤销 / 重做历史都会相对新的正式
        版本重新基准化，使全局版本变化能同步到每个事件，同时不吞掉排序、
        单元格编辑等尚未应用操作。
        """
        rebased_draft = None
        rebased_undo_stack = None
        rebased_redo_stack = None
        target_committed = self._csv_snapshot_from_global_snapshot(snapshot)
        if preserve_csv_draft and hasattr(self, "_csv_snapshot"):
            old_committed = copy.deepcopy(getattr(self, "csv_committed_snapshot", None))
            current_draft = self._csv_snapshot()
            rebased_draft = self._rebase_csv_draft_snapshot(
                current_draft, old_committed, target_committed
            )
            rebased_undo_stack = [
                self._rebase_csv_draft_snapshot(item, old_committed, target_committed)
                for item in list(getattr(self, "csv_local_undo_stack", []))
            ]
            rebased_redo_stack = [
                self._rebase_csv_draft_snapshot(item, old_committed, target_committed)
                for item in list(getattr(self, "csv_local_redo_stack", []))
            ]

        migration_rules_before = (
            self._snapshot_event_migration_rules()
            if hasattr(self, "_snapshot_event_migration_rules") else []
        )
        target_migration_rules = copy.deepcopy(snapshot["event_migration_rules"])
        migration_plan_changed = migration_rules_before != target_migration_rules

        self.global_history_suspended = True
        try:
            if hasattr(self, "_close_csv_cell_editor"):
                self._close_csv_cell_editor(commit=True if preserve_csv_draft else False)
            if hasattr(self, "_close_migration_popup"):
                self._close_migration_popup()
            if hasattr(self, "hide_info_tooltip"):
                self.hide_info_tooltip()

            self.rows = copy.deepcopy(snapshot["rows"])
            self.categories = list(snapshot["categories"])
            self.category_side_states = dict(snapshot["category_side_states"])
            self.category_colors = dict(snapshot["category_colors"])
            self.hidden_categories = set(snapshot["hidden_categories"]).intersection(self.categories)
            self.selected_categories = set(snapshot["selected_categories"]).intersection(self.categories)
            # 迁移计划未变化时保留现有 rule 对象及其控件引用；
            # 否则如果只替换数据对象却不重建 UI，现有按钮会仍绑定旧 rule。
            if migration_plan_changed:
                self.event_migration_rules = target_migration_rules

            # 日期顺序属于正式版本语义。即使保留一份未应用 CSV 草稿，
            # 时间轴也必须按被恢复的正式版本解释歧义数字日期。
            self.current_numeric_date_style_hint = snapshot.get(
                "current_numeric_date_style_hint"
            )
            set_current_numeric_date_style_hint(
                self.current_numeric_date_style_hint
            )

            if not preserve_csv_draft:
                self.csv_fieldnames = list(snapshot["csv_fieldnames"])
                self.csv_model_rows = copy.deepcopy(snapshot["csv_model_rows"])
                self.csv_pending_delete_row_uids = set(snapshot["csv_pending_delete_row_uids"])
                self.csv_pending_delete_fields = set(snapshot["csv_pending_delete_fields"])
                self.csv_selected_row_uids = set(snapshot["csv_selected_row_uids"])
                self.csv_selected_fields = set(snapshot["csv_selected_fields"])
                self.csv_next_row_uid = int(snapshot["csv_next_row_uid"])
                self.csv_local_undo_stack = []
                self.csv_local_redo_stack = []
                self.csv_side_display_mode = snapshot["csv_side_display_mode"]
                self.csv_side_display_values = tuple(snapshot["csv_side_display_values"])
                self.current_csv_text = snapshot["current_csv_text"]
                self.current_csv_format = copy.deepcopy(snapshot["current_csv_format"])
                self.current_numeric_date_style_hint = snapshot.get(
                    "current_numeric_date_style_hint"
                )
                set_current_numeric_date_style_hint(
                    self.current_numeric_date_style_hint
                )
                self.has_unexported_csv_edits = bool(snapshot["has_unexported_csv_edits"])
                if hasattr(self, "_clear_csv_validation_state"):
                    self._clear_csv_validation_state()
                if hasattr(self, "_render_csv_grid"):
                    self._render_csv_grid()
                if hasattr(self, "_reset_csv_search_state"):
                    self._reset_csv_search_state()
            elif rebased_draft is not None:
                self.csv_fieldnames = list(rebased_draft[0])
                self.csv_model_rows = copy.deepcopy(rebased_draft[1])
                self.csv_pending_delete_row_uids = set(rebased_draft[2])
                self.csv_pending_delete_fields = set(rebased_draft[3])
                self.csv_selected_row_uids = set()
                self.csv_selected_fields = set()
                self.csv_next_row_uid = max(
                    [int(row.get("__csv_uid__", 0) or 0) for row in self.csv_model_rows],
                    default=0,
                ) + 1
                self.csv_local_undo_stack = list(rebased_undo_stack or [])
                self.csv_local_redo_stack = list(rebased_redo_stack or [])
                if hasattr(self, "_clear_csv_validation_state"):
                    self._clear_csv_validation_state()
                if hasattr(self, "_render_csv_grid"):
                    self._render_csv_grid()
                if hasattr(self, "_reset_csv_search_state"):
                    self._reset_csv_search_state()

            # 正式版本基线始终切换到本次全局撤销 / 重做所恢复的版本。
            self.csv_committed_snapshot = copy.deepcopy(target_committed)

            self.timeline_search_matches = []
            self.timeline_search_index = -1
            self.timeline_search_query = ""
            self.selected_event_id = None
            if hasattr(self, "update_timeline_search_counter"):
                self.update_timeline_search_counter()

            self.category_search_matches = []
            self.category_search_index = -1
            self.category_search_focus_category = None
            self.category_search_focus_field = None
            if hasattr(self, "_update_category_search_counter"):
                self._update_category_search_counter()

            self.render_legend()
            if migration_plan_changed and hasattr(self, "event_migration_body"):
                self._render_event_migration_plan()
            self.render()
        finally:
            self.global_history_suspended = False

    def undo_global_action(self):
        """只撤销已经正式生效的全局操作，不消费 CSV 草稿历史。"""
        if hasattr(self, "_close_csv_cell_editor"):
            self._close_csv_cell_editor(commit=True)
        if not self.global_undo_stack:
            try:
                self.bell()
            except tk.TclError:
                pass
            self.status_var.set("全局历史：没有可撤销的正式操作")
            self._update_global_history_buttons()
            return "break"

        preserve_draft = bool(
            hasattr(self, "_csv_has_unapplied_changes")
            and self._csv_has_unapplied_changes()
        )
        current = self._capture_global_snapshot(use_committed_csv=preserve_draft)
        entry = self.global_undo_stack.pop()
        self.global_redo_stack.append({
            "label": entry["label"],
            "detail": entry.get("detail", ""),
            "snapshot": current,
        })
        self._restore_global_snapshot(entry["snapshot"], preserve_csv_draft=preserve_draft)
        self._update_global_history_buttons()
        suffix = "；当前 CSV 未应用操作仍保留" if preserve_draft else ""
        detail = entry.get("detail", "")
        self.status_var.set(
            f"已撤销全局操作：{entry['label']}"
            + (f"；{detail}" if detail else "")
            + suffix
        )
        return "break"

    def redo_global_action(self):
        """只重做已经正式生效的全局操作，不消费 CSV 草稿历史。"""
        if hasattr(self, "_close_csv_cell_editor"):
            self._close_csv_cell_editor(commit=True)
        if not self.global_redo_stack:
            try:
                self.bell()
            except tk.TclError:
                pass
            self.status_var.set("全局历史：没有可重做的正式操作")
            self._update_global_history_buttons()
            return "break"

        preserve_draft = bool(
            hasattr(self, "_csv_has_unapplied_changes")
            and self._csv_has_unapplied_changes()
        )
        current = self._capture_global_snapshot(use_committed_csv=preserve_draft)
        entry = self.global_redo_stack.pop()
        self.global_undo_stack.append({
            "label": entry["label"],
            "detail": entry.get("detail", ""),
            "snapshot": current,
        })
        if len(self.global_undo_stack) > self.global_history_limit:
            self.global_undo_stack.pop(0)
        self._restore_global_snapshot(entry["snapshot"], preserve_csv_draft=preserve_draft)
        self._update_global_history_buttons()
        suffix = "；当前 CSV 未应用操作仍保留" if preserve_draft else ""
        detail = entry.get("detail", "")
        self.status_var.set(
            f"已重做全局操作：{entry['label']}"
            + (f"；{detail}" if detail else "")
            + suffix
        )
        return "break"
