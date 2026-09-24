"""统一滚动条组件。"""

import tkinter as tk


class UnifiedScrollbar(tk.Canvas):
    """全页统一滚动条：低对比度外观，三角只在滚动/拖动时短暂显示。"""

    TRACK_COLOR = "#f1f2f4"
    THUMB_COLOR = "#c4c8ce"
    THUMB_ACTIVE_COLOR = "#b8bdc4"
    ARROW_COLOR = "#8f98a5"
    THICKNESS = 14
    ARROW_SIZE = 12
    MIN_THUMB = 18
    ARROW_VISIBLE_MS = 650

    def __init__(self, parent, orient, command, **kwargs):
        self.orient = str(orient)
        self.command = command
        self._first = 0.0
        self._last = 1.0
        self._has_set_once = False
        self._feedback_ready = False
        self._arrows_visible = False
        self._hide_job = None
        self._dragging = False
        self._drag_offset = 0.0
        self._thumb_start = 0.0
        self._thumb_end = 0.0
        self._hover_thumb = False
        self._is_timeline_scrollbar = True

        thickness = int(kwargs.pop("width", self.THICKNESS))
        kwargs.pop("troughcolor", None)
        kwargs.pop("background", None)
        kwargs.pop("activebackground", None)
        kwargs.pop("relief", None)
        kwargs.pop("bd", None)
        kwargs.pop("borderwidth", None)
        kwargs.pop("elementborderwidth", None)
        kwargs.pop("activerelief", None)

        # Canvas 自身有很大的默认 request size（约 276 px）。
        # 统一滚动条只在“厚度”方向声明尺寸；沿滚动方向只请求 1 px，
        # 由 grid/pack 的 sticky/fill 拉伸到宿主区域。否则例如信息记录区的
        # 纵向滚动条会把第一横区直接撑高，破坏原来的三横区比例。
        if self.orient == "horizontal":
            kwargs.setdefault("height", thickness)
            kwargs.setdefault("width", 1)
        else:
            kwargs.setdefault("width", thickness)
            kwargs.setdefault("height", 1)

        super().__init__(
            parent,
            bg=self.TRACK_COLOR,
            highlightthickness=0,
            bd=0,
            cursor="arrow",
            **kwargs,
        )

        self.bind("<Configure>", self._redraw, add="+")
        self.bind("<Motion>", self._on_motion, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<B1-Motion>", self._on_drag, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.after(500, self._enable_change_feedback)

    def _enable_change_feedback(self):
        self._feedback_ready = True
        self._arrows_visible = False
        self._redraw()

    def set(self, first, last):
        try:
            first_f = max(0.0, min(1.0, float(first)))
            last_f = max(first_f, min(1.0, float(last)))
        except (TypeError, ValueError):
            return

        changed = abs(first_f - self._first) > 1e-9 or abs(last_f - self._last) > 1e-9
        self._first, self._last = first_f, last_f
        if self._feedback_ready and self._has_set_once and changed:
            self.show_arrows_temporarily()
        else:
            self._has_set_once = True
        self._redraw()

    def get(self):
        return (self._first, self._last)

    def show_arrows_temporarily(self):
        self._arrows_visible = True
        if self._hide_job is not None:
            try:
                self.after_cancel(self._hide_job)
            except tk.TclError:
                pass
            self._hide_job = None
        self._redraw()
        if not self._dragging:
            self._hide_job = self.after(self.ARROW_VISIBLE_MS, self._hide_arrows)

    def _hide_arrows(self):
        self._hide_job = None
        if self._dragging:
            return
        self._arrows_visible = False
        self._redraw()

    def _axis_pos(self, event):
        return float(event.y if self.orient != "horizontal" else event.x)

    def _axis_length(self):
        return float(self.winfo_height() if self.orient != "horizontal" else self.winfo_width())

    def _cross_length(self):
        return float(self.winfo_width() if self.orient != "horizontal" else self.winfo_height())

    def _geometry(self):
        length = max(1.0, self._axis_length())
        cross = max(1.0, self._cross_length())
        arrow = min(float(self.ARROW_SIZE), max(0.0, (length - 4.0) / 2.0))
        track_start = arrow
        track_end = max(track_start, length - arrow)
        track_len = max(1.0, track_end - track_start)
        visible = max(0.0, min(1.0, self._last - self._first))
        thumb_len = track_len if visible >= 1.0 else max(float(self.MIN_THUMB), track_len * visible)
        thumb_len = min(track_len, thumb_len)
        movable = max(0.0, track_len - thumb_len)
        max_first = max(1e-12, 1.0 - visible)
        ratio = 0.0 if movable <= 0.0 else max(0.0, min(1.0, self._first / max_first))
        thumb_start = track_start + movable * ratio
        thumb_end = thumb_start + thumb_len
        return length, cross, arrow, track_start, track_end, thumb_start, thumb_end

    def _redraw(self, _event=None):
        if not self.winfo_exists():
            return
        self.delete("scrollbar")
        length, cross, arrow, _ts, _te, thumb_start, thumb_end = self._geometry()
        self._thumb_start, self._thumb_end = thumb_start, thumb_end

        self.create_rectangle(
            0, 0, self.winfo_width(), self.winfo_height(),
            fill=self.TRACK_COLOR, outline=self.TRACK_COLOR, tags="scrollbar"
        )

        inset = 2.0
        thumb_color = self.THUMB_ACTIVE_COLOR if self._hover_thumb or self._dragging else self.THUMB_COLOR
        if self.orient == "horizontal":
            self.create_rectangle(
                thumb_start, inset, thumb_end, max(inset, cross - inset),
                fill=thumb_color, outline=thumb_color, tags="scrollbar"
            )
        else:
            self.create_rectangle(
                inset, thumb_start, max(inset, cross - inset), thumb_end,
                fill=thumb_color, outline=thumb_color, tags="scrollbar"
            )

        if self._arrows_visible and arrow >= 5:
            c = self.ARROW_COLOR
            mid = cross / 2.0
            a = min(3.5, arrow * 0.28)
            if self.orient == "horizontal":
                c1, c2 = arrow / 2.0, length - arrow / 2.0
                self.create_polygon(c1 + a, mid - a, c1 + a, mid + a, c1 - a, mid, fill=c, outline=c, tags="scrollbar")
                self.create_polygon(c2 - a, mid - a, c2 - a, mid + a, c2 + a, mid, fill=c, outline=c, tags="scrollbar")
            else:
                c1, c2 = arrow / 2.0, length - arrow / 2.0
                self.create_polygon(mid - a, c1 + a, mid + a, c1 + a, mid, c1 - a, fill=c, outline=c, tags="scrollbar")
                self.create_polygon(mid - a, c2 - a, mid + a, c2 - a, mid, c2 + a, fill=c, outline=c, tags="scrollbar")

    def _on_motion(self, event):
        pos = self._axis_pos(event)
        hover = self._thumb_start <= pos <= self._thumb_end
        if hover != self._hover_thumb:
            self._hover_thumb = hover
            self._redraw()

    def _on_leave(self, _event=None):
        if self._hover_thumb and not self._dragging:
            self._hover_thumb = False
            self._redraw()

    def _on_press(self, event):
        self.show_arrows_temporarily()
        pos = self._axis_pos(event)
        length, _cross, arrow, _ts, _te, thumb_start, thumb_end = self._geometry()

        if pos < arrow:
            self.command("scroll", -1, "units")
            return "break"
        if pos > length - arrow:
            self.command("scroll", 1, "units")
            return "break"
        if thumb_start <= pos <= thumb_end:
            self._dragging = True
            self._drag_offset = pos - thumb_start
            if self._hide_job is not None:
                try:
                    self.after_cancel(self._hide_job)
                except tk.TclError:
                    pass
                self._hide_job = None
            self._redraw()
            return "break"

        self.command("scroll", -1 if pos < thumb_start else 1, "pages")
        return "break"

    def _on_drag(self, event):
        if not self._dragging:
            return None
        pos = self._axis_pos(event)
        length, _cross, arrow, track_start, track_end, thumb_start, thumb_end = self._geometry()
        track_len = max(1.0, track_end - track_start)
        thumb_len = max(0.0, thumb_end - thumb_start)
        movable = max(0.0, track_len - thumb_len)
        visible = max(0.0, min(1.0, self._last - self._first))
        max_first = max(0.0, 1.0 - visible)
        if movable <= 0.0 or max_first <= 0.0:
            return "break"
        pixel = max(0.0, min(movable, pos - self._drag_offset - track_start))
        target = (pixel / movable) * max_first
        self.command("moveto", target)
        return "break"

    def _on_release(self, _event=None):
        if self._dragging:
            self._dragging = False
            self._redraw()
        self.show_arrows_temporarily()
        return "break"

