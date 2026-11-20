"""farga.yaml — the single contract.

Everything (skill, CLI, future TUI) reads and writes the same manifest; no field
is invented at runtime. Schema lives here, pure and framework-free: load, model,
validate. Catalog and wire checks are environment data, not schema.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

API_VERSION = "farga/v0"
ROLES = ("planner", "worker", "reviewer")
MODEL_ID_RE = re.compile(r"^(local|remote|litellm)/[A-Za-z0-9][A-Za-z0-9._-]*$")


class Tool(str, Enum):
    opencode = "opencode"
    claude = "claude"


class Workflow(str, Enum):
    full = "full"
    hybrid = "hybrid"


class Architecture(str, Enum):
    hexagonal = "hexagonal"
    layered = "layered"
    clean = "clean"
    cqrs = "cqrs"
    microservices = "microservices"
    modular_monolith = "modular-monolith"
    event_driven = "event-driven"


class ConceptStatus(str, Enum):
    drafted = "drafted"
    profiled = "profiled"
    building = "building"
    parked = "parked"
    shipped = "shipped"


class Size(str, Enum):
    S = "S"
    M = "M"
    L = "L"


class Concept(BaseModel):
    file: str = "concept.md"
    profile: str = "profile.md"
    status: ConceptStatus = ConceptStatus.drafted


class Stack(BaseModel):
    """Literal flags for harness/install.sh — nothing more, nothing less."""

    tool: Tool = Tool.opencode
    workflow: Workflow = Workflow.hybrid
    architecture: Architecture = Architecture.modular_monolith
    modules: list[str] = Field(default_factory=list)


class PieceRef(BaseModel):
    """A catalog piece by id — referenced, never copied into the manifest."""

    id: str
    role: str
    config: dict[str, Any] = Field(default_factory=dict)


class Models(BaseModel):
    """Role -> registry id, mirroring buildwright's BW_ROLE_* (ROLES order)."""

    planner: str
    worker: str
    reviewer: str
    alternatives: dict[str, str] = Field(default_factory=dict)

    @field_validator("planner", "worker", "reviewer")
    @classmethod
    def _known_shape(cls, v: str) -> str:
        if not MODEL_ID_RE.match(v):
            raise ValueError(f"model id '{v}' must match local/… | remote/… | litellm/…")
        return v

    @field_validator("alternatives")
    @classmethod
    def _alt_shape(cls, v: dict[str, str]) -> dict[str, str]:
        for key, mid in v.items():
            if not MODEL_ID_RE.match(mid):
                raise ValueError(
                    f"alternative '{key}' -> '{mid}' must match local/… | remote/… | litellm/…"
                )
        return v

    def by_role(self, role: str) -> str:
        if role not in ROLES:
            raise KeyError(f"unknown role '{role}'. Known: {', '.join(ROLES)}")
        return str(getattr(self, role))


class Routing(BaseModel):
    source: str = "debrief"
    mode: str = "propose-then-confirm"
    proposal: str = ".farga/proposal.txt"


class Execution(BaseModel):
    runner: str = "buildwright"
    features_per_run: int = Field(default=2, ge=1)
    auto: bool = False
    size: Size = Size.M


class Lanes(BaseModel):
    slots: int = Field(default=2, ge=1)
    servers: list[str] = Field(default_factory=lambda: ["llama8999"])


class Observability(BaseModel):
    trace: str = "langfuse"
    evidence: str = "harness/logs/"


class Manifest(BaseModel):
    apiVersion: str
    concept: Concept = Field(default_factory=Concept)
    stack: Stack = Field(default_factory=Stack)
    pieces: list[PieceRef] = Field(default_factory=list)
    models: Models
    routing: Routing = Field(default_factory=Routing)
    execution: Execution = Field(default_factory=Execution)
    lanes: Lanes = Field(default_factory=Lanes)
    observability: Observability = Field(default_factory=Observability)

    @model_validator(mode="after")
    def _invariants(self) -> Self:
        if self.apiVersion != API_VERSION:
            raise ValueError(f"apiVersion must be '{API_VERSION}' (saw '{self.apiVersion}')")
        # Design rule (drafts/11): size L adds gauntlet + vertical slices.
        if self.execution.size == Size.L and "gauntlet" not in self.stack.modules:
            raise ValueError("execution.size L requires 'gauntlet' in stack.modules")
        return self


def load_manifest(path: Path) -> Manifest:
    """Parse and validate a farga.yaml. Raises ValidationError/yaml errors as-is."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path}: manifest must be a YAML mapping (saw {type(data).__name__})")
    return Manifest.model_validate(data)
