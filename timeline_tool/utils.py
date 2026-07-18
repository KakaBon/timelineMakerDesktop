"""不依赖界面的通用工具函数。"""

import sys
from datetime import datetime
from pathlib import Path

from .config import DATE_FORMAT


def parse_date(value: str):
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT)
    except Exception:
        return None


def lighten(hex_color: str, ratio: float = 0.86) -> str:
    value = hex_color.lstrip("#")
    r = int(value[0:2], 16)
    g = int(value[2:4], 16)
    b = int(value[4:6], 16)

    def mix(channel):
        return round(channel + (255 - channel) * ratio)

    return f"#{mix(r):02x}{mix(g):02x}{mix(b):02x}"


def resource_path(relative_path: str) -> Path:
    """返回源码运行和 PyInstaller 运行时都可用的资源路径。"""
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path
