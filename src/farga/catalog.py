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
    """Return {piece_id: piece_dict}. Raises json/KeyError as-is on a bad file.

    Schema (informal, seed-documented in the $comment): every piece carries
    id/kind/repo/provides/needs/integration/status/evidence and an OPTIONAL
    `command` — the EXACT spawn argv for launchable pieces (MCP servers, APIs).
    Incident #8: a command that was assumed (`uv run <script>`) broke the S5
    demo; the catalog now carries the tested argv, and this loader validates
    its shape so a malformed entry fails here, not mid-demo.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    pieces: dict[str, dict[str, Any]] = {}
    for piece in data.get("pieces", []):
        command = piece.get("command")
        if command is not None and (
            not isinstance(command, list)
            or not command
            or not all(isinstance(arg, str) and arg for arg in command)
        ):
            raise ValueError(
                f"piece '{piece.get('id')}': command must be a non-empty list of "
                f"argv strings (saw {command!r})"
            )
        pieces[piece["id"]] = piece
    return pieces


def piece_command(piece: dict[str, Any]) -> list[str] | None:
    """The validated launch argv for a piece, or None (not launchable)."""
    command = piece.get("command")
    return list(command) if command else None


def check_pieces(manifest: Manifest, catalog: dict[str, dict[str, Any]]) -> list[str]:
    """Error strings for every manifest piece id missing from the catalog."""
    return [
        f"piece '{ref.id}' not in catalog (known: {', '.join(sorted(catalog)) or '—'})"
        for ref in manifest.pieces
        if ref.id not in catalog
    ]
