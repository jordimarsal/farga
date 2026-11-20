"""Piece catalog: the declarative registry of reusable own-repos.

Lives at ~/.config/farga/peces.json (FARGA_PECES or --catalog to override).
The manifest references pieces by id; this module answers "does it exist?".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from farga.schema import Manifest

DEFAULT_CATALOG = Path.home() / ".config" / "farga" / "peces.json"


def catalog_path(override: str | Path | None = None) -> Path:
    import os

    if override:
        return Path(override).expanduser()
    env = os.environ.get("FARGA_PECES")
    if env:
        return Path(env).expanduser()
    return DEFAULT_CATALOG


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    """Return {piece_id: piece_dict}. Raises json/KeyError as-is on a bad file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return {piece["id"]: piece for piece in data.get("pieces", [])}


def check_pieces(manifest: Manifest, catalog: dict[str, dict[str, Any]]) -> list[str]:
    """Error strings for every manifest piece id missing from the catalog."""
    return [
        f"piece '{ref.id}' not in catalog (known: {', '.join(sorted(catalog)) or '—'})"
        for ref in manifest.pieces
        if ref.id not in catalog
    ]
