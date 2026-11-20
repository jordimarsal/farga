from __future__ import annotations

from pathlib import Path

from farga.proposal import (
    NOT_APPLIED,
    parse_plus_lines,
    registry_ids,
    render_greenfield,
    validate_against,
)
from farga.schema import Models


def test_render_greenfield_all_same_server(manifest_dict):
    models = Models.model_validate(manifest_dict["models"])
    text = render_greenfield(models, ".farga/proposal.txt")
    lines = parse_plus_lines(text)
    assert lines == [
        ("planner", "local/gemma4"),
        ("worker", "local/gemma4"),
        ("reviewer", "local/gemma4"),
    ]
    assert text.count("why bench:") == 3
    assert "S5 llama-slots" in text  # same-server rationale present
    assert NOT_APPLIED in text


def test_render_greenfield_mixed_servers_drops_s5_prefix(manifest_dict):
    """The collapse rationale only prefixes a why when all roles share one server."""
    manifest_dict["models"].update(
        planner="local/qwen36", worker="local/gemma4", reviewer="local/strata"
    )
    text = render_greenfield(Models.model_validate(manifest_dict["models"]))
    assert text.count("un servidor carrega un sol model") == 0  # no why carries it
    assert text.count("why bench:") == 3


def test_parse_plus_lines_ignores_minus_and_noise():
    text = (
        "proposal: BW_ROLE_WORKER\n"
        "- BW_ROLE_WORKER=local/qwen36\n"  # a - line can never apply
        "+ BW_ROLE_WORKER=local/gemma4\n"
        "why bench: fleet-eval 10/10\n"
        "+ BW_ROLE_WEIRD=local/x\n"  # parsed, but validate flags the role
    )
    assert parse_plus_lines(text) == [("worker", "local/gemma4"), ("weird", "local/x")]


def test_validate_against_registry(tmp_path: Path):
    models_yaml = tmp_path / "models.yaml"
    models_yaml.write_text(
        "models:\n  - id: local/gemma4\n    model: m1\n  - id: local/strata\n    model: m2\n",
        encoding="utf-8",
    )
    known = registry_ids(models_yaml)
    assert known == {"local/gemma4", "local/strata"}

    ok = validate_against([("planner", "local/gemma4")], known)
    assert ok == []

    errs = validate_against(
        [("planner", "local/gemma4"), ("chef", "local/strata"), ("worker", "remote/none")],
        known,
    )
    assert any("role 'chef' unknown" in e for e in errs)
    assert any("'remote/none' not in project models.yaml" in e for e in errs)


def test_registry_ids_missing_file_is_empty(tmp_path):
    assert registry_ids(tmp_path / "nope.yaml") == set()
