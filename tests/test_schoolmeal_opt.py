"""Tests for schoolmeal-opt."""

from __future__ import annotations

import json

import pytest

from schoolmeal_opt import MealTarget, optimize_school_meal
from schoolmeal_opt.cli import main as cli_main


def test_simplex_lp_satisfies_all_rda_targets_at_low_cost() -> None:
    plan = optimize_school_meal(students=800, school_days=65)
    assert plan.feasible is True
    assert 700.0 <= plan.kcal_per_meal <= 950.5
    assert plan.protein_g_per_meal >= 19.9
    assert plan.iron_mg_per_meal >= 4.49
    assert plan.vit_a_ug_per_meal >= 199.9
    assert plan.zinc_mg_per_meal >= 2.99
    assert 0.12 <= plan.cost_usd_per_student_meal <= 0.35
    assert plan.term_procurement_kg_by_commodity["maize_flour"] > 3000.0
    assert plan.improved_rocket_stove_firewood_saved_kg > 10000.0


def test_impossible_target_returns_infeasible() -> None:
    impossible = MealTarget(min_kcal=4000.0, max_kcal=4500.0)
    plan = optimize_school_meal(students=100, target=impossible)
    assert plan.feasible is False


def test_cli_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli_main(["--students", "500", "--days", "60"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["feasible"] is True
    assert out["total_term_budget_usd"] > 3000.0
