from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import VALID_MANIFEST, write_manifest
from farga_core.schema import Manifest, load_manifest


def test_valid_manifest_loads(manifest_dict, tmp_path):
    manifest = load_manifest(write_manifest(tmp_path, manifest_dict))
    assert manifest.concept.status.value == "building"
    assert manifest.stack.modules == ["vertical-slices"]
    assert manifest.models.by_role("worker") == "local/gemma4"


def test_bad_api_version_refused(manifest_dict):
    manifest_dict["apiVersion"] = "farga/v1"
    with pytest.raises(ValidationError, match="apiVersion"):
        Manifest.model_validate(manifest_dict)


def test_bad_model_prefix_refused(manifest_dict):
    manifest_dict["models"]["worker"] = "gemma4"  # missing local/ remote/ litellm/
    with pytest.raises(ValidationError, match="model id"):
        Manifest.model_validate(manifest_dict)


def test_bad_alternative_prefix_refused(manifest_dict):
    manifest_dict["models"]["alternatives"]["fast_tools"] = "qwen36-bare"
    with pytest.raises(ValidationError, match="alternative"):
        Manifest.model_validate(manifest_dict)


def test_size_L_requires_gauntlet(manifest_dict):
    manifest_dict["execution"]["size"] = "L"
    with pytest.raises(ValidationError, match="gauntlet"):
        Manifest.model_validate(manifest_dict)
    manifest_dict["stack"]["modules"] = ["gauntlet", "vertical-slices"]
    assert Manifest.model_validate(manifest_dict).execution.size.value == "L"


def test_unknown_role_refused():
    with pytest.raises(KeyError, match="unknown role"):
        Manifest.model_validate(VALID_MANIFEST).models.by_role("chef")


def test_defaults_fill_in(manifest_dict):
    """Optional sections default per the template — only apiVersion+models are hard."""
    minimal = {
        "apiVersion": "farga/v0",
        "models": {"planner": "local/gemma4", "worker": "local/gemma4", "reviewer": "local/strata"},
    }
    manifest = Manifest.model_validate(minimal)
    assert manifest.stack.workflow.value == "hybrid"
    assert manifest.lanes.servers == ["llama8999"]
    assert manifest.execution.size.value == "M"
