"""CSV 文档解析、格式记录与导出。"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

REQUIRED_HEADERS = {"date", "title", "side"}
CATEGORY_HEADERS = {"category", "group"}
DELIMITERS = (",", ";", "\t")


@dataclass
class CsvFormat:
    encoding: str = "utf-8-sig"
    newline: str = "\r\n"
    delimiter: str = ","
    structure: str = "multi"  # multi | single_wrapped
    outer_delimiter: str = ","


@dataclass
class ParsedCsvDocument:
    rows: list[dict[str, str]]
    editor_text: str
    format: CsvFormat
    fieldnames: list[str]


def detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def decode_csv_bytes(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig"), "utf-8-sig"
    candidates = (
        "utf-8",
        "gb18030",
        "cp1252",
        "cp1250",
        "latin-1",
    )
    last_error: Exception | None = None
    for encoding in candidates:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"无法识别 CSV 编码：{last_error}")


def _normalize_header(value: str) -> str:
    return value.strip().lstrip("\ufeff").lower()


def _read_table(text: str, delimiter: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    raw = [row for row in reader if any(cell.strip() for cell in row)]
    if not raw:
        raise ValueError("CSV 文本为空。")
    return raw[0], raw[1:]


def _validate_headers(fieldnames: list[str]) -> dict[str, int]:
    normalized = [_normalize_header(name) for name in fieldnames]
    duplicates = sorted({name for name in normalized if normalized.count(name) > 1 and name})
    if duplicates:
        raise ValueError("表头字段重复：" + "、".join(duplicates))

    missing = sorted(REQUIRED_HEADERS - set(normalized))
    if not (CATEGORY_HEADERS & set(normalized)):
        missing.append("category/group")
    if missing:
        raise ValueError("CSV 缺少必要表头：" + "、".join(missing))

    return {name: index for index, name in enumerate(normalized)}


def _candidate_delimiter(text: str) -> tuple[str, list[str], list[list[str]]]:
    failures: list[tuple[int, str]] = []
    for delimiter in DELIMITERS:
        try:
            header, data = _read_table(text, delimiter)
            width = len(header)
            _validate_headers(header)
            return delimiter, header, data
        except Exception as exc:
            width = len(header) if "header" in locals() else 0
            failures.append((width, str(exc)))
    if failures:
        # 使用最像真实表格的候选错误，避免逗号文件最后只显示 Tab 候选的泛化提示。
        failures.sort(key=lambda item: item[0], reverse=True)
        raise ValueError(failures[0][1])
    raise ValueError("无法识别 CSV 分隔符。")


def _unwrap_single_column(text: str) -> tuple[str, str] | None:
    # 单列包装文件常见形式：每个物理 CSV 单元格中放一整行逗号或分号文本。
    for outer_delimiter in DELIMITERS:
        try:
            reader = csv.reader(io.StringIO(text), delimiter=outer_delimiter)
            rows = [row for row in reader if any(cell.strip() for cell in row)]
        except csv.Error:
            continue
        if not rows or any(len(row) != 1 for row in rows):
            continue
        logical_text = "\n".join(row[0] for row in rows)
        try:
            _candidate_delimiter(logical_text)
            return logical_text, outer_delimiter
        except ValueError:
            continue
    return None


def parse_csv_document(text: str, *, encoding: str = "utf-8-sig") -> ParsedCsvDocument:
    if not text.strip():
        raise ValueError("CSV 文本为空。")

    newline = detect_newline(text)
    try:
        delimiter, fieldnames, data_rows = _candidate_delimiter(text)
        structure = "multi"
        outer_delimiter = ","
        editor_text = text
    except ValueError:
        unwrapped = _unwrap_single_column(text)
        if not unwrapped:
            raise
        structure = "single_wrapped"
        editor_text = unwrapped[0]
        delimiter, fieldnames, data_rows = _candidate_delimiter(editor_text)
        outer_delimiter = delimiter
    header_map = _validate_headers(fieldnames)
    width = len(fieldnames)
    rows: list[dict[str, str]] = []

    for source_index, values in enumerate(data_rows, start=2):
        if len(values) > width:
            raise ValueError(f"第 {source_index} 行字段数量多于表头。")
        values = values + [""] * (width - len(values))
        row = {fieldnames[i]: values[i] for i in range(width)}
        row["__source_row__"] = str(source_index)
        rows.append(row)

    if not rows:
        raise ValueError("CSV 中没有事件数据。")

    return ParsedCsvDocument(
        rows=rows,
        editor_text=editor_text.replace("\r\n", "\n").replace("\r", "\n"),
        format=CsvFormat(
            encoding=encoding,
            newline=newline,
            delimiter=delimiter,
            structure=structure,
            outer_delimiter=outer_delimiter,
        ),
        fieldnames=fieldnames,
    )


def serialize_editor_text(editor_text: str, fmt: CsvFormat) -> str:
    logical = editor_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = logical.split("\n")
    while lines and lines[-1] == "":
        lines.pop()

    if fmt.structure == "single_wrapped":
        output = io.StringIO(newline="")
        writer = csv.writer(
            output,
            delimiter=fmt.outer_delimiter,
            lineterminator=fmt.newline,
            quoting=csv.QUOTE_MINIMAL,
        )
        for line in lines:
            writer.writerow([line])
        return output.getvalue()

    return fmt.newline.join(lines) + (fmt.newline if lines else "")


_MONTHS = {
    "jan": 1, "january": 1, "januar": 1,
    "feb": 2, "february": 2, "februar": 2,
    "mar": 3, "march": 3, "mär": 3, "maerz": 3, "märz": 3,
    "apr": 4, "april": 4,
    "may": 5, "mai": 5,
    "jun": 6, "june": 6, "juni": 6,
    "jul": 7, "july": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "okt": 10, "october": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dec": 12, "dez": 12, "december": 12, "dezember": 12,
}


def _build_date(year: int, month: int, day: int) -> datetime | None:
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def parse_flexible_date(value: str) -> tuple[datetime | None, str | None]:
    raw = value.strip()
    if not raw:
        return None, None

    m = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日", raw)
    if m:
        return _build_date(*map(int, m.groups())), "ymd-cn"

    m = re.fullmatch(r"(\d{4})([-./])(\d{1,2})\2(\d{1,2})", raw)
    if m:
        return _build_date(int(m.group(1)), int(m.group(3)), int(m.group(4))), f"ymd-{m.group(2)}"

    m = re.fullmatch(r"(\d{1,2})([-./])(\d{1,2})\2(\d{4})", raw)
    if m:
        first, second, year = int(m.group(1)), int(m.group(3)), int(m.group(4))
        sep = m.group(2)
        if first > 12 and second <= 12:
            return _build_date(year, second, first), f"dmy-{sep}"
        if second > 12 and first <= 12:
            return _build_date(year, first, second), f"mdy-{sep}"
        return None, "ambiguous-numeric"

    normalized = re.sub(r"[,]+", " ", raw)
    normalized = re.sub(r"[.\-/]+", " ", normalized)
    parts = [part for part in normalized.split() if part]
    if len(parts) == 3:
        lower = [part.casefold() for part in parts]
        # 月 日 年
        month = _MONTHS.get(lower[0])
        if month and parts[1].isdigit() and parts[2].isdigit():
            return _build_date(int(parts[2]), month, int(parts[1])), "mdy-name"
        # 日 月 年
        month = _MONTHS.get(lower[1])
        if parts[0].isdigit() and month and parts[2].isdigit():
            return _build_date(int(parts[2]), month, int(parts[0])), "dmy-name"

    return None, None


def validate_date_style(styles: Iterable[str]) -> None:
    used = {style for style in styles if style}
    if "ambiguous-numeric" in used:
        raise ValueError(
            "日期列包含无法判断日/月顺序的日期，请改用 YYYY-MM-DD、中文年月日或月份文字格式。"
        )
    if len(used) > 1:
        raise ValueError("日期格式混用，请在同一份 CSV 中统一日期顺序和分隔写法。")
