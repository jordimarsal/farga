from __future__ import annotations

import json

from conftest import write_catalog
from farga_core.catalog import check_pieces, load_catalog
from farga_core.schema import Manifest


def test_known_pieces_pass(manifest_dict, tmp_path):
    catalog = load_catalog(write_catalog(tmp_path))
    manifest = Manifest.model_validate(manifest_dict)
    assert check_pieces(manifest, catalog) == []


def test_unknown_piece_reported(manifest_dict, tmp_path):
    manifest_dict["pieces"].append({"id": "nope", "role": "ghost"})
    catalog = load_catalog(write_catalog(tmp_path))
    manifest = Manifest.model_validate(manifest_dict)
    errors = check_pieces(manifest, catalog)
    assert len(errors) == 1
    assert "'nope' not in catalog" in errors[0]
    assert "mcp-reddit" in errors[0]  # known ids listed in the refusal


def test_command_shape_validated(tmp_path):
    """A malformed `command` (incident #8: an assumed command broke a demo)
    fails at load time, not mid-demo."""
    base = {"pieces": [{"id": "x", "command": ["uv", "run", "x"]}]}
    good = tmp_path / "good.json"
    good.write_text(json.dumps(base), encoding="utf-8")
    catalog = load_catalog(good)
    from farga_core.catalog import piece_command

    assert piece_command(catalog["x"]) == ["uv", "run", "x"]

    for bad in (["uv", ""], "uv run x", []):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"pieces": [{"id": "x", "command": bad}]}), encoding="utf-8")
        try:
            load_catalog(p)
        except ValueError as exc:
            assert "command must be" in str(exc)
        else:
            raise AssertionError(f"expected ValueError for command={bad!r}")

    piece = {"id": "lib", "command": None}
    assert piece_command(piece) is None
