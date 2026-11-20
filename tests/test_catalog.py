from __future__ import annotations

from conftest import write_catalog
from farga.catalog import check_pieces, load_catalog
from farga.schema import Manifest


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
