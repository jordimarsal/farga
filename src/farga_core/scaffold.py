"""Scaffold: manifest -> executable repo (the S4/S5 steps, scripted).

Lesson #2 from the mcp-plane pilot: `git init` BEFORE harness install, or the
Conventional-Commits hook lands in the enclosing repo's .git.
"""

from __future__ import annotations

import subprocess
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


# The published harness detects the stack from files; a new project is empty and
# would fall back to "generic". These temporary markers make the installer see the
# stack chosen in the manifest. They are removed before the initial commit.
STACK_MARKERS: dict[str, tuple[str, ...]] = {
    "typescript": ("tsconfig.json",),
    "node": ("package.json",),
    "python": ("pyproject.toml",),
    "go": ("go.mod",),
    "java": ("pom.xml",),
    "rust": ("Cargo.toml",),
    "android": ("build.gradle", "app/src/main/AndroidManifest.xml"),
    "generic": (),
}


def ensure_stack_markers(project: Path, language: str) -> list[Path]:
    """Create the harness detection markers that are missing; return the created ones."""
    created: list[Path] = []
    for relative in STACK_MARKERS.get(language, ()):
        path = project / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "", encoding="utf-8")
        created.append(path)
    return created


def remove_stack_markers(project: Path, created: list[Path]) -> None:
    """Remove only the markers this run created, plus the dirs it had to make."""
    for path in reversed(created):
        path.unlink(missing_ok=True)
        parent = path.parent
        while parent != project and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent


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
    created_markers = ensure_stack_markers(project, manifest.stack.language.value)
    try:
        for label, cmd in steps:
            if not cmd:
                continue
            rc = _run(cmd)
            if rc != 0:
                raise RuntimeError(f"scaffold step failed (rc={rc}): {label}")
    finally:
        remove_stack_markers(project, created_markers)

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
