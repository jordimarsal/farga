"""Evidence strings: why a model serves a role.

Every routing line carries its evidence (the debrief contract: proposals are
text with `why bench:` citations). Sources, newest first:

  - fleet-eval 2026-11-23 (P2b reduida n=8, C2 n=33): TWO role signals were
    measured and BURIED. NULL_RESULTS below records both with citations so no
    proposal re-routes on them. The reviewer leaderboard also demonstrated the
    winner's curse live (minicpm 0.56 at n=9 -> 0.27 at n=33).
  - ASSIGNACIO.md S dispatch map (fleet-eval 2026-11-15): the IMPLEMENTER
    signal survived every gate (gemma4, only 10/10 + 10/10 of the fleet).
  - ggufbench v5 by_lang: worker-per-language selection — the only live
    best-of-breed channel.

No number invented here; every cited figure lives in the fleet-eval repo
(github.com/jordimarsal/fleet-eval) or ggufbench's report.
"""

from __future__ import annotations

from farga.schema import Models

S5_RULE = (
    "S5 llama-slots — un servidor carrega un sol model i els rols d'un run son "
    "sequencials al mateix proces; tots els rols al mateix servidor"
)

# Signals measured and buried on 2026-11-23. Routing on these roles is not
# evidence-based: any proposal that re-introduces them must first beat these
# nulls with a larger corpus (see fleet-eval docs/ARTICLE-NOTES.md).
NULL_RESULTS: dict[str, str] = {
    "planner": (
        "SENVAL NO (P2b reduida, fleet-eval 6a5bb2f): pla huma 0.198 vs Huihui "
        "0.204 sobre 8 tasques amb el mateix executor — 0 victories de l'huma. "
        "El planning no s'enruta per model: el fa l'agent de la sessio. "
        "Desempat sota nul, si algú aïlla el rol per velocitat: qwen36 "
        "(207 t/s, cap mesura de planner en contra); MAI el qwen4b — ultim a "
        "P v2 (ratio 1.95, 4B baix) i col·lapse 0/20 a P01 de P2b. Aixo es "
        "POLITICA de desempat, no evidencia de qualitat."
    ),
    "reviewer": (
        "SENVAL PLA (C2 n=33, fleet-eval 775120f): banda 0.12-0.33, McNemar "
        "aparellat sense cap parell significatiu (p minima 0.18). Winner's "
        "curse demostrat: minicpm 0.56 (n=9) -> 0.27 (n=33). Strata es "
        "REFERENCIA per convencio (sintetica C 0.86), no per mesura."
    ),
}

WHY_BENCH: dict[str, str] = {
    "local/gemma4": (
        "fleet-eval dispatch 2026-11-15: unic 10/10 (implementar) + 10/10 "
        "(reproduir) — l'unic senyal de rol que va sobreviure les portes del "
        "23-11. Com a ressenyador de defectes reals NO: C2 6/33 (0.18). "
        "ASSIGNACIO S dispatch"
    ),
    "local/qwen36": (
        "v5 OFF 0.88 global (tools 0.94, agent 0.92), el mes rapid (207 t/s); "
        "alternativa fast_tools NOMES — com a ressenyor el mes sorollos de la "
        "flota (C2: 0.18 recall, 239 FP). ASSIGNACIO S dispatch"
    ),
    "local/strata": (
        "REFERENCIA per convencio (NULL_RESULTS['reviewer']): sintetica C 0.86, "
        "B 10/10, D 7/7; defectes reals C2 9/33 (0.27), banda alta sense "
        "significancia. lent (74 t/s), viu a 8080. ASSIGNACIO S dispatch"
    ),
    "local/qwen38": (
        "model diari (13 GB, mes VRAM lliure); codi NOMES amb thinking ON i "
        "sostre >=16k. ASSIGNACIO S dispatch"
    ),
    "local/minicpm": (
        "C2 9/33 (0.27): el guanyador de la primera onada (0.56 a n=9) era "
        "winner's curse. v5 global 0.85; visio via mmproj. model diari "
        "alternatiu, mai ressenyor per ranking"
    ),
    "local/inkling2": (
        "C2 11/33 (0.33) capdavanter NOMINAL sense cap parell significatiu "
        "(McNemar p>=0.18); dispatch E 5/5. Inkling 2 Mini (26.2B MoE looped, "
        "layout Mainline_Support). També inestable en servei el seu germà "
        "uncensored (2 crashes documentats)."
    ),
}

# The dispatch map, per role — collapsed to one server by S5 before it reaches
# a manifest (see default_models). No "planner" entry: planning is not routed
# per model (NULL_RESULTS["planner"]).
DISPATCH_MAP: dict[str, str] = {
    "worker": "local/gemma4",
    "reviewer": "local/strata",
}


def why_for(model: str, all_same_server: bool) -> str:
    base = WHY_BENCH.get(model, "registry local; sense mesura dedicada al mapa")
    return f"{S5_RULE}. {base}" if all_same_server else base


def default_models(preferred: str = "local/gemma4") -> Models:
    """S5-collapsed defaults: every role on `preferred`, dispatch map as alternatives.

    The planner field stays for BW_ROLE_* compatibility (buildwright expects the
    three roles) but carries no routing claim: it rides `preferred` like the
    rest, and NULL_RESULTS["planner"] documents why no map entry exists.
    """
    return Models(
        planner=preferred,
        worker=preferred,
        reviewer=preferred,
        alternatives={
            "review_heavy": DISPATCH_MAP["reviewer"],
            "fast_tools": "local/qwen36",
        },
    )
