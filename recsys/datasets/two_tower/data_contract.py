"""Two-Tower 数据口径冻结与契约校验。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DataContractFreezeSummary:
    """数据口径冻结摘要。"""

    checked_files: int
    missing_files: int
    files_with_invalid_columns: int
    output_path: str


def _read_csv_header(path: Path) -> list[str]:
    """读取 CSV 表头并标准化空白字符。"""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            return []
        return [field.strip() for field in reader.fieldnames if field and field.strip()]


def freeze_data_contract(
    *,
    input_paths: dict[str, Path],
    required_columns: dict[str, list[str]],
    field_dictionary: dict[str, dict[str, str]],
    id_mapping: dict[str, str],
    missing_value_policy: dict[str, str],
    split_policy: dict[str, Any],
    negative_sampling_policy: dict[str, Any],
    output_json: Path,
) -> DataContractFreezeSummary:
    """冻结训练输入契约，并在缺失关键字段时抛出异常。"""
    validations: list[dict[str, Any]] = []

    missing_files: list[str] = []
    invalid_column_files: list[str] = []

    for alias, path in input_paths.items():
        required = required_columns.get(alias, [])
        exists = path.exists()
        headers: list[str] = []
        missing_required_columns: list[str] = []

        if exists:
            headers = _read_csv_header(path)
            missing_required_columns = [
                column for column in required if column not in headers
            ]
            if missing_required_columns:
                invalid_column_files.append(alias)
        else:
            missing_files.append(alias)

        validations.append(
            {
                "alias": alias,
                "path": str(path),
                "exists": exists,
                "required_columns": required,
                "actual_columns": headers,
                "missing_required_columns": missing_required_columns,
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_files": {alias: str(path) for alias, path in input_paths.items()},
        "required_columns": required_columns,
        "field_dictionary": field_dictionary,
        "id_mapping": id_mapping,
        "missing_value_policy": missing_value_policy,
        "split_policy": split_policy,
        "negative_sampling_policy": negative_sampling_policy,
        "validations": validations,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if missing_files or invalid_column_files:
        problems = {
            "missing_files": missing_files,
            "invalid_column_files": invalid_column_files,
        }
        raise ValueError(
            "数据口径冻结失败，存在缺失文件或字段不匹配："
            + json.dumps(problems, ensure_ascii=False)
        )

    return DataContractFreezeSummary(
        checked_files=len(validations),
        missing_files=len(missing_files),
        files_with_invalid_columns=len(invalid_column_files),
        output_path=str(output_json),
    )
