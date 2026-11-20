from __future__ import annotations

import pytest

from farga.scaffold import (
    GITIGNORE_BLOCK,
    ensure_gitignore,
    installer_argv,
    render_models_yaml,
)
from farga.schema import Architecture, Manifest, Stack, Tool, Workflow
from farga.wires import UnknownWire


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
    with pytest.raises(UnknownWire, match="extend farga.wires.WIRES"):
        render_models_yaml(Manifest.model_validate(manifest_dict))


def test_ensure_gitignore_idempotent():
    once = ensure_gitignore("harness/backup/\n")
    assert ".farga/" in once and ".env" in once
    twice = ensure_gitignore(once)
    assert twice == once
    assert twice.count(GITIGNORE_BLOCK) == 1
    assert ensure_gitignore("") == GITIGNORE_BLOCK
