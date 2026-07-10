from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).parent
_KNOWLEDGE_BASE = _PACKAGE_ROOT.parent.parent / "knowledge"
_DEFAULT_PROJECT = "projeto_playwright_piloto"


def _default_knowledge_root() -> Path:
    return _KNOWLEDGE_BASE / _DEFAULT_PROJECT


@dataclass
class AQuAConfig:
    knowledge_root: Path = field(default_factory=_default_knowledge_root)

    def __post_init__(self) -> None:
        self.knowledge_root = Path(self.knowledge_root)

    @classmethod
    def from_project(
        cls, project: str | None = None, knowledge_root: str | Path | None = None
    ) -> AQuAConfig:
        if knowledge_root:
            return cls(knowledge_root=Path(knowledge_root))
        proj = project or _DEFAULT_PROJECT
        return cls(knowledge_root=_KNOWLEDGE_BASE / proj)
