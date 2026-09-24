"""UIMixin 聚合入口。实现已按职责拆分，保留原导入路径。"""

from .ui_scrollbar import UnifiedScrollbar
from .ui_core import UICoreMixin
from .ui_layout import UILayoutMixin
from .ui_interaction import UIInteractionMixin
from .ui_controls import UIControlsMixin


class UIMixin(
    UICoreMixin,
    UILayoutMixin,
    UIInteractionMixin,
    UIControlsMixin,
):
    pass


__all__ = ["UIMixin", "UnifiedScrollbar"]
