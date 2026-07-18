"""ExportMixin：按功能拆分自原始桌面时间轴工具。"""

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from xml.sax.saxutils import escape as xml_escape

from .utils import lighten

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    Image = ImageDraw = ImageFont = None
    PIL_AVAILABLE = False


class ExportMixin:
    def export_image(self):
        if not self.rows:
            return

        path = filedialog.asksaveasfilename(
            title="导出图片",
            defaultextension=".svg",
            filetypes=[
                ("SVG 矢量图片", "*.svg"),
                ("PNG 图片", "*.png"),
            ],
        )
        if not path:
            return

        suffix = Path(path).suffix.lower()

        old_start = self.view_start
        old_end = self.view_end

        try:
            full_start, full_end = self.get_full_data_range()

            self.view_start = full_start
            self.view_end = full_end

            export_width = self.get_full_export_width(
                full_start,
                full_end,
            )

            layout = self.calculate_layout(
                width_override=export_width,
            )

            if suffix == ".png":
                self.export_png(path, layout)
            else:
                if suffix != ".svg":
                    path += ".svg"

                svg_text = self.build_svg(layout)
                Path(path).write_text(
                    svg_text,
                    encoding="utf-8",
                )

            exported_path = str(Path(path))
            exported_name = Path(path).name
            self.status_var.set(f"已导出图片：{exported_path}")
            messagebox.showinfo(
                "导出完成",
                f"图片导出成功。\n\n文件：{exported_name}",
            )

        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

        finally:
            self.view_start = old_start
            self.view_end = old_end
            self.render()

    def export_png(self, path, layout):
        if not PIL_AVAILABLE:
            raise RuntimeError(
                "当前 Python 环境没有 Pillow。\n"
                "请在命令行运行：pip install pillow"
            )

        width = int(layout["width"])
        height = int(layout["height"])
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        title_font = self.find_font(15, bold=True)
        date_font = self.find_font(11)
        category_font = self.find_font(15, bold=True)
        year_font = self.find_font(12)

        axis_y = layout["axis_y"]

        for year in range(self.view_start.year, self.view_end.year + 1):
            date = datetime(year, 1, 1)
            if date < self.view_start or date > self.view_end:
                continue

            x = self.date_to_x(date, width)
            if x < self.clip_start or x > width - self.right_margin:
                continue

            draw.line((x, 30, x, height - 30), fill="#e8ebf0", width=1)
            draw.line((x, axis_y - 7, x, axis_y + 7), fill="#8b95a6", width=1)
            self.draw_centered_text(draw, x, axis_y + 16, str(year), year_font, "#657084")

        today = datetime.now()

        if self.view_start <= today <= self.view_end:
            today_x = self.date_to_x(today, width)

            draw.line(
                (today_x, 30, today_x, height - 30),
                fill="#e87979",
                width=1,
            )

        lane_positions = []
        cursor = self.top_margin
        for name in layout["top_categories"]:
            items, lane_height = layout["category_layout"][("top", name)]
            lane_bottom = cursor + lane_height
            self.draw_png_category_items(
                draw, name, items, "top", cursor, lane_bottom, axis_y,
                title_font, date_font
            )
            lane_positions.append((name, cursor, lane_bottom, "top"))
            cursor = lane_bottom + self.lane_gap

        cursor = axis_y + self.axis_gap
        for name in layout["bottom_categories"]:
            items, lane_height = layout["category_layout"][("bottom", name)]
            lane_top = cursor
            lane_bottom = cursor + lane_height
            self.draw_png_category_items(
                draw, name, items, "bottom", lane_top, lane_bottom, axis_y,
                title_font, date_font
            )
            lane_positions.append((name, lane_top, lane_bottom, "bottom"))
            cursor = lane_bottom + self.lane_gap

        draw.line(
            (self.plot_start, axis_y, width - self.right_margin, axis_y),
            fill="#2f3a4e",
            width=2,
        )

        # 固定标签列遮罩与标签。
        draw.rectangle((0, 0, self.clip_start, height), fill="white")
        draw.line((self.clip_start, 0, self.clip_start, height), fill="#e1e5eb", width=1)

        for name, lane_top, lane_bottom, side in lane_positions:
            separator_y = lane_bottom if side == "top" else lane_top
            draw.line((0, separator_y, width, separator_y), fill="#edf0f4", width=1)
            draw.text((16, lane_top + 6), name, font=category_font, fill="#30394c")

        image.save(path, "PNG")

    def find_font(self, size, bold=False):
        candidates = [
            r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        ]

        for candidate in candidates:
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue

        return ImageFont.load_default()

    def draw_centered_text(self, draw, x, y, text, font, fill):
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        draw.text((x - width / 2, y), text, font=font, fill=fill)

    def draw_png_category_items(
        self, draw, name, items, side, lane_top, lane_bottom, axis_y,
        title_font, date_font,
    ):
        color = self.category_colors[name]

        for item in items:
            x = item["_x"]
            box_width = item["_box_width"]
            level_offset = item["_level"] * (self.box_height + 10)

            if side == "top":
                box_y = lane_bottom - 20 - self.box_height - level_offset
                connector_end = box_y + self.box_height
            else:
                box_y = lane_top + 30 + level_offset
                connector_end = box_y

            if x + box_width / 2 < self.clip_start:
                continue

            draw.line((x, axis_y, x, connector_end), fill=color, width=1)
            draw.ellipse((x - 4, axis_y - 4, x + 4, axis_y + 4), fill=color)

            draw.rounded_rectangle(
                (x - box_width / 2, box_y, x + box_width / 2, box_y + self.box_height),
                radius=7,
                fill=lighten(color),
                outline=color,
                width=1,
            )

            title_box = draw.textbbox((0, 0), item["title"], font=title_font)
            title_width = title_box[2] - title_box[0]
            draw.text(
                (x - title_width / 2, box_y + 5),
                item["title"],
                font=title_font,
                fill="#172033",
            )

            date_box = draw.textbbox((0, 0), item["date"], font=date_font)
            date_width = date_box[2] - date_box[0]
            draw.text(
                (x - date_width / 2, box_y + 26),
                item["date"],
                font=date_font,
                fill="#667084",
            )

    def build_svg(self, layout):
        width = layout["width"]
        height = layout["height"]
        axis_y = layout["axis_y"]

        clip_width = width - self.clip_start
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<defs>',
            f'<clipPath id="plotClip"><rect x="{self.clip_start}" y="0" width="{clip_width}" height="{height}"/></clipPath>',
            '</defs>',
            '<style>',
            'text{font-family:"Microsoft YaHei","PingFang SC",sans-serif}',
            '.year{font-size:12px;fill:#657084}',
            '.category{font-size:13px;font-weight:700;fill:#30394c}',
            '.title{font-size:13px;font-weight:700;fill:#172033}',
            '.date{font-size:10px;fill:#667084}',
            '</style>',
            '<g clip-path="url(#plotClip)">',
        ]

        for year in range(self.view_start.year, self.view_end.year + 1):
            date = datetime(year, 1, 1)
            if date < self.view_start or date > self.view_end:
                continue
            x = self.date_to_x(date, width)
            parts.append(f'<line x1="{x:.2f}" y1="30" x2="{x:.2f}" y2="{height - 30}" stroke="#e8ebf0"/>')
            parts.append(f'<line x1="{x:.2f}" y1="{axis_y - 7}" x2="{x:.2f}" y2="{axis_y + 7}" stroke="#8b95a6"/>')
            parts.append(f'<text x="{x:.2f}" y="{axis_y + 24}" text-anchor="middle" class="year">{year}</text>')

        today = datetime.now()

        if self.view_start <= today <= self.view_end:
            today_x = self.date_to_x(today, width)

            parts.append(
                f'<line '
                f'x1="{today_x:.2f}" y1="30" '
                f'x2="{today_x:.2f}" y2="{height - 30}" '
                f'stroke="#e87979" stroke-width="1"/>'
            )

        lane_positions = []
        cursor = self.top_margin
        for name in layout["top_categories"]:
            items, lane_height = layout["category_layout"][("top", name)]
            lane_bottom = cursor + lane_height
            parts.extend(self.svg_category_items(name, items, "top", cursor, lane_bottom, axis_y))
            lane_positions.append((name, cursor, lane_bottom, "top"))
            cursor = lane_bottom + self.lane_gap

        cursor = axis_y + self.axis_gap
        for name in layout["bottom_categories"]:
            items, lane_height = layout["category_layout"][("bottom", name)]
            lane_top = cursor
            lane_bottom = cursor + lane_height
            parts.extend(self.svg_category_items(name, items, "bottom", lane_top, lane_bottom, axis_y))
            lane_positions.append((name, lane_top, lane_bottom, "bottom"))
            cursor = lane_bottom + self.lane_gap

        parts.append(
            f'<line x1="{self.plot_start}" y1="{axis_y}" x2="{width - self.right_margin}" y2="{axis_y}" stroke="#2f3a4e" stroke-width="2"/>'
        )
        parts.append('</g>')

        # 固定标签列与分类标签。
        parts.append(f'<rect x="0" y="0" width="{self.clip_start}" height="{height}" fill="#ffffff"/>')
        parts.append(f'<line x1="{self.clip_start}" y1="0" x2="{self.clip_start}" y2="{height}" stroke="#e1e5eb"/>')

        for name, lane_top, lane_bottom, side in lane_positions:
            separator_y = lane_bottom if side == "top" else lane_top
            parts.append(f'<line x1="0" y1="{separator_y:.2f}" x2="{width}" y2="{separator_y:.2f}" stroke="#edf0f4"/>')
            parts.append(f'<text x="16" y="{lane_top + 20:.2f}" class="category">{xml_escape(name)}</text>')

        parts.append("</svg>")
        return "\n".join(parts)

    def svg_category_items(self, name, items, side, lane_top, lane_bottom, axis_y):
        color = self.category_colors[name]
        output = []

        for item in items:
            x = item["_x"]
            box_width = item["_box_width"]
            level_offset = item["_level"] * (self.box_height + 10)

            if side == "top":
                box_y = lane_bottom - 20 - self.box_height - level_offset
                connector_end = box_y + self.box_height
            else:
                box_y = lane_top + 30 + level_offset
                connector_end = box_y

            output.extend([
                f'<line x1="{x:.2f}" y1="{axis_y:.2f}" x2="{x:.2f}" y2="{connector_end:.2f}" stroke="{color}" stroke-width="1.4"/>',
                f'<circle cx="{x:.2f}" cy="{axis_y:.2f}" r="4" fill="{color}"/>',
                f'<rect x="{x - box_width / 2:.2f}" y="{box_y:.2f}" width="{box_width:.2f}" height="{self.box_height}" rx="7" fill="{lighten(color)}" stroke="{color}"/>',
                f'<text x="{x:.2f}" y="{box_y + 18:.2f}" text-anchor="middle" class="title">{xml_escape(item["title"])}</text>',
                f'<text x="{x:.2f}" y="{box_y + 35:.2f}" text-anchor="middle" class="date">{xml_escape(item["date"])}</text>',
            ])

        return output
