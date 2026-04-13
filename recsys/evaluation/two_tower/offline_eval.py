"""Two-Tower 离线评估（Recall@K / NDCG@K / Coverage）。"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class TwoTowerEvaluationSummary:
    """离线评估摘要。"""

    total_ranked_users: int
    evaluable_users: int
    ks: list[int]
    report_path: str
    two_tower_recall_at_k: dict[str, float]
    two_tower_ndcg_at_k: dict[str, float]
    two_tower_coverage_at_k: dict[str, float]
    global_hot_recall_at_k: dict[str, float]
    global_hot_ndcg_at_k: dict[str, float]
    global_hot_coverage_at_k: dict[str, float]


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return int(text)
        except ValueError:
            return default
    return default


def _deduplicate_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        deduplicated.append(item)
    return deduplicated


def _load_ranked_by_user(ranked_jsonl: Path) -> tuple[dict[str, list[str]], int]:
    ranked: dict[str, list[str]] = {}
    total_rows = 0

    for row in _iter_jsonl(ranked_jsonl):
        total_rows += 1
        user_key = str(row.get("user_key") or "").strip()
        if not user_key:
            continue

        items = row.get("items") or []
        if not isinstance(items, list):
            items = []

        song_ids: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            song_id = str(item.get("song_id") or "").strip()
            if song_id:
                song_ids.append(song_id)

        ranked[user_key] = _deduplicate_keep_order(song_ids)

    return ranked, total_rows


def _load_positive_by_user(interactions_jsonl: Path) -> dict[str, set[str]]:
    positives: dict[str, set[str]] = {}
    for row in _iter_jsonl(interactions_jsonl):
        if _to_int(row.get("label"), default=0) <= 0:
            continue

        user_key = str(row.get("user_key") or "").strip()
        song_id = str(row.get("song_id") or "").strip()
        if not user_key or not song_id:
            continue

        user_set = positives.setdefault(user_key, set())
        user_set.add(song_id)

    return positives


def _build_global_hot_from_train(interactions_train_jsonl: Path) -> list[str]:
    counter: Counter[str] = Counter()
    for row in _iter_jsonl(interactions_train_jsonl):
        if _to_int(row.get("label"), default=0) <= 0:
            continue
        song_id = str(row.get("song_id") or "").strip()
        if song_id:
            counter[song_id] += 1

    # 按播放次数降序，再按 song_id 升序，保证同分稳定。
    sorted_pairs = sorted(counter.items(), key=lambda pair: (-pair[1], pair[0]))
    return [song_id for song_id, _ in sorted_pairs]


def _load_catalog_size(item_index_json: Path) -> int:
    raw = json.loads(item_index_json.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return 0
    count = 0
    for key in raw:
        item_key = str(key)
        if item_key and item_key != "__UNK__":
            count += 1
    return count


def _recall_at_k(recommendations: list[str], ground_truth: set[str], k: int) -> float:
    if k <= 0 or not ground_truth:
        return 0.0
    top_k = recommendations[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for song_id in top_k if song_id in ground_truth)
    return hits / len(ground_truth)


def _ndcg_at_k(recommendations: list[str], ground_truth: set[str], k: int) -> float:
    if k <= 0 or not ground_truth:
        return 0.0

    top_k = recommendations[:k]
    if not top_k:
        return 0.0

    dcg = 0.0
    for rank, song_id in enumerate(top_k, start=1):
        if song_id in ground_truth:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(len(ground_truth), k)
    if ideal_hits <= 0:
        return 0.0
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_two_tower_ranked_results(
    *,
    ranked_jsonl: Path,
    interactions_train_jsonl: Path,
    interactions_test_jsonl: Path,
    item_index_json: Path,
    report_json: Path,
    ks: list[int] | tuple[int, ...] = (10, 50),
) -> TwoTowerEvaluationSummary:
    """评估 two_tower 排序结果，并给出与 global_hot 的基线对比。"""
    normalized_ks = sorted({int(k) for k in ks if int(k) > 0})
    if not normalized_ks:
        raise ValueError("ks 至少需要一个正整数")

    ranked_by_user, total_ranked_users = _load_ranked_by_user(ranked_jsonl)
    test_positive_by_user = _load_positive_by_user(interactions_test_jsonl)
    global_hot_list = _build_global_hot_from_train(interactions_train_jsonl)
    catalog_size = _load_catalog_size(item_index_json)

    evaluable_users = 0
    two_tower_recall_sum = {k: 0.0 for k in normalized_ks}
    two_tower_ndcg_sum = {k: 0.0 for k in normalized_ks}
    global_hot_recall_sum = {k: 0.0 for k in normalized_ks}
    global_hot_ndcg_sum = {k: 0.0 for k in normalized_ks}

    two_tower_coverage_items = {k: set() for k in normalized_ks}
    global_hot_coverage_items = {k: set() for k in normalized_ks}

    for user_key, ground_truth in test_positive_by_user.items():
        if not ground_truth:
            continue
        evaluable_users += 1

        ranked_items = ranked_by_user.get(user_key, [])
        hot_items = global_hot_list

        for k in normalized_ks:
            two_tower_recall_sum[k] += _recall_at_k(ranked_items, ground_truth, k)
            two_tower_ndcg_sum[k] += _ndcg_at_k(ranked_items, ground_truth, k)

            global_hot_recall_sum[k] += _recall_at_k(hot_items, ground_truth, k)
            global_hot_ndcg_sum[k] += _ndcg_at_k(hot_items, ground_truth, k)

            two_tower_coverage_items[k].update(ranked_items[:k])
            global_hot_coverage_items[k].update(hot_items[:k])

    def _avg(value: float) -> float:
        if evaluable_users <= 0:
            return 0.0
        return value / evaluable_users

    two_tower_recall_at_k = {
        str(k): round(_avg(two_tower_recall_sum[k]), 6) for k in normalized_ks
    }
    two_tower_ndcg_at_k = {
        str(k): round(_avg(two_tower_ndcg_sum[k]), 6) for k in normalized_ks
    }
    global_hot_recall_at_k = {
        str(k): round(_avg(global_hot_recall_sum[k]), 6) for k in normalized_ks
    }
    global_hot_ndcg_at_k = {
        str(k): round(_avg(global_hot_ndcg_sum[k]), 6) for k in normalized_ks
    }

    if catalog_size <= 0:
        two_tower_coverage_at_k = {str(k): 0.0 for k in normalized_ks}
        global_hot_coverage_at_k = {str(k): 0.0 for k in normalized_ks}
    else:
        two_tower_coverage_at_k = {
            str(k): round(len(two_tower_coverage_items[k]) / catalog_size, 6)
            for k in normalized_ks
        }
        global_hot_coverage_at_k = {
            str(k): round(len(global_hot_coverage_items[k]) / catalog_size, 6)
            for k in normalized_ks
        }

    comparison = {}
    for k in normalized_ks:
        key = str(k)
        comparison[key] = {
            "recall_improved": two_tower_recall_at_k[key] > global_hot_recall_at_k[key],
            "ndcg_improved": two_tower_ndcg_at_k[key] > global_hot_ndcg_at_k[key],
            "coverage_improved": two_tower_coverage_at_k[key]
            > global_hot_coverage_at_k[key],
        }

    report_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "ranked_jsonl": str(ranked_jsonl),
            "interactions_train_jsonl": str(interactions_train_jsonl),
            "interactions_test_jsonl": str(interactions_test_jsonl),
            "item_index_json": str(item_index_json),
        },
        "summary": {
            "total_ranked_users": total_ranked_users,
            "evaluable_users": evaluable_users,
            "catalog_size": catalog_size,
            "ks": normalized_ks,
        },
        "two_tower": {
            "recall_at_k": two_tower_recall_at_k,
            "ndcg_at_k": two_tower_ndcg_at_k,
            "coverage_at_k": two_tower_coverage_at_k,
        },
        "global_hot_baseline": {
            "recall_at_k": global_hot_recall_at_k,
            "ndcg_at_k": global_hot_ndcg_at_k,
            "coverage_at_k": global_hot_coverage_at_k,
        },
        "comparison": comparison,
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerEvaluationSummary(
        total_ranked_users=total_ranked_users,
        evaluable_users=evaluable_users,
        ks=normalized_ks,
        report_path=str(report_json),
        two_tower_recall_at_k=two_tower_recall_at_k,
        two_tower_ndcg_at_k=two_tower_ndcg_at_k,
        two_tower_coverage_at_k=two_tower_coverage_at_k,
        global_hot_recall_at_k=global_hot_recall_at_k,
        global_hot_ndcg_at_k=global_hot_ndcg_at_k,
        global_hot_coverage_at_k=global_hot_coverage_at_k,
    )


def summary_to_json(summary: TwoTowerEvaluationSummary) -> str:
    """将评估摘要转为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
