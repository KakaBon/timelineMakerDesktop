"""TimelineMixin：按功能拆分自原始桌面时间轴工具。"""

import math
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta

from .config import DATE_FORMAT
from .utils import lighten, parse_date


class TimelineMixin:
    def _ensure_visual_scale_state(self):
        """兼容旧版 application.py：按需补齐视觉缩放状态。"""
        if not hasattr(self, "default_visual_scale"):
            self.default_visual_scale = 0.86

        if not hasattr(self, "visual_scale"):
            self.visual_scale = self.default_visual_scale

        if not hasattr(self, "_base_visual_metrics"):
            self._base_visual_metrics = {
                "top_margin": getattr(self, "top_margin", 70),
                "bottom_margin": getattr(self, "bottom_margin", 70),
                "axis_gap": getattr(self, "axis_gap", 45),
                "box_height": getattr(self, "box_height", 46),
                "item_gap": getattr(self, "item_gap", 12),
                "lane_gap": getattr(self, "lane_gap", 26),
            }

        self._update_visual_zoom_percent()

    def _update_visual_zoom_percent(self):
        """更新工具栏中的二维缩放百分比。

        默认视觉比例作为 100%，因此界面不暴露内部的 0.86 等实现值。
        """
        if not hasattr(self, "visual_zoom_percent_var"):
            return

        default_scale = getattr(self, "default_visual_scale", 0.86)
        current_scale = getattr(self, "visual_scale", default_scale)
        percent = round((current_scale / default_scale) * 100)
        self.visual_zoom_percent_var.set(f"{percent}%")

    def _apply_visual_scale_metrics(self):
        """按当前视觉比例更新事件盒、泳道与留白尺寸。"""
        self._ensure_visual_scale_state()
        base = self._base_visual_metrics
        scale = self.visual_scale
        self.top_margin = max(20, round(base["top_margin"] * scale))
        self.bottom_margin = max(20, round(base["bottom_margin"] * scale))
        self.axis_gap = max(16, round(base["axis_gap"] * scale))
        self.box_height = max(24, round(base["box_height"] * scale))
        self.item_gap = max(4, round(base["item_gap"] * scale))
        self.lane_gap = max(8, round(base["lane_gap"] * scale))

    def _scaled_font_size(self, base_size, minimum=7):
        self._ensure_visual_scale_state()
        return max(minimum, round(base_size * self.visual_scale))

    def change_visual_scale(self, factor, anchor_x=None, anchor_y=None):
        """同时缩放横向时间密度与纵向视觉尺寸，并保持锚点稳定。"""
        self._ensure_visual_scale_state()
        old_scale = self.visual_scale
        new_scale = max(0.38, min(1.35, old_scale * factor))
        if abs(new_scale - old_scale) < 0.001:
            return

        # 横向锚点默认为画布中央；滚轮调用时使用鼠标位置。
        width = self.canvas_width()
        if anchor_x is None:
            anchor_x = self.canvas.winfo_width() / 2
        anchor_x = max(self.plot_start, min(width - self.right_margin, anchor_x))
        anchor_date = self.x_to_date(anchor_x, width)

        old_span = self.view_end - self.view_start
        scale_ratio = new_scale / old_scale
        new_seconds = old_span.total_seconds() / scale_ratio
        new_seconds = max(30 * 86400, min(200 * 365 * 86400, new_seconds))
        new_span = timedelta(seconds=new_seconds)
        date_ratio = (anchor_date - self.view_start).total_seconds() / old_span.total_seconds()

        # 记录鼠标下方的纵向内容坐标。重绘后按同一比例恢复，
        # 这样视觉缩放不会突然跳到画布顶部。
        if anchor_y is None:
            anchor_y = self.canvas.winfo_height() / 2
        old_canvas_y = self.canvas.canvasy(anchor_y)

        self.visual_scale = new_scale
        self._apply_visual_scale_metrics()
        self._update_visual_zoom_percent()
        self.view_start = anchor_date - new_span * date_ratio
        self.view_end = self.view_start + new_span
        self.sync_range_entries()
        self.render()
        self.update_idletasks()

        scroll_region = self.canvas.cget("scrollregion").split()
        if len(scroll_region) == 4:
            content_height = max(1.0, float(scroll_region[3]) - float(scroll_region[1]))
            new_canvas_y = old_canvas_y * scale_ratio
            target_top = max(0.0, new_canvas_y - anchor_y)
            self.canvas.yview_moveto(min(1.0, target_top / content_height))

    def visual_zoom_in(self):
        self.change_visual_scale(1.10)

    def visual_zoom_out(self):
        self.change_visual_scale(1 / 1.10)

    def fit_to_data(self):
        dates = [parse_date(row["date"]) for row in self.rows]
        dates = [date for date in dates if date]
        if not dates:
            return

        self.view_start = min(dates) - timedelta(days=240)
        self.view_end = max(dates) + timedelta(days=240)
        self.sync_range_entries()

    def get_full_data_range(self):
        dates = [
            parse_date(row["date"])
            for row in self.visible_rows()
        ]

        dates = [date for date in dates if date]

        if not dates:
            return self.view_start, self.view_end

        start = min(dates) - timedelta(days=240)
        end = max(dates) + timedelta(days=240)

        return start, end

    def get_full_export_width(self, start, end):
        total_days = max(1, (end - start).days)
        total_years = total_days / 365.2425

        pixels_per_year = 220

        timeline_width = int(total_years * pixels_per_year)

        return max(
            self.canvas_width(),
            self.plot_start + timeline_width + self.right_margin,
        )

    def reset_view(self):
        self._ensure_visual_scale_state()
        self.hidden_categories.clear()
        self.visual_scale = self.default_visual_scale
        self._apply_visual_scale_metrics()
        self._update_visual_zoom_percent()
        self.selected_event_id = None
        self.pressed_event_id = None
        for variable in self.category_vars.values():
            variable.set(True)
        self.fit_to_data()
        self.canvas.yview_moveto(0)
        self.render()

    def sync_range_entries(self):
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, self.view_start.strftime(DATE_FORMAT))
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, self.view_end.strftime(DATE_FORMAT))

    def apply_range(self):
        start = parse_date(self.start_entry.get())
        end = parse_date(self.end_entry.get())
        if not start or not end or start >= end:
            messagebox.showwarning("日期无效", "请输入有效的起止日期，格式为 YYYY-MM-DD。")
            return

        self.view_start = start
        self.view_end = end
        self.render()

    def canvas_width(self):
        # 画布宽度始终等于当前视口宽度，不再产生横向滚动区域。
        return max(700, self.canvas.winfo_width() - 2)

    def date_to_x(self, date, width):
        total = (self.view_end - self.view_start).total_seconds()
        position = (date - self.view_start).total_seconds() / total
        return self.plot_start + position * (width - self.plot_start - self.right_margin)

    def x_to_date(self, x, width):
        usable = width - self.plot_start - self.right_margin
        ratio = (x - self.plot_start) / usable
        return self.view_start + (self.view_end - self.view_start) * ratio

    def measure_text(self, text):
        font = ("Microsoft YaHei", self._scaled_font_size(10, 6), "bold")
        test = self.canvas.create_text(-1000, -1000, text=text, font=font)
        bounds = self.canvas.bbox(test)
        self.canvas.delete(test)
        return max(52, (bounds[2] - bounds[0]) + max(12, round(22 * self.visual_scale)))

    def assign_levels(self, items, width):
        levels = []
        for item in sorted(items, key=lambda row: parse_date(row["date"])):
            x = self.date_to_x(parse_date(item["date"]), width)
            box_width = self.measure_text(item["title"])
            left = x - box_width / 2
            right = x + box_width / 2

            level = 0
            while True:
                last_right = levels[level] if level < len(levels) else -math.inf
                if left >= last_right + self.item_gap:
                    if level == len(levels):
                        levels.append(right)
                    else:
                        levels[level] = right
                    item["_level"] = level
                    item["_x"] = x
                    item["_box_width"] = box_width
                    break
                level += 1

        return max(1, len(levels))

    def calculate_layout(self, width_override=None):
        visible = self.visible_rows()
        if width_override is None:
            width = self.canvas_width()
        else:
            width = width_override

        top_categories = [
            name for name in self.categories
            if name not in self.hidden_categories
            and any(row["category"] == name and row["side"] == "top" for row in visible)
        ]
        bottom_categories = [
            name for name in self.categories
            if name not in self.hidden_categories
            and any(row["category"] == name and row["side"] == "bottom" for row in visible)
        ]

        category_layout = {}
        top_height = 0

        for name in top_categories:
            items = [row for row in visible if row["category"] == name and row["side"] == "top"]
            levels = self.assign_levels(items, width)
            lane_height = levels * (self.box_height + max(4, round(10 * self.visual_scale))) + max(12, round(34 * self.visual_scale))
            category_layout[("top", name)] = (items, lane_height)
            top_height += lane_height + self.lane_gap

        bottom_height = 0
        for name in bottom_categories:
            items = [row for row in visible if row["category"] == name and row["side"] == "bottom"]
            levels = self.assign_levels(items, width)
            lane_height = levels * (self.box_height + max(4, round(10 * self.visual_scale))) + max(12, round(34 * self.visual_scale))
            category_layout[("bottom", name)] = (items, lane_height)
            bottom_height += lane_height + self.lane_gap

        axis_y = self.top_margin + top_height + self.axis_gap
        content_height = axis_y + self.axis_gap + bottom_height + self.bottom_margin
        height = max(content_height, self.canvas.winfo_height() - 2)

        return {
            "width": width,
            "height": height,
            "axis_y": axis_y,
            "top_categories": top_categories,
            "bottom_categories": bottom_categories,
            "category_layout": category_layout,
        }

    def render(self):
        if not self.rows:
            return

        self.hide_tooltip()
        self.canvas.delete("all")

        layout = self.calculate_layout()
        self.last_layout = layout

        width = layout["width"]
        height = layout["height"]
        axis_y = layout["axis_y"]

        self.draw_time_grid(width, height, axis_y)
        self.draw_today_line(width, height, axis_y)

        # 先画所有事件与连接线。
        cursor = self.top_margin
        lane_positions = []
        for name in layout["top_categories"]:
            items, lane_height = layout["category_layout"][("top", name)]
            lane_bottom = cursor + lane_height
            self.draw_category_items(name, items, "top", cursor, lane_bottom, axis_y)
            lane_positions.append((name, cursor, lane_bottom, "top"))
            cursor = lane_bottom + self.lane_gap

        cursor = axis_y + self.axis_gap
        for name in layout["bottom_categories"]:
            items, lane_height = layout["category_layout"][("bottom", name)]
            lane_top = cursor
            lane_bottom = cursor + lane_height
            self.draw_category_items(name, items, "bottom", lane_top, lane_bottom, axis_y)
            lane_positions.append((name, lane_top, lane_bottom, "bottom"))
            cursor = lane_bottom + self.lane_gap

        self.canvas.create_line(
            self.plot_start,
            axis_y,
            width - self.right_margin,
            axis_y,
            fill="#2f3a4e",
            width=2,
        )

        # 固定标签列遮罩：任何向左平移进入标签列的事件都会在这里被遮住。
        self.canvas.create_rectangle(
            0,
            0,
            self.clip_start,
            height,
            fill="white",
            outline="",
            tags=("label_mask",),
        )
        self.canvas.create_line(
            self.clip_start,
            0,
            self.clip_start,
            height,
            fill="#e1e5eb",
            width=1,
        )

        # 最后重画分类标签与分隔线，使其始终固定在左侧标签列。
        for name, lane_top, lane_bottom, side in lane_positions:
            separator_y = lane_bottom if side == "top" else lane_top
            self.canvas.create_line(0, separator_y, width, separator_y, fill="#edf0f4")
            self.canvas.create_text(
                16,
                lane_top + 17,
                text=name,
                anchor="w",
                font=("Microsoft YaHei", self._scaled_font_size(10, 6), "bold"),
                fill="#30394c",
            )

        self.canvas.configure(scrollregion=(0, 0, width, height))

    def draw_time_grid(self, width, height, axis_y):
        for year in range(self.view_start.year, self.view_end.year + 1):
            date = datetime(year, 1, 1)
            if date < self.view_start or date > self.view_end:
                continue

            x = self.date_to_x(date, width)
            if x < self.clip_start or x > width - self.right_margin:
                continue

            self.canvas.create_line(x, 30, x, height - 30, fill="#e8ebf0", width=1)
            self.canvas.create_line(x, axis_y - 7, x, axis_y + 7, fill="#8b95a6", width=1)
            self.canvas.create_text(
                x,
                axis_y + 22,
                text=str(year),
                font=("Microsoft YaHei", self._scaled_font_size(9, 6)),
                fill="#657084",
            )

    def draw_today_line(self, width, height, axis_y):
        today = datetime.now()

        # 当今天日期不在当前可视时间范围内时，不绘制
        if today < self.view_start or today > self.view_end:
            return

        x = self.date_to_x(today, width)

        # 避免画进左侧固定分类区域，也避免超出右边界
        if x < self.clip_start or x > width - self.right_margin:
            return

        self.canvas.create_line(
            x,
            30,
            x,
            height - 30,
            fill="#e87979",
            width=1,
            tags=("today_line",),
        )

    def draw_category_items(self, name, items, side, lane_top, lane_bottom, axis_y):
        color = self.category_colors[name]

        for item in items:
            x = item["_x"]
            box_width = item["_box_width"]
            level_offset = item["_level"] * (self.box_height + max(4, round(10 * self.visual_scale)))

            if side == "top":
                box_y = lane_bottom - max(8, round(20 * self.visual_scale)) - self.box_height - level_offset
                connector_end = box_y + self.box_height
            else:
                box_y = lane_top + max(12, round(30 * self.visual_scale)) + level_offset
                connector_end = box_y

            # 完全位于标签列左侧的事件直接不画；
            # 部分进入标签列的事件会由固定遮罩裁掉。
            if x + box_width / 2 < self.clip_start:
                continue

            self.canvas.create_line(x, axis_y, x, connector_end, fill=color, width=1)
            self.canvas.create_oval(x - 4, axis_y - 4, x + 4, axis_y + 4, fill=color, outline="")

            item_tag = f"item_{item['_id']}"
            is_selected = (
                item["_id"] == getattr(self, "selected_event_id", None)
                or item["_id"] == getattr(self, "pressed_event_id", None)
            )
            self.canvas.create_rectangle(
                x - box_width / 2,
                box_y,
                x + box_width / 2,
                box_y + self.box_height,
                fill=lighten(color, 0.76 if is_selected else 0.86),
                outline="#111827" if is_selected else color,
                width=3 if is_selected else 1,
                tags=(item_tag, "timeline_item"),
            )

            self.canvas.create_text(
                x,
                box_y + max(9, round(17 * self.visual_scale)),
                text=item["title"],
                font=("Microsoft YaHei", self._scaled_font_size(10, 6), "bold"),
                fill="#172033",
                tags=(item_tag, "timeline_item"),
            )

            self.canvas.create_text(
                x,
                box_y + max(18, round(34 * self.visual_scale)),
                text=item["date"],
                font=("Consolas", self._scaled_font_size(8, 5)),
                fill="#667084",
                tags=(item_tag, "timeline_item"),
            )

            self.canvas.tag_bind(
                item_tag,
                "<ButtonPress-1>",
                lambda event, row=item: self.on_event_press(event, row),
            )
            self.canvas.tag_bind(item_tag, "<Enter>", lambda event, row=item: self.show_tooltip(event, row))
            self.canvas.tag_bind(item_tag, "<Motion>", self.move_tooltip)
            self.canvas.tag_bind(item_tag, "<Leave>", lambda _event: self.hide_tooltip())

    def show_tooltip(self, event, item):
        self.hide_tooltip()

        known = {
            "date",
            "title",
            "category",
            "group",
            "side",
            "_id",
            "_level",
            "_x",
            "_box_width",
            "_source_row",
        }

        lines = [
            item["title"],
            f"{item['date']} · {item['category']}",
        ]

        for key, value in item.items():
            if key in known or key.startswith("_"):
                continue

            text = str(value).strip()

            if text:
                lines.append(f"{key}：{text}")

        self.tooltip = tk.Toplevel(self)
        self.tooltip.overrideredirect(True)
        self.tooltip.attributes("-topmost", True)

        label = tk.Label(
            self.tooltip,
            text="\n".join(lines),
            justify="left",
            bg="white",
            fg="#293247",
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=8,
            font=("Microsoft YaHei", 9),
            wraplength=380,
        )
        label.pack()
        self.move_tooltip(event)

    def move_tooltip(self, _event):
        if not self.tooltip:
            return
        x = self.winfo_pointerx() + 14
        y = self.winfo_pointery() + 14
        self.tooltip.geometry(f"+{x}+{y}")

    def hide_tooltip(self):
        if self.tooltip:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None

    def on_event_press(self, _event, item):
        """左键按住事件时临时高亮，直到左键真正松开。"""
        self.pressed_event_id = item["_id"]
        self.drag_start_x = None
        self.drag_start_view = None

        # 抓取鼠标后，即使指针移出事件框、画布或主窗口，
        # 松开左键时仍能收到释放事件并取消高亮。
        try:
            self.canvas.grab_set()
        except tk.TclError:
            pass

        self.render()
        return "break"

    def on_event_release(self, _event=None):
        """左键松开时取消临时高亮；鼠标位置不作限制。"""
        if getattr(self, "pressed_event_id", None) is None:
            return None

        self.pressed_event_id = None

        try:
            if self.canvas.grab_current() is self.canvas:
                self.canvas.grab_release()
        except tk.TclError:
            pass

        self.render()
        return "break"

    def on_drag_start(self, event):
        if self.canvas.find_withtag("current"):
            tags = self.canvas.gettags("current")
            if "timeline_item" in tags:
                return

        self.drag_start_x = event.x_root
        self.drag_start_view = (self.view_start, self.view_end)

    def on_drag_move(self, event):
        if self.drag_start_x is None or self.drag_start_view is None:
            return

        delta_x = event.x_root - self.drag_start_x
        start, end = self.drag_start_view
        span = end - start
        usable_width = max(400, self.canvas.winfo_width() - self.plot_start - self.right_margin)
        delta_seconds = (-delta_x / usable_width) * span.total_seconds()

        self.view_start = start + timedelta(seconds=delta_seconds)
        self.view_end = end + timedelta(seconds=delta_seconds)

        self.sync_range_entries()
        self.render()

    def on_drag_end(self, _event):
        self.drag_start_x = None
        self.drag_start_view = None

    def on_alt_key_press(self, _event=None):
        """兼容 ui.py 中现有绑定；当前不处理 Alt。"""
        return None

    def on_alt_key_release(self, _event=None):
        """兼容 ui.py 中现有绑定；当前不处理 Alt。"""
        return None

    def on_modifier_focus_out(self, _event=None):
        """兼容 ui.py 中现有绑定；当前不保存修饰键状态。"""
        return None

    @staticmethod
    def _wheel_delta(event):
        """统一 Windows、macOS 与 Linux 的滚轮方向。"""
        if getattr(event, "num", None) == 4:
            return 120
        if getattr(event, "num", None) == 5:
            return -120
        return getattr(event, "delta", 0)

    def on_mousewheel(self, event):
        """时间轴画布滚轮控制。

        普通滚轮：上下移动视野
        Shift + 滚轮：左右移动视野
        Ctrl + 滚轮：横向缩放时间轴
        Ctrl + Shift + 滚轮：二维缩放视野

        当前完全忽略 Alt，不读取 Alt 状态，也不维护 Alt 状态。
        """
        delta_value = self._wheel_delta(event)
        if delta_value == 0:
            return "break"

        state = getattr(event, "state", 0)
        ctrl_pressed = bool(state & 0x0004)
        shift_pressed = bool(state & 0x0001)

        # Ctrl + Shift + 滚轮：二维缩放。
        # 直接复用工具栏“＋ / －”已经验证可用的视觉缩放逻辑，
        # 并把鼠标位置作为缩放锚点。
        if ctrl_pressed and shift_pressed:
            steps = max(1, abs(int(delta_value / 120)))
            factor = (1.10 ** steps) if delta_value > 0 else ((1 / 1.10) ** steps)
            self.change_visual_scale(
                factor,
                anchor_x=event.x,
                anchor_y=event.y,
            )
            return "break"

        if ctrl_pressed:
            event.delta = delta_value
            self.zoom_at_pointer(event)
            return "break"

        steps = max(1, abs(int(delta_value / 120)))
        direction = -1 if delta_value > 0 else 1

        if shift_pressed:
            span = self.view_end - self.view_start
            move_delta = span * (0.08 * steps)

            if direction < 0:
                self.view_start -= move_delta
                self.view_end -= move_delta
            else:
                self.view_start += move_delta
                self.view_end += move_delta

            self.sync_range_entries()
            self.render()
            return "break"

        self.canvas.yview_scroll(direction * steps * 35, "units")
        return "break"

    def zoom_at_pointer(self, event):
        width = self.canvas_width()
        pointer_x = max(self.plot_start, min(width - self.right_margin, event.x))
        anchor_date = self.x_to_date(pointer_x, width)

        old_span = self.view_end - self.view_start
        factor = 0.82 if event.delta > 0 else 1.22

        new_seconds = old_span.total_seconds() * factor
        new_seconds = max(30 * 86400, min(200 * 365 * 86400, new_seconds))
        new_span = timedelta(seconds=new_seconds)

        ratio = (anchor_date - self.view_start).total_seconds() / old_span.total_seconds()
        self.view_start = anchor_date - new_span * ratio
        self.view_end = self.view_start + new_span

        self.sync_range_entries()
        self.render()
