"""Evidence strings: why a model serves a role.

Every routing line carries its evidence (the debrief contract: proposals are
text with `why bench:` citations). Sources: ASSIGNACIO.md § dispatch map
(fleet-eval 2026-11-15) and ggufbench v5. No number invented here.
"""

from __future__ import annotations

from farga.schema import Models

S5_RULE = (
    "S5 llama-slots — un servidor carrega un sol model i els rols d'un run son "
    "sequencials al mateix proces; tots els rols al mateix servidor"
)

WHY_BENCH: dict[str, str] = {
    "local/gemma4": (
        "fleet-eval — unic 10/10 (implementar) + 10/10 (reproduir) de la flota; "
        "2n millor revisor (unics que van veure el bug < vs <=). ASSIGNACIO § dispatch"
    ),
    "local/qwen36": (
        "v5 OFF 0.88 global (tools 0.94, agent 0.92), el mes rapid (207 t/s); "
        "fluix en codi amb casos borde (A 7/10) i diagnostic. ASSIGNACIO § dispatch"
    ),
    "local/strata": (
        "fleet-eval B 10/10 (revisar) i D 7/7 (diagnosticar) — referencia de "
        "l'estol; lent (74 t/s), viu a 8080. ASSIGNACIO § dispatch"
    ),
    "local/qwen38": (
        "model diari (13 GB, mes VRAM lliure); codi NOMES amb thinking ON i "
        "sostre >=16k. ASSIGNACIO § dispatch"
    ),
}

# The dispatch map, per role — collapsed to one server by S5 before it reaches
# a manifest (see default_models).
DISPATCH_MAP: dict[str, str] = {
    "planner": "local/qwen36",
    "worker": "local/gemma4",
    "reviewer": "local/strata",
}


def why_for(model: str, all_same_server: bool) -> str:
    base = WHY_BENCH.get(model, "registry local; sense mesura dedicada al mapa")
    return f"{S5_RULE}. {base}" if all_same_server else base


def default_models(preferred: str = "local/gemma4") -> Models:
    """S5-collapsed defaults: every role on `preferred`, dispatch map as alternatives."""
    return Models(
        planner=preferred,
        worker=preferred,
        reviewer=preferred,
        alternatives={
            "review_heavy": DISPATCH_MAP["reviewer"],
            "fast_tools": DISPATCH_MAP["planner"],
        },
    )
