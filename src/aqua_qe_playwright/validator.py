"""Validação da cadeia PPOM e consistência da base de conhecimento."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidationResult:
    errors: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        if self.ok:
            return "OK — nenhum erro encontrado."
        return "\n".join(f"- {e}" for e in self.errors)


def validate_ppom_chain(target_root: Path, module: str = "home") -> ValidationResult:
    """Valida a cadeia PPOM (3 camadas) de um módulo e retorna erros."""
    module_slug = module.lower()
    module_pascal = "".join(part.capitalize() for part in module_slug.split("_"))
    errors: list[str] = []

    spec_dir = target_root / "tests" / "e2e" / module_slug
    spec_files = sorted(spec_dir.glob("*.spec.ts")) if spec_dir.exists() else []
    page = target_root / "pages" / f"{module_pascal}Page.ts"
    locators = target_root / "locators" / f"{module_slug}.locators.ts"

    if not spec_files:
        errors.append(f"Sem arquivos .spec.ts em: {spec_dir}")
    if not page.exists():
        errors.append(f"Arquivo de Page Object não encontrado: {page}")
    if not locators.exists():
        errors.append(f"Arquivo de Locators não encontrado: {locators}")

    # Valida que a Page importa os Locators do módulo
    expected_locators_import = f"../locators/{module_slug}.locators"
    if page.exists() and not _has_import(page, expected_locators_import):
        errors.append(
            f"Import de locators ausente ou incorreto em {page} "
            f"(esperado: '{expected_locators_import}')"
        )

    # Valida que ao menos um spec importa a Page
    expected_page_import = f"{module_pascal}Page"
    if spec_files:
        has_valid = any(_has_import(f, expected_page_import) for f in spec_files)
        if not has_valid:
            errors.append(
                f"Import de '{expected_page_import}' ausente em tests/e2e/{module_slug}/*.spec.ts"
            )

    return ValidationResult(errors=errors)


def validate_knowledge_consistency(knowledge_root: Path) -> ValidationResult:
    """Valida consistência entre módulos, histórias e DOM contracts."""
    errors: list[str] = []

    modules_registry_path = knowledge_root / "modules_registry.yaml"
    stories_index_path = knowledge_root / "stories_index.yaml"

    if not modules_registry_path.exists():
        return ValidationResult(
            errors=[f"modules_registry.yaml não encontrado: {modules_registry_path}"]
        )
    if not stories_index_path.exists():
        return ValidationResult(
            errors=[f"stories_index.yaml não encontrado: {stories_index_path}"]
        )

    modules = _load_modules_registry(modules_registry_path)
    if not modules:
        return ValidationResult(
            errors=[f"Nenhum module_id encontrado em {modules_registry_path}"]
        )

    stories = _load_stories_index(stories_index_path)
    story_ids = {s["story_id"] for s in stories if s.get("story_id")}

    for story in stories:
        story_id = story.get("story_id")
        module = story.get("modulo")
        relative_file = story.get("arquivo")

        if not story_id:
            errors.append("Entrada sem story_id em stories_index.yaml")
            continue
        if not module:
            errors.append(f"História {story_id} sem campo 'modulo' em stories_index.yaml")
            continue
        if module not in modules:
            errors.append(
                f"História {story_id} referencia módulo desconhecido '{module}' "
                f"(não registrado em modules_registry.yaml)"
            )
        if not relative_file:
            errors.append(f"História {story_id} sem campo 'arquivo' em stories_index.yaml")
            continue

        story_path = (
            knowledge_root.parent / relative_file
            if not relative_file.startswith("/")
            else Path(relative_file)
        )
        if not story_path.exists():
            story_path = knowledge_root / "stories" / f"{story_id}.md"
        if not story_path.exists():
            errors.append(f"Arquivo de história não encontrado para {story_id}: {story_path}")
            continue

        metadata_module = _extract_story_metadata_module(story_path)
        if not metadata_module:
            errors.append(f"Campo 'modulo' ausente nos metadados de {story_path}")
        elif metadata_module != module:
            errors.append(
                f"Módulo divergente em {story_id}: "
                f"index='{module}' vs metadata='{metadata_module}'"
            )

    dom_index_path = knowledge_root / "dom" / "index.json"
    if not dom_index_path.exists():
        return ValidationResult(errors=errors)

    dom_index = json.loads(dom_index_path.read_text(encoding="utf-8"))
    for dom_module_key, dom_module in dom_index.get("modules", {}).items():
        if dom_module_key not in modules:
            errors.append(
                f"Módulo DOM '{dom_module_key}' não registrado em modules_registry.yaml"
            )

        snapshots = dom_module.get("snapshots", [])
        if not snapshots:
            continue

        latest = snapshots[-1]
        latest_story_id = latest.get("story_id")
        if not latest_story_id:
            errors.append(
                f"Snapshot DOM mais recente sem story_id — módulo '{dom_module_key}'"
            )
        elif latest_story_id not in story_ids:
            errors.append(
                f"story_id '{latest_story_id}' do snapshot DOM de '{dom_module_key}' "
                f"não encontrado em stories_index.yaml"
            )

        contract_path = (
            knowledge_root / "dom" / "modules" / dom_module_key
            / "contracts" / "dom_contract.json"
        )
        if not contract_path.exists():
            errors.append(
                f"dom_contract.json ausente para módulo '{dom_module_key}': {contract_path}"
            )
            continue

        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract_story_id = contract.get("story_id")
        if not contract_story_id:
            errors.append(f"story_id vazio no dom_contract.json de '{dom_module_key}'")
        elif contract_story_id not in story_ids:
            errors.append(
                f"story_id '{contract_story_id}' do dom_contract de '{dom_module_key}' "
                f"não encontrado em stories_index.yaml"
            )

        if (
            latest_story_id
            and contract_story_id
            and latest_story_id != contract_story_id
        ):
            errors.append(
                f"Divergência em '{dom_module_key}': snapshot story='{latest_story_id}' "
                f"vs contract story='{contract_story_id}'"
            )

    return ValidationResult(errors=errors)


def _has_import(file_path: Path, expected_import: str) -> bool:
    if not file_path.exists():
        return False
    return expected_import in file_path.read_text(encoding="utf-8")


def _load_modules_registry(file_path: Path) -> set[str]:
    modules: set[str] = set()
    for line in file_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*-\s*module_id:\s*([a-z0-9_]+)\s*$", line)
        if match:
            modules.add(match.group(1))
    return modules


def _load_stories_index(file_path: Path) -> list[dict[str, str]]:
    stories: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in file_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("  - story_id:"):
            if current:
                stories.append(current)
            current = {"story_id": line.split(":", 1)[1].strip()}
            continue
        if not current:
            continue
        if line.startswith("    modulo:"):
            current["modulo"] = line.split(":", 1)[1].strip()
        elif line.startswith("    arquivo:"):
            current["arquivo"] = line.split(":", 1)[1].strip()
    if current:
        stories.append(current)
    return stories


def _extract_story_metadata_module(story_path: Path) -> str | None:
    content = story_path.read_text(encoding="utf-8")
    match = re.search(r"^- modulo:\s*(.+)$", content, flags=re.MULTILINE)
    return match.group(1).strip() if match else None
