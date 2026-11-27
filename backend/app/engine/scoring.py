"""Deterministic economic ranking; no weighted score changes the sort order."""

from collections.abc import Iterable, Mapping
import math
from numbers import Real
from typing import Any


def _sort_value(value: Any, name: str) -> float:
    if value is None:
        return math.inf
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be nonnegative and finite or None")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be nonnegative and finite or None")
    return number


def rank_configurations(results: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return copies ranked by LCOE, then CAPEX, with unknown values last.

    Exact ties retain input order. A one-based ``rank`` is added to each copy;
    neither input records nor their nested economics mappings are modified.
    """
    records = []
    for result in results:
        if not isinstance(result, Mapping) or not isinstance(result.get("economics"), Mapping):
            raise ValueError("each configuration must contain an economics mapping")
        economics = result["economics"]
        key = (_sort_value(economics.get("lcoe"), "lcoe"), _sort_value(economics.get("capex"), "capex"))
        records.append((key, dict(result)))
    records.sort(key=lambda item: item[0])
    return [dict(record, rank=index) for index, (_, record) in enumerate(records, start=1)]
