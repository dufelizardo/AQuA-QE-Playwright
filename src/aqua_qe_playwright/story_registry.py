"""Story onboarding helpers — persiste artefatos de conhecimento em disco."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class StoryRegistrationResult:
    created: list[str]
    updated: list[str]
    skipped: list[str]


def register_story_artifacts(
    *,
    knowledge_root: Path,
    story_id: str,
    module: str,
    title: str,
    tags: list[str] | None = None,
) -> StoryRegistrationResult:
    module_slug = _slugify(module)
    story_id = story_id.strip().upper()
    tags = tags or [story_id, module_slug]

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    stories_dir = knowledge_root / "stories"
    rules_delta_dir = knowledge_root / "rules_delta"
    stories_dir.mkdir(parents=True, exist_ok=True)
    rules_delta_dir.mkdir(parents=True, exist_ok=True)

    story_path = stories_dir / f"{story_id}.md"
    if story_path.exists():
        skipped.append(str(story_path))
    else:
        story_path.write_text(
            _build_story_template(story_id=story_id, module=module_slug, title=title),
            encoding="utf-8",
        )
        created.append(str(story_path))

    stories_index_path = knowledge_root / "stories_index.yaml"
    if not stories_index_path.exists():
        stories_index_path.write_text(
            "version: 1\nupdated_at: 1970-01-01\nstories:\n", encoding="utf-8"
        )
        created.append(str(stories_index_path))

    index_content = stories_index_path.read_text(encoding="utf-8")
    if _story_exists_in_index(index_content, story_id):
        skipped.append(f"{stories_index_path} (story {story_id} already indexed)")
    else:
        entry = _build_story_index_entry(
            story_id=story_id, module=module_slug, title=title, tags=tags
        )
        new_content = index_content.rstrip() + "\n\n" + entry + "\n"
        new_content = _set_updated_at(new_content, date.today().isoformat())
        stories_index_path.write_text(new_content, encoding="utf-8")
        updated.append(str(stories_index_path))

    rules_delta_path = rules_delta_dir / f"{module_slug}_rules_delta.md"
    if not rules_delta_path.exists():
        rules_delta_path.write_text(
            _build_rules_delta_header(module_slug), encoding="utf-8"
        )
        created.append(str(rules_delta_path))

    delta_content = rules_delta_path.read_text(encoding="utf-8")
    if _rules_delta_has_story(delta_content, story_id):
        skipped.append(f"{rules_delta_path} (story {story_id} already documented)")
    else:
        delta_content = (
            delta_content.rstrip()
            + "\n\n"
            + _build_rules_delta_story_section(story_id=story_id)
            + "\n"
        )
        rules_delta_path.write_text(delta_content, encoding="utf-8")
        updated.append(str(rules_delta_path))

    return StoryRegistrationResult(created=created, updated=updated, skipped=skipped)


def _build_story_template(*, story_id: str, module: str, title: str) -> str:
    return f"""# {story_id} [{module.upper()}] {title}

## Story metadata

- story_id: {story_id}
- modulo: {module}
- perfil: Usuário
- origem: Jira
- status_conhecimento: draft

## Objetivo

Descrever objetivo funcional da historia.

## Regras de negocio

1. Preencher regra 1.
2. Preencher regra 2.

## Criterios de aceitacao mapeados para automacao

- CA1: Preencher criterio 1.

## Regras novas em vigor

- R1: Preencher regra nova.

## Regras que deixam de fazer sentido

- L1: Preencher regra que deixa de valer.

## Analise de impacto vs historias anteriores

- Preencher impacto em specs/pages/locators.

## Mapeamento PPOM recomendado

- spec: tests/e2e/{module}/{story_id.lower()}.spec.ts
- page: pages/{_pascal(module)}Page.ts
- locators: locators/{module}.locators.ts

## Tags recomendadas

- @{story_id.lower()}
- @{module.replace("_", "-")}

## Casos de teste sugeridos

1. {story_id} - validar cenario principal
"""


def _build_story_index_entry(
    *, story_id: str, module: str, title: str, tags: list[str]
) -> str:
    normalized_tags = [t.strip() for t in tags if t.strip()]
    if story_id not in normalized_tags:
        normalized_tags.insert(0, story_id)
    if module not in normalized_tags:
        normalized_tags.append(module)

    lines = [
        f"  - story_id: {story_id}",
        f'    titulo: "[{module.upper()}] {title}"',
        "    fonte: jira",
        f"    modulo: {module}",
        f"    arquivo: knowledge/stories/{story_id}.md",
        "    status: ativo",
        "    tags:",
        *[f"      - {tag}" for tag in normalized_tags],
        "    saida_recomendada:",
        f"      spec: tests/e2e/{module}/{story_id.lower()}.spec.ts",
        f"      page: pages/{_pascal(module)}Page.ts",
        f"      locators: locators/{module}.locators.ts",
    ]
    return "\n".join(lines)


def _build_rules_delta_header(module: str) -> str:
    return (
        f"# {module.upper()} rules delta ledger\n\n"
        f"Documento para registrar regras novas e regras descontinuadas por historia do modulo {module}.\n"
    )


def _build_rules_delta_story_section(*, story_id: str) -> str:
    return f"""## {story_id}

### Regras novas em vigor

- Preencher regras novas.

### Regras que deixam de valer

- Preencher regras descontinuadas.

### Pontos de atencao

- Preencher riscos e pontos de validacao.

### Impacto de automacao esperado

- Preencher impacto em specs, pages e locators Playwright.
"""


def _story_exists_in_index(content: str, story_id: str) -> bool:
    return (
        re.search(
            rf"^\s*-\s*story_id:\s*{re.escape(story_id)}\s*$",
            content,
            flags=re.MULTILINE,
        )
        is not None
    )


def _rules_delta_has_story(content: str, story_id: str) -> bool:
    return (
        re.search(rf"^##\s+{re.escape(story_id)}\s*$", content, flags=re.MULTILINE)
        is not None
    )


def _set_updated_at(content: str, value: str) -> str:
    if re.search(r"^updated_at:\s*.*$", content, flags=re.MULTILINE):
        return re.sub(
            r"^updated_at:\s*.*$",
            f"updated_at: {value}",
            content,
            count=1,
            flags=re.MULTILINE,
        )
    return f"updated_at: {value}\n" + content


def _slugify(value: str) -> str:
    cleaned = value.lower().strip()
    for src, tgt in {
        "á": "a", "à": "a", "â": "a", "ã": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u", "ç": "c",
    }.items():
        cleaned = cleaned.replace(src, tgt)
    return re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in _slugify(value).split("_"))
