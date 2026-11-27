from datetime import datetime, timedelta, timezone
import numpy as np
import pytest
from app.data_loader import calendar, numeric_series, demo_dataset, parse_resource_data
from app.validation import normalize_options


def test_huge_integer_series_rejected():
    with pytest.raises(ValueError, match="numbers"):
        numeric_series([10**400], "resource")


def test_calendar_leap_year_and_duplicates():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dates = [(start + timedelta(hours=index)).isoformat() for index in range(8784)]
    months = calendar(dates)
    assert np.count_nonzero(months == 1) == 29 * 24
    dates[100] = dates[99]
    with pytest.raises(ValueError, match="contiguous"):
        calendar(dates)


def test_resources_require_explicit_provenance_and_complete_year():
    demo = demo_dataset()
    data = {"timestamps": list(demo["timestamps"]), "capacity_factors": {"wave": [0.] * 8760}}
    with pytest.raises(ValueError, match="provenance"):
        parse_resource_data(data)
    data["provenance"] = {"source": "test", "synthetic": True}
    data["capacity_factors"]["wave"][5] = 1.1
    with pytest.raises(ValueError, match="<= 1.0"):
        parse_resource_data(data)


def test_options_cannot_be_coerced_from_empty_list():
    with pytest.raises(ValueError, match="object"):
        normalize_options([])
