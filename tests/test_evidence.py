"""Tests de l'honest pass d'evidence (campanya fleet-eval 2026-11-23)."""

from farga.evidence import DISPATCH_MAP, NULL_RESULTS, WHY_BENCH, default_models, why_for


def test_no_planner_entry_in_dispatch_map() -> None:
    """P2b va enterrar el senyal de planner: el mapa no el pot tornar a oferir."""
    assert "planner" not in DISPATCH_MAP
    assert set(DISPATCH_MAP) == {"worker", "reviewer"}


def test_null_results_cite_fleet_eval_commits() -> None:
    """Cada senyal mort porta la seva cita (commit de fleet-eval)."""
    assert "6a5bb2f" in NULL_RESULTS["planner"]
    assert "775120f" in NULL_RESULTS["reviewer"]
    assert "P2b" in NULL_RESULTS["planner"]
    assert "McNemar" in NULL_RESULTS["reviewer"]


def test_default_models_keeps_bw_role_compat_and_alternatives() -> None:
    models = default_models()
    assert models.planner == "local/gemma4"
    assert models.worker == "local/gemma4"
    assert models.reviewer == "local/gemma4"
    assert models.alternatives == {
        "review_heavy": "local/strata",
        "fast_tools": "local/qwen36",
    }


def test_strata_why_is_convention_not_measurement() -> None:
    why = why_for("local/strata", all_same_server=False)
    assert "REFERENCIA per convencio" in why
    assert "0.86" in why  # sintetica
    assert "0.27" in why  # C2 reals


def test_gemma4_why_carries_both_sides() -> None:
    """Senyal d'implementer viva + advertencia de ressenyador (C2 0.18)."""
    why = why_for("local/gemma4", all_same_server=False)
    assert "10/10" in why
    assert "0.18" in why


def test_unknown_model_falls_back_to_registry_line() -> None:
    why = why_for("local/desconegut", all_same_server=False)
    assert why == "registry local; sense mesura dedicada al mapa"


def test_s5_rule_prepends_when_single_server() -> None:
    why = why_for("local/qwen38", all_same_server=True)
    assert why.startswith("S5 llama-slots")
    assert "thinking ON" in why


def test_every_dispatch_map_model_has_why_bench_entry() -> None:
    for model in DISPATCH_MAP.values():
        assert model in WHY_BENCH


def test_whys_mention_c2_for_review_capable_models() -> None:
    """Els models que podrien fer de ressenyador duen el seu numero C2."""
    for model in ("local/gemma4", "local/qwen36", "local/strata", "local/minicpm", "local/inkling2"):
        assert "C2" in WHY_BENCH[model], model
