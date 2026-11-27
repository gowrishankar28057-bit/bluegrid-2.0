import pytest

from app.engine.carbon import calculate_carbon
from app.engine.scoring import rank_configurations


def test_carbon_includes_assumed_diesel_backup_and_tonne_conversion():
    result = calculate_carbon(900, 100, 0.7, 0.05, 1000)
    assert result["baseline_kg_co2"] == pytest.approx(700)
    assert result["scenario_kg_co2"] == pytest.approx(115)
    assert result["avoided_kg_co2"] == pytest.approx(585)
    assert result["carbon_credit_value"] == pytest.approx(585)


def test_no_renewable_energy_has_no_avoided_emissions():
    result = calculate_carbon(0, 100)
    assert result["avoided_kg_co2"] == 0
    assert result["carbon_credit_value"] == 0
    assert calculate_carbon(0, 0)["baseline_kg_co2"] == 0


def test_negative_avoided_emissions_are_visible_but_do_not_earn_credits():
    result = calculate_carbon(100, 0, 0.5, 0.8, 1000)
    assert result["avoided_kg_co2"] == pytest.approx(-30)
    assert result["carbon_credit_value"] == 0


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_invalid_carbon_inputs_rejected(value):
    with pytest.raises(ValueError):
        calculate_carbon(value, 0)


def test_ranking_is_strictly_lcoe_then_capex_unknown_lcoe_last_and_stable():
    records = [
        {"id": "unknown", "economics": {"lcoe": None, "capex": 0}},
        {"id": "expensive", "economics": {"lcoe": 5, "capex": 0}},
        {"id": "high_capex", "economics": {"lcoe": 4, "capex": 200}},
        {"id": "first_tie", "economics": {"lcoe": 4, "capex": 100}},
        {"id": "second_tie", "economics": {"lcoe": 4, "capex": 100}},
    ]
    ranked = rank_configurations(records)
    assert [row["id"] for row in ranked] == ["first_tie", "second_tie", "high_capex", "expensive", "unknown"]
    assert [row["rank"] for row in ranked] == [1, 2, 3, 4, 5]
    assert all("rank" not in row for row in records)
    assert rank_configurations([]) == []


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True])
def test_ranking_rejects_invalid_numeric_values(value):
    with pytest.raises(ValueError):
        rank_configurations([{"economics": {"lcoe": value, "capex": 10}}])
