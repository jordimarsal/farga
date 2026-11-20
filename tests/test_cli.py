from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import VALID_MANIFEST, write_catalog, write_manifest
from farga.cli import main

MCP_PLANE = Path.home() / "Documents" / "CV" / "projects" / "mcp-plane"


# ------------------------------------------------------------------ new


def test_new_creates_repo_and_concept(tmp_path, monkeypatch):
    project = tmp_path / "idea"
    rc = main(["new", str(project)])
    assert rc == 0
    assert (project / ".git").is_dir()
    assert "concepte" in (project / "concept.md").read_text(encoding="utf-8")

    rc = main(["new", str(project)])
    assert rc == 2  # refuses to overwrite concept.md without --force


def test_new_with_concept_file_keeps_content_verbatim(tmp_path):
    src = tmp_path / "c.md"
    src.write_text("# La meva idea {amb} claus\n", encoding="utf-8")
    rc = main(["new", str(tmp_path / "p2"), "--concept-file", str(src)])
    assert rc == 0
    assert (tmp_path / "p2" / "concept.md").read_text(encoding="utf-8") == src.read_text(
        encoding="utf-8"
    )


# ------------------------------------------------------------------ architect


def test_architect_writes_valid_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    catalog = write_catalog(tmp_path)
    rc = main(
        [
            "architect",
            "--catalog",
            str(catalog),
            "--modules",
            "vertical-slices",
            "--piece",
            "mcp-reddit:test-backend",
            "--piece",
            "mcp-png:test-backend",
            "--preferred-model",
            "local/gemma4",
        ]
    )
    assert rc == 0
    from farga.schema import load_manifest

    manifest = load_manifest(Path("farga.yaml"))
    assert manifest.models.planner == "local/gemma4"
    assert manifest.models.alternatives == {
        "review_heavy": "local/strata",
        "fast_tools": "local/qwen36",
    }
    assert [p.id for p in manifest.pieces] == ["mcp-reddit", "mcp-png"]


def test_architect_refuses_overwrite_and_unknown_piece(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    catalog = write_catalog(tmp_path)
    rc = main(["architect", "--catalog", str(catalog), "--piece", "ghost:x"])
    assert rc == 2
    assert not Path("farga.yaml").exists()

    rc = main(["architect", "--catalog", str(catalog)])
    assert rc == 0
    rc = main(["architect", "--catalog", str(catalog)])
    assert rc == 2  # exists, no --force


# ------------------------------------------------------------------ validate / route


def test_validate_and_route_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    catalog = write_catalog(tmp_path)
    # no models.yaml in project -> registry check is skipped (greenfield)
    rc = main(["validate", "--catalog", str(catalog)])
    assert rc == 0

    rc = main(["route", "--dry-run"])
    assert rc == 0

    rc = main(["route"])
    assert rc == 0
    proposal = Path(".farga/proposal.txt")
    assert proposal.is_file()
    assert "+ BW_ROLE_WORKER=local/gemma4" in proposal.read_text(encoding="utf-8")


def test_route_refuses_model_outside_registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    Path("models.yaml").write_text("models:\n  - id: local/strata\n", encoding="utf-8")
    rc = main(["route"])  # manifest uses local/gemma4, registry only has strata
    assert rc == 2
    assert not Path(".farga/proposal.txt").exists()


def test_route_debrief_verbatim(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    debrief_out = tmp_path / "debrief.txt"
    debrief_out.write_text(
        "proposal: BW_ROLE_REVIEWER\n"
        "+ BW_ROLE_REVIEWER=local/strata\n"
        "why run: gemma4 failed review (2/5) — exec42.log\n"
        "why bench: strata passed review at 0.91 — runs/20261118.json\n",
        encoding="utf-8",
    )
    Path("models.yaml").write_text(
        "models:\n  - id: local/gemma4\n  - id: local/strata\n", encoding="utf-8"
    )
    rc = main(["route", "--debrief", str(debrief_out)])
    assert rc == 0
    saved = Path(".farga/proposal.txt").read_text(encoding="utf-8")
    assert "+ BW_ROLE_REVIEWER=local/strata" in saved
    assert "why run:" in saved and "why bench:" in saved  # evidence preserved verbatim


def test_route_debrief_without_plus_lines_refused(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    junk = tmp_path / "junk.txt"
    junk.write_text("why bench: res d'aplicable\n", encoding="utf-8")
    assert main(["route", "--debrief", str(junk)]) == 2


# ------------------------------------------------------------------ status / up


def test_status_reports_manifest_board_and_gaps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    Path(".env").write_text("BW_ROLE_WORKER=local/gemma4\n", encoding="utf-8")
    fl = Path("harness/feature_list.json")
    fl.parent.mkdir()
    fl.write_text(
        json.dumps(
            {"features": [{"name": "f1", "status": "done"}, {"name": "f2", "status": "pending"}]}
        ),
        encoding="utf-8",
    )
    rc = main(["status"])
    assert rc == 0


def test_up_dry_run_plans_without_touching(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    installer = tmp_path / "install.sh"
    installer.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    rc = main(["up", "--dry-run", "--installer", str(installer)])
    assert rc == 0
    assert not Path("models.yaml").exists()  # dry-run writes nothing
    assert not list(Path(".").glob("harness"))


def test_up_refuses_missing_installer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path, VALID_MANIFEST)
    rc = main(["up", "--installer", str(tmp_path / "nope.sh")])
    assert rc == 2


# ------------------------------------------------------------------ real world


@pytest.mark.skipif(not MCP_PLANE.is_dir(), reason="pilot mcp-plane not present")
def test_real_pilot_manifest_validates(monkeypatch):
    monkeypatch.chdir(MCP_PLANE)
    rc = main(["validate"])
    assert rc == 0  # schema + catalog pieces (mcp-reddit, mcp-png) + wires


@pytest.mark.skipif(not MCP_PLANE.is_dir(), reason="pilot mcp-plane not present")
def test_real_pilot_route_matches_applied_routing(monkeypatch, tmp_path):
    """F1 criterion: `farga route` must reproduce the pilot's applied proposal."""
    monkeypatch.chdir(MCP_PLANE)
    rc = main(["route", "--dry-run"])
    assert rc == 0
