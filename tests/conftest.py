from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

VALID_MANIFEST: dict = {
    "apiVersion": "farga/v0",
    "concept": {"file": "concept.md", "profile": "profile.md", "status": "building"},
    "stack": {
        "tool": "opencode",
        "workflow": "hybrid",
        "architecture": "modular-monolith",
        "modules": ["vertical-slices"],
    },
    "pieces": [
        {"id": "mcp-reddit", "role": "test-backend", "config": {}},
        {"id": "mcp-png", "role": "test-backend"},
    ],
    "models": {
        "planner": "local/gemma4",
        "worker": "local/gemma4",
        "reviewer": "local/gemma4",
        "alternatives": {"review_heavy": "local/strata", "fast_tools": "local/qwen36"},
    },
    "routing": {
        "source": "debrief",
        "mode": "propose-then-confirm",
        "proposal": ".farga/proposal.txt",
    },
    "execution": {"runner": "buildwright", "features_per_run": 2, "auto": False, "size": "M"},
    "lanes": {"slots": 2, "servers": ["llama8999"]},
    "observability": {"trace": "langfuse", "evidence": "harness/logs/"},
}

CATALOG: dict = {
    "version": 0,
    "pieces": [
        {
            "id": "mcp-reddit",
            "kind": "mcp",
            "repo": "~/x",
            "provides": [],
            "needs": [],
            "integration": "reference",
            "status": "stable",
            "evidence": "t",
        },
        {
            "id": "mcp-png",
            "kind": "mcp",
            "repo": "~/y",
            "provides": [],
            "needs": [],
            "integration": "reference",
            "status": "stable",
            "evidence": "t",
        },
    ],
}


@pytest.fixture()
def manifest_dict() -> dict:
    return copy.deepcopy(VALID_MANIFEST)


def write_manifest(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "farga.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def write_catalog(tmp_path: Path) -> Path:
    path = tmp_path / "peces.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    return path
