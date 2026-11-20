# farga

*The forge where concepts become projects* — a concept-to-PR pipeline over the
personal stack. The **manifest is the single contract** (`farga.yaml`); the
skill, the CLI and the future TUI all read and write the same file. Design:
`drafts/11-farga-pipeline-factory.md`.

## The pipeline (stages → commands)

| Stage | Command | What it does | Delegates to |
|---|---|---|---|
| S0 concept | `farga new <dir>` | git repo (**before** harness install — lesson #2) + concept.md skeleton | — |
| S2 architect | `farga architect` | draft `farga.yaml` from flags + the piece catalog + S5-collapsed model defaults | — |
| check | `farga validate` | schema + catalog ids + wires | — |
| S3 routing | `farga route [--debrief FILE]` | write `.farga/proposal.txt` (greenfield defaults, or a saved `debrief.routing_propose` verbatim); validates against the project registry; **never applies** | — |
| S3 gate | `farga apply` | the human gate — thin wrapper | `buildwright roles apply` |
| S4/S5 scaffold | `farga up [--dry-run]` | harness install (literal manifest flags) + project `models.yaml` from the wire table + `.gitignore` + initial commit | `harness/install.sh` |
| S6 execute | `farga run -- --features 2` | the feature queue with parked gates | `buildwright harness run` |
| glance | `farga status` | manifest + board + applied routing + missing artifacts | — |

## Invariants (non-negotiable)

1. `farga.yaml` is the only contract — no field is invented at runtime.
2. Routing changes never bypass `buildwright roles apply`: proposals are text
   with `why bench:` evidence, applied behind a human gate.
3. **S5 hard constraint** (skill `llama-slots`): one llama-server hosts ONE
   model; the roles of a single buildwright run are sequential in one process,
   so they all serve from the same server. Never 8999 and 8080 at once.
4. Evidence or it did not happen — gate logs live in `harness/logs/`.

## Install

```bash
uv sync
uv run farga --help
```

## Development

```bash
uv run pytest          # 30 tests (schema, catalog, proposal, scaffold, cli)
uv run ruff check .
```
