"""LegendMixin 聚合入口。实现已按职责拆分，保留原导入路径。"""

from .legend_core import LegendCoreMixin
from .legend_migration_ui import LegendMigrationUIMixin
from .legend_migration_actions import LegendMigrationActionsMixin
from .legend_rows import LegendRowsMixin
from .legend_search import LegendSearchMixin
from .legend_render import LegendRenderMixin


class LegendMixin(
    LegendCoreMixin,
    LegendMigrationUIMixin,
    LegendMigrationActionsMixin,
    LegendRowsMixin,
    LegendSearchMixin,
    LegendRenderMixin,
):
    pass


__all__ = ["LegendMixin"]
