"""CSVManagerMixin 聚合入口。实现已按职责拆分，保留原导入路径。"""

from .csv_model import CSVModelMixin
from .csv_validation import CSVValidationMixin
from .csv_search import CSVSearchMixin
from .csv_structure import CSVStructureMixin
from .csv_apply import CSVApplyMixin
from .csv_interaction import CSVInteractionMixin


class CSVManagerMixin(
    CSVModelMixin,
    CSVValidationMixin,
    CSVSearchMixin,
    CSVStructureMixin,
    CSVApplyMixin,
    CSVInteractionMixin,
):
    pass


__all__ = ["CSVManagerMixin"]
