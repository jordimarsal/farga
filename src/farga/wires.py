"""Wire table: registry id -> server endpoint and served model name.

Source of truth for endpoints/aliases is the OpenCode global config
(~/.config/opencode/opencode.json) plus the ASSIGNACIO.md context pins; this
table is the snapshot farga renders project-local models.yaml from. Extend it
when a new model enters the fleet.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Wire:
    base_url: str
    model: str
    context_window: int


WIRES: dict[str, Wire] = {
    "local/gemma4": Wire(
        base_url="http://127.0.0.1:8999/v1",
        model="gemma-4-26B-A4B-it-UD-Q5_K_XL",
        context_window=184748,  # per slot with 2 slots (live pin)
    ),
    "local/qwen36": Wire(
        base_url="http://127.0.0.1:8999/v1",
        model="qwen36-35b-distill-mxfp4_moe",
        context_window=49061,  # per slot with 2 slots
    ),
    "local/qwen38": Wire(
        base_url="http://127.0.0.1:8999/v1",
        model="Qwen3.8-27B-UD-Q3_K_XL",
        context_window=131072,  # per slot with 2 slots (its -c pin is 262144)
    ),
    "local/strata": Wire(
        base_url="http://127.0.0.1:8080/v1",
        model="qwen3.8-flash-next-iq3_xxs",
        context_window=131072,
    ),
}

# llama-slots hard rules, quoted verbatim in generated files.
SERVER_RULES = """\
# REGLES DE SERVIDORS (skill llama-slots):
#  - Regla d'or: MAI 8999 i 8080 alhora (es disputen la VRAM de les dues RTX 5080).
#  - Un servidor llama.cpp carrega UN sol model amb N slots -> els tres rols d'un
#    mateix run de buildwright (plan->execute->review, seqüencials) han de
#    servir-se del MATEIX servidor i model, o de remots.
"""


class UnknownWire(KeyError):
    """A registry id with no wire entry — extend WIRES first."""


def wire_for(registry_id: str) -> Wire:
    try:
        return WIRES[registry_id]
    except KeyError:
        raise UnknownWire(
            f"no wire for '{registry_id}' (known: {', '.join(sorted(WIRES))}) — "
            "extend farga.wires.WIRES or add the entry to the project models.yaml by hand"
        ) from None
