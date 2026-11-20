"""Proposal text: the only artifact that ever changes routing.

Grammar mirrors debrief's routing.propose / buildwright roles apply: blocks of
`proposal:` + `+ BW_ROLE_<ROLE>=<model>` + `why bench:`; only `+` lines are
applyable. farga renders, validates and pipes — it never writes .env itself.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from farga.evidence import why_for
from farga.schema import ROLES, Models

PLUS_RE = re.compile(r"^\+\s*BW_ROLE_([A-Z][A-Z0-9_]*)\s*=\s*(\S+)\s*$", re.MULTILINE)

GREENFIELD_HEADER = """\
# farga — proposta de routing inicial (projecte verd)
# font: defaults ASSIGNACIO.md § «Mapa de dispatch empíric», col·lapsats per la
# restricció de servidors (S5, skill llama-slots). Cap run de buildwright encara;
# S8 (debrief routing_propose) la substituirà per una proposta amb runs reals.
# Aplicació: buildwright roles apply {path}   (gate humà)
"""

NOT_APPLIED = "not applied: farga mai aplica — gate humà via `buildwright roles apply`"


def parse_plus_lines(text: str) -> list[tuple[str, str]]:
    """[(role_lowercase, model_id)] from the `+ BW_ROLE_X=y` lines only."""
    return [(role.lower(), model) for role, model in PLUS_RE.findall(text)]


def render_greenfield(models: Models, proposal_path: str = ".farga/proposal.txt") -> str:
    same_server = len({models.planner, models.worker, models.reviewer}) == 1
    out = [GREENFIELD_HEADER.format(path=proposal_path)]
    for role in ROLES:
        model = models.by_role(role)
        out.append(f"proposal: BW_ROLE_{role.upper()}")
        out.append(f"+ BW_ROLE_{role.upper()}={model}")
        out.append(f"why bench: {why_for(model, same_server)}")
        out.append("")
    out.append(NOT_APPLIED)
    return "\n".join(out) + "\n"


def registry_ids(models_yaml: Path) -> set[str]:
    """Ids declared in a buildwright project-local models.yaml (empty if absent)."""
    if not models_yaml.is_file():
        return set()
    data = yaml.safe_load(models_yaml.read_text(encoding="utf-8")) or {}
    return {entry["id"] for entry in data.get("models", []) if "id" in entry}


def validate_against(lines: list[tuple[str, str]], known_ids: set[str]) -> list[str]:
    """Error strings for unknown roles or models (buildwright would refuse them)."""
    errors: list[str] = []
    for role, model in lines:
        if role not in ROLES:
            errors.append(f"role '{role}' unknown (known: {', '.join(ROLES)})")
        if known_ids and model not in known_ids:
            errors.append(
                f"model '{model}' not in project models.yaml "
                f"(known: {', '.join(sorted(known_ids))})"
            )
    return errors
