# farga-core

The headless core of the **farga concept→PR pipeline**. `farga-core` v0.1.0 owns the
manifest, scaffold, routing and execution commands; the `farga` TUI (sibling repository)
is a primary client, not a second implementation.

The manifest (`farga.yaml`) is the single contract. State and evidence live in the
project: `harness/feature_list.json`, `harness/specs/`, `harness/progress/` and
`harness/logs/`.

## Requirements

- Python **3.12+** and [`uv`](https://docs.astral.sh/uv/).
- The [harness](https://github.com/jordimarsal/harness) installer for `up` (default:
  `/home/jordi/Documents/CV/projects/harness/install.sh`).
- [buildwright](https://github.com/jordimarsal/buildwright) for `run`, `apply` and
  `gate`. The CLI prefers the repository-local
  `~/Documents/CV/projects/buildwright/.venv/bin/buildwright`, then `PATH`.
- Exactly one local model server (8999 or 8080) when executing a local-model run.

## Install

```bash
uv sync
uv run farga-core --help
```

Or install the CLI globally from the repository:

```bash
uv tool install --editable /path/to/farga-core
farga-core --version
```

## Pipeline

| Stage | Command | What it does |
|---|---|---|
| S0 concept | `farga-core new <dir>` | Git repo **before** harness install + `concept.md` skeleton |
| S2 architect | `farga-core architect` | Draft `farga.yaml` from flags, catalog and model defaults |
| Check | `farga-core validate` | Schema + catalog ids + model wires |
| S3 routing | `farga-core route` | Write `.farga/proposal.txt`; never apply it |
| S3 gate | `farga-core apply` | Human-gated `buildwright roles apply` |
| S4/S5 scaffold | `farga-core up` | Harness install + project `models.yaml` + `.gitignore` + initial commit |
| S6 execute | `farga-core run` | Buildwright feature loop with parked human gates |
| Gate | `farga-core gate` | `approve`, `reject` or `fix` a parked feature |
| Glance | `farga-core status` | Manifest + board + applied routing + missing artifacts |

## Quickstart

```bash
farga-core new /tmp/my-project
cd /tmp/my-project

# Edit concept.md, then draft the manifest
farga-core architect \
  --architecture modular-monolith \
  --tool opencode \
  --preferred-model local/strata

farga-core validate
farga-core up
bash harness/init.sh
farga-core status
```

`new` creates `concept.md`; `architect` creates `farga.yaml`; `up` installs the harness
and writes the project-local `models.yaml`.

> **`up` has no path argument.** It scaffolds into the current working directory. Run
> it from the project root. Use `farga-core up --dry-run` to inspect the plan first.

The initial commit includes only paths that actually exist. A fresh scaffold has no
`pyproject.toml`; requiring it in the commit pathspec used to break the
`new → architect → up` chain.

## Execute and resolve gates

Start exactly one model server, then:

```bash
farga-core run -y -- --max-tasks 1
```

`-y` skips the interactive start prompt, not the human gates. `--max-tasks 1` keeps
prompts small and review batches narrow.

When the loop parks:

```bash
farga-core gate fix --feature my_feature "concrete changes for the implementer"
farga-core gate approve --feature my_feature "verification evidence"
farga-core gate reject --feature my_feature "reason"
```

At a Completion Gate, verify tests and traceability, reproduce the feature demo, then
approve. Approval merges the feature worktree into `main`, records the decision and
marks the feature `done`.

## Routing

```bash
farga-core route
# review .farga/proposal.txt
farga-core apply
```

`route` only proposes. `apply` is the human gate. Routing changes never bypass
`buildwright roles apply`.

## Invariants

1. `farga.yaml` is the only contract — no field is invented at runtime.
2. Routing proposals carry evidence and are applied only behind a human gate.
3. One llama.cpp server hosts one model; all roles of a single sequential run use it.
4. Never run 8999 and 8080 at the same time on the two-GPU rig.
5. Evidence or it did not happen: gate logs live in `harness/logs/`.

## Development

```bash
uv run pytest -q                 # 50 passed
uv run ruff check .
uv run mypy --strict src/farga_core
```

`ruff format --check .` currently flags one pre-existing file outside this change.
