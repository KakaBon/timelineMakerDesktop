"""TimelineSearchMixin：按功能拆分自原始桌面时间轴工具。"""

import tkinter as tk

from .utils import parse_date


class TimelineSearchMixin:
    def execute_timeline_search(self):
        query = self.timeline_search_var.get().strip()

        if not query:
            self.clear_timeline_search()
            self.status_var.set("请输入事件搜索关键词")
            return

        normalized_query = query.casefold()
        self.timeline_search_query = query
        self.timeline_search_matches = [
            row
            for row in self.rows
            if normalized_query in self.timeline_searchable_text(row)
        ]
        self.timeline_search_index = -1
        self.selected_event_id = None
        self.update_timeline_search_counter()

        if not self.timeline_search_matches:
            self.render()
            self.status_var.set("没有找到匹配的时间轴事件")
            return

        self.show_timeline_search_match(0)

    def timeline_searchable_text(self, row):
        ignored_keys = {
            "category",
            "group",
            "side",
            "_id",
            "_level",
            "_x",
            "_box_width",
        }

        values = []
        for key, value in row.items():
            if key in ignored_keys or key.startswith("_"):
                continue

            text = str(value).strip()
            if text:
                values.append(text.casefold())

        return "\n".join(values)

    def show_next_timeline_search_match(self):
        if not self.timeline_search_matches:
            self.execute_timeline_search()
            return

        self.show_timeline_search_match(self.timeline_search_index + 1)

    def show_previous_timeline_search_match(self):
        if not self.timeline_search_matches:
            self.execute_timeline_search()
            return

        self.show_timeline_search_match(self.timeline_search_index - 1)

    def show_timeline_search_match(self, index):
        if not self.timeline_search_matches:
            return

        self.timeline_search_index = index % len(self.timeline_search_matches)
        item = self.timeline_search_matches[self.timeline_search_index]

        category = item["category"]
        if category in self.hidden_categories:
            self.hidden_categories.discard(category)
            variable = self.category_vars.get(category)
            if variable is not None:
                variable.set(True)

        target_date = parse_date(item["date"])
        if target_date is None:
            self.status_var.set("匹配事件的日期无效，无法定位")
            return

        current_span = self.view_end - self.view_start
        half_span = current_span / 2
        self.view_start = target_date - half_span
        self.view_end = target_date + half_span
        self.selected_event_id = item["_id"]

        self.sync_range_entries()
        self.update_timeline_search_counter()
        self.render()
        self.after_idle(lambda: self.scroll_selected_event_into_view(item["_id"]))

        self.status_var.set(
            f"已定位匹配结果 "
            f"{self.timeline_search_index + 1} / {len(self.timeline_search_matches)}"
        )

    def scroll_selected_event_into_view(self, item_id):
        self.update_idletasks()
        bounds = self.canvas.bbox(f"item_{item_id}")
        if not bounds:
            return

        scroll_region = self.canvas.bbox("all")
        if not scroll_region:
            return

        content_height = max(1, scroll_region[3] - scroll_region[1])
        viewport_height = max(1, self.canvas.winfo_height())
        item_center = (bounds[1] + bounds[3]) / 2
        target_top = item_center - viewport_height / 2
        max_top = max(0, content_height - viewport_height)
        target_top = max(0, min(target_top, max_top))

        self.canvas.yview_moveto(target_top / content_height)

    def clear_timeline_search(self):
        self.timeline_search_var.set("")
        self.timeline_search_query = ""
        self.timeline_search_matches = []
        self.timeline_search_index = -1
        self.selected_event_id = None
        self.update_timeline_search_counter()
        self.render()
        self.timeline_search_entry.focus_set()

    def update_timeline_search_counter(self):
        current = (
            self.timeline_search_index + 1
            if self.timeline_search_index >= 0
            else 0
        )
        self.timeline_search_counter_var.set(
            f"{current}/{len(self.timeline_search_matches)}"
        )
