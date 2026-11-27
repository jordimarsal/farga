"""Scaffold: manifest -> executable repo (the S4/S5 steps, scripted).

Lesson #2 from the mcp-plane pilot: `git init` BEFORE harness install, or the
Conventional-Commits hook lands in the enclosing repo's .git.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from farga_core.schema import Manifest, Stack
from farga_core.wires import SERVER_RULES, UnknownWire, wire_for

GITIGNORE_BLOCK = """\
# farga (estat local, proposals)
.farga/

# buildwright routing (.env du BW_ROLE_* i claus)
.env

# python
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
dist/
"""

DEFAULT_INSTALLER = Path.home() / "Documents" / "CV" / "projects" / "harness" / "install.sh"


def installer_argv(stack: Stack) -> list[str]:
    """Manifest stack -> literal harness/install.sh flags."""
    argv = [
        f"--tool={stack.tool.value}",
        f"--workflow={stack.workflow.value}",
        f"--architecture={stack.architecture.value}",
    ]
    if stack.modules:
        argv.append(f"--modules={','.join(stack.modules)}")
    return argv


def render_models_yaml(manifest: Manifest) -> str:
    """Project-local models.yaml: every id the manifest mentions, wired."""
    ids: list[str] = []
    for role in ("planner", "worker", "reviewer"):
        mid = manifest.models.by_role(role)
        if mid not in ids:
            ids.append(mid)
    for mid in manifest.models.alternatives.values():
        if mid not in ids:
            ids.append(mid)

    wires = []
    for mid in ids:
        try:
            wires.append((mid, wire_for(mid)))
        except UnknownWire:
            raise UnknownWire(
                f"manifest uses '{mid}' but no wire is defined for it; either extend "
                "farga_core.wires.WIRES or write the project models.yaml entry by hand"
            ) from None

    lines = [
        (
            "# Model registry del projecte (generat per `farga up`; project-local, "
            "buildwright el prefereix al bundled)."
        ),
        "# Aliasos = els de la config global d'OpenCode (~/.config/opencode/opencode.json).",
        SERVER_RULES.rstrip("\n"),
        "models:",
    ]
    for mid, wire in wires:
        lines += [
            f"  - id: {mid}",
            f"    label: {wire.model} ({wire.base_url})",
            "    kind: local",
            f"    base_url: {wire.base_url}",
            f"    model: {wire.model}",
            f"    context_window: {wire.context_window}",
            "",
        ]
    return "\n".join(lines).rstrip("\n") + "\n"


def ensure_gitignore(current: str) -> str:
    """Append the farga/python block once; idempotent. Normalizes trailing newlines."""
    if ".farga/" in current:
        return current
    body = current.rstrip("\n")
    if not body:
        return GITIGNORE_BLOCK
    return body + "\n\n" + GITIGNORE_BLOCK


def _run(cmd: list[str], cwd: Path | None = None) -> int:
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


# The harness detects the stack from files and verifies a test framework before it
# reports "Environment ready". A new project must ship those files from `up`, otherwise
# the first session starts with a red gate. These files are permanent and committed.
STACK_MARKERS: dict[str, tuple[str, ...]] = {
    "typescript": ("tsconfig.json", "package.json"),
    "node": ("package.json",),
    "python": ("pyproject.toml", "tests"),
    "go": ("go.mod",),
    "java": ("pom.xml",),
    "rust": ("Cargo.toml",),
    "android": ("build.gradle", "app/src/main/AndroidManifest.xml"),
    "generic": (),
}

_SMOKE_MJS = """\
import test from "node:test";
import assert from "node:assert/strict";

test("scaffold is ready", () => assert.equal(1 + 1, 2));
"""

_SMOKE_PY = """\
def test_scaffold_is_ready() -> None:
    assert 1 + 1 == 2
"""

_SMOKE_GO = """\
package main

import "testing"

func TestScaffoldIsReady(t *testing.T) {
	if 1+1 != 2 {
		t.Fatal("scaffold is not ready")
	}
}
"""

_SMOKE_RS = """\
#[test]
fn scaffold_is_ready() {
    assert_eq!(1 + 1, 2);
}
"""


def stack_scaffold_files(language: str, project_name: str) -> dict[str, str]:
    """Minimal real project files with a runnable test suite for the harness."""
    if language in ("typescript", "node"):
        package = {
            "name": project_name,
            "private": True,
            "type": "module",
            "scripts": {
                "test": "node --test tests/*.test.mjs",
                "build": "tsc --noEmit" if language == "typescript" else "echo 'no build step'",
            },
        }
        files = {
            "package.json": json.dumps(package, indent=2) + "\n",
            "tests/smoke.test.mjs": _SMOKE_MJS,
        }
        if language == "typescript":
            files["tsconfig.json"] = (
                json.dumps(
                    {
                        "compilerOptions": {
                            "target": "ES2022",
                            "module": "ESNext",
                            "moduleResolution": "bundler",
                            "strict": True,
                            "noEmit": True,
                        },
                        "include": ["src", "tests"],
                    },
                    indent=2,
                )
                + "\n"
            )
        return files
    if language == "python":
        return {
            "pyproject.toml": (
                "[project]\n"
                f'name = "{project_name}"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.10"\n\n'
                "[tool.pytest.ini_options]\n"
                'testpaths = ["tests"]\n'
            ),
            "tests/test_smoke.py": _SMOKE_PY,
        }
    if language == "go":
        return {
            "go.mod": f"module {project_name}\n\ngo 1.22\n",
            "smoke_test.go": _SMOKE_GO,
        }
    if language == "rust":
        return {
            "Cargo.toml": (
                f'[package]\nname = "{project_name}"\nversion = "0.1.0"\nedition = "2021"\n'
            ),
            "tests/smoke.rs": _SMOKE_RS,
        }
    return {}


def seed_first_feature(project: Path) -> dict[str, object] | None:
    """Seed one pending feature from concept.md when the board is empty.

    `farga-core run` delegates to buildwright, which refuses an empty queue. A
    greenfield project must therefore arrive with a first feature the SDD loop can
    pick up; the spec-author phase refines it from the concept text.
    """
    board = project / "harness" / "feature_list.json"
    concept_file = project / "concept.md"
    if not board.is_file() or not concept_file.is_file():
        return None
    try:
        data = json.loads(board.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("features"):
        return None
    concept = concept_file.read_text(encoding="utf-8").strip()
    if not concept:
        return None
    first_line = next(
        (line.strip() for line in concept.splitlines() if line.strip()), "Projecte inicial"
    )
    title = re.sub(r"^#+\s*", "", first_line)[:100]
    slug = (
        re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:60] or "initial_concept"
    )
    feature = {
        "id": 1,
        "name": slug,
        "title": title,
        "description": concept,
        "acceptance": [
            "Implementa el concepte descrit a concept.md",
            "harness/init.sh passa amb tests verds",
        ],
        "status": "pending",
    }
    data.setdefault("features", []).append(feature)
    fd, temporary = tempfile.mkstemp(dir=str(board.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temporary, board)
    except OSError:
        Path(temporary).unlink(missing_ok=True)
        raise
    return feature


def ensure_stack_scaffold(project: Path, language: str) -> list[Path]:
    """Create the permanent stack files; return the ones this run created."""
    created: list[Path] = []
    real_files = stack_scaffold_files(language, project.name)
    for relative in STACK_MARKERS.get(language, ()):
        if relative in real_files:
            continue  # real content is written below, not an empty marker
        path = project / relative
        if relative in ("tests",) and path.is_dir():
            continue
        if path.exists():
            continue
        if relative.endswith("/") or relative == "tests":
            path.mkdir(parents=True, exist_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n" if path.suffix == ".json" else "", encoding="utf-8")
        created.append(path)
    for relative, content in stack_scaffold_files(language, project.name).items():
        path = project / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(path)
    return created


SCAFFOLD_COMMIT_PATHS = (
    "AGENTS.md",
    "HARNESS.md",
    "opencode.json",
    ".opencode",
    "docs",
    "harness",
    "pyproject.toml",
    "farga.yaml",
    "concept.md",
    "profile.md",
    ".gitignore",
    "models.yaml",
    "package.json",
    "tsconfig.json",
    "tests",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "app",
)


def commit_paths_for(project: Path) -> list[str]:
    """Només els paths que existeixen: un scaffold net no té pyproject.toml (el
    crea el bucle de build) i un pathspec inexistent fa fallir `git add` (rc=1),
    trencant la cadena new → architect → up."""
    return [p for p in SCAFFOLD_COMMIT_PATHS if (project / p).exists()]


def up(
    manifest: Manifest,
    project: Path,
    installer: Path = DEFAULT_INSTALLER,
    dry_run: bool = False,
) -> list[str]:
    """Execute (or plan) the scaffold. Returns the plan; raises on failure."""
    steps: list[tuple[str, list[str]]] = []

    if not (project / ".git").exists():
        steps.append(("git init (abans d'instal·lar — lliçó #2)", ["git", "init", "-b", "main"]))

    steps.append(
        (
            "harness install",
            [
                "bash",
                str(installer.expanduser()),
                *installer_argv(manifest.stack),
                "--dest",
                str(project),
            ],
        )
    )
    steps.append(("models.yaml del projecte", []))  # file write, below
    steps.append((".gitignore + .farga/", []))

    plan = [f"{label}: {' '.join(cmd) if cmd else '(fitxers)'}" for label, cmd in steps]
    if dry_run:
        plan.append("commit inicial: harness/tools/commit.sh -m 'chore(scaffold): …'")
        return plan

    project.mkdir(parents=True, exist_ok=True)
    ensure_stack_scaffold(project, manifest.stack.language.value)
    for label, cmd in steps:
        if not cmd:
            continue
        rc = _run(cmd)
        if rc != 0:
            raise RuntimeError(f"scaffold step failed (rc={rc}): {label}")

    seed_first_feature(project)
    (project / "models.yaml").write_text(render_models_yaml(manifest), encoding="utf-8")
    gi = project / ".gitignore"
    gi.write_text(
        ensure_gitignore(gi.read_text(encoding="utf-8") if gi.is_file() else ""), encoding="utf-8"
    )
    (project / ".farga").mkdir(exist_ok=True)

    commit_sh = project / "harness" / "tools" / "commit.sh"
    rc = _run(
        [
            "bash",
            str(commit_sh),
            "-m",
            "chore(scaffold): harness + manifest farga",
            *commit_paths_for(project),
        ],
        cwd=project,
    )
    if rc != 0:
        raise RuntimeError(f"initial commit failed (rc={rc}) — run it by hand with commit.sh")
    return plan
