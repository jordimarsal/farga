from __future__ import annotations

import pytest

from farga_core.scaffold import (
    GITIGNORE_BLOCK,
    commit_paths_for,
    ensure_gitignore,
    ensure_stack_markers,
    installer_argv,
    remove_stack_markers,
    render_models_yaml,
)
from farga_core.schema import Architecture, Manifest, Stack, Tool, Workflow
from farga_core.wires import UnknownWire


def _stack(modules: list[str]) -> Stack:
    return Stack(
        tool=Tool.opencode,
        workflow=Workflow.hybrid,
        architecture=Architecture.modular_monolith,
        modules=modules,
    )


def test_installer_argv_literal_flags():
    argv = installer_argv(_stack(["gauntlet", "vertical-slices"]))
    assert argv == [
        "--tool=opencode",
        "--workflow=hybrid",
        "--architecture=modular-monolith",
        "--modules=gauntlet,vertical-slices",
    ]


def test_installer_argv_no_modules_omits_flag():
    assert "--modules" not in " ".join(installer_argv(_stack([])))


def test_render_models_yaml_roles_then_alternatives(manifest_dict):
    text = render_models_yaml(Manifest.model_validate(manifest_dict))
    assert text.index("id: local/gemma4") < text.index("id: local/strata")
    assert text.index("id: local/strata") < text.index("id: local/qwen36")
    assert "gemma-4-26B-A4B-it-UD-Q5_K_XL" in text
    assert "qwen3.8-flash-next-iq3_xxs" in text
    assert "REGLES DE SERVIDORS" in text  # the llama-slots rules ride along


def test_render_models_yaml_unknown_wire_lists_known(manifest_dict):
    manifest_dict["models"]["alternatives"]["daily"] = "local/sc117"
    with pytest.raises(UnknownWire, match="extend farga_core.wires.WIRES"):
        render_models_yaml(Manifest.model_validate(manifest_dict))


def test_stack_markers_are_created_and_removed(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()

    created = ensure_stack_markers(project, "typescript")

    assert [path.name for path in created] == ["tsconfig.json"]
    assert (project / "tsconfig.json").is_file()
    remove_stack_markers(project, created)
    assert not (project / "tsconfig.json").exists()


def test_existing_stack_marker_is_never_removed(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "package.json").write_text('{"name":"real"}', encoding="utf-8")

    created = ensure_stack_markers(project, "node")

    assert created == []
    remove_stack_markers(project, created)
    assert (project / "package.json").read_text(encoding="utf-8") == '{"name":"real"}'


def test_android_marker_creates_and_cleans_nested_dirs(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()

    created = ensure_stack_markers(project, "android")
    assert (project / "app" / "src" / "main" / "AndroidManifest.xml").is_file()

    remove_stack_markers(project, created)
    assert not (project / "app").exists()
    assert not (project / "build.gradle").exists()


def test_ensure_gitignore_idempotent():
    once = ensure_gitignore("harness/backup/\n")
    assert ".farga/" in once and ".env" in once
    twice = ensure_gitignore(once)
    assert twice == once
    assert twice.count(GITIGNORE_BLOCK) == 1
    assert ensure_gitignore("") == GITIGNORE_BLOCK


def test_commit_paths_skip_missing(tmp_path):
    """Un scaffold net no té pyproject.toml (l'afegeix el bucle de build): els
    pathspecs inexistents feien fallir `git add` (rc=1) i trencaven la cadena
    new → architect → up que el wizard d'integració verifica en viu."""
    (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
    (tmp_path / "harness").mkdir()
    (tmp_path / "farga.yaml").write_text("y", encoding="utf-8")
    assert commit_paths_for(tmp_path) == ["AGENTS.md", "harness", "farga.yaml"]


def test_commit_paths_empty_when_nothing_exists(tmp_path):
    assert commit_paths_for(tmp_path) == []
