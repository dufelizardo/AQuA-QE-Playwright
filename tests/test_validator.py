import pytest
from pathlib import Path
from aqua_qe_playwright.validator import validate_ppom_chain, validate_knowledge_consistency


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# validate_ppom_chain
# ---------------------------------------------------------------------------

def test_valid_ppom_chain_passes(tmp_path):
    module = "checkout"
    _write(
        tmp_path / "tests" / "e2e" / module / "pwt-1.spec.ts",
        "import { CheckoutPage } from '../../pages/CheckoutPage';\n"
        "import * as loc from '../../locators/checkout.locators';\n"
        "test.describe('Checkout', () => {});\n",
    )
    _write(
        tmp_path / "pages" / "CheckoutPage.ts",
        "import { type Page, expect } from '@playwright/test';\n"
        "import * as loc from '../locators/checkout.locators';\n"
        "export class CheckoutPage {}\n",
    )
    _write(
        tmp_path / "locators" / "checkout.locators.ts",
        "export const URL_CHECKOUT = '/checkout';\n",
    )

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is True


def test_missing_spec_fails(tmp_path):
    module = "checkout"
    _write(tmp_path / "pages" / "CheckoutPage.ts",
           "import * as loc from '../locators/checkout.locators';\nexport class CheckoutPage {}")
    _write(tmp_path / "locators" / "checkout.locators.ts", "export const URL = '/';")

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is False
    assert any("spec" in e.lower() for e in result.errors)


def test_missing_page_fails(tmp_path):
    module = "checkout"
    _write(
        tmp_path / "tests" / "e2e" / module / "pwt-1.spec.ts",
        "import { CheckoutPage } from '../../pages/CheckoutPage';",
    )
    _write(tmp_path / "locators" / "checkout.locators.ts", "export const URL = '/';")

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is False
    assert any("page" in e.lower() or "Page" in e for e in result.errors)


def test_missing_locators_fails(tmp_path):
    module = "checkout"
    _write(
        tmp_path / "tests" / "e2e" / module / "pwt-1.spec.ts",
        "import { CheckoutPage } from '../../pages/CheckoutPage';",
    )
    _write(
        tmp_path / "pages" / "CheckoutPage.ts",
        "import * as loc from '../locators/checkout.locators';\nexport class CheckoutPage {}",
    )

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is False
    assert any("locator" in e.lower() or "Locator" in e for e in result.errors)


def test_page_missing_locators_import_fails(tmp_path):
    module = "checkout"
    _write(
        tmp_path / "tests" / "e2e" / module / "pwt-1.spec.ts",
        "import { CheckoutPage } from '../../pages/CheckoutPage';",
    )
    _write(
        tmp_path / "pages" / "CheckoutPage.ts",
        "export class CheckoutPage {}",  # sem import de locators
    )
    _write(tmp_path / "locators" / "checkout.locators.ts", "export const URL = '/';")

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is False


def test_spec_missing_page_import_fails(tmp_path):
    module = "checkout"
    _write(
        tmp_path / "tests" / "e2e" / module / "pwt-1.spec.ts",
        "// sem import da page\ntest('ok', async () => {});",
    )
    _write(
        tmp_path / "pages" / "CheckoutPage.ts",
        "import * as loc from '../locators/checkout.locators';\nexport class CheckoutPage {}",
    )
    _write(tmp_path / "locators" / "checkout.locators.ts", "export const URL = '/';")

    result = validate_ppom_chain(tmp_path, module)
    assert result.ok is False


# ---------------------------------------------------------------------------
# validate_knowledge_consistency
# ---------------------------------------------------------------------------

def _setup_knowledge(root: Path):
    # modules_registry com module_id (formato que o parser espera)
    (root / "modules_registry.yaml").write_text(
        "modulos:\n  - module_id: home\n    nome: home\n", encoding="utf-8"
    )
    (root / "stories_index.yaml").write_text(
        "version: 1\nupdated_at: 2026-01-01\nstories:\n"
        "  - story_id: PWT-1\n"
        "    titulo: \"[HOME] Home inicial\"\n"
        "    modulo: home\n"
        "    arquivo: knowledge/stories/PWT-1.md\n",
        encoding="utf-8",
    )
    stories_dir = root / "stories"
    stories_dir.mkdir(exist_ok=True)
    (stories_dir / "PWT-1.md").write_text(
        "# PWT-1 [HOME] Home inicial\n\n## Story metadata\n\n- modulo: home\n",
        encoding="utf-8",
    )


def test_consistent_knowledge_passes(tmp_path):
    _setup_knowledge(tmp_path)
    result = validate_knowledge_consistency(tmp_path)
    assert result.ok is True


def test_story_in_index_but_missing_file_fails(tmp_path):
    _setup_knowledge(tmp_path)
    (tmp_path / "stories_index.yaml").write_text(
        "version: 1\nupdated_at: 2026-01-01\nstories:\n"
        "  - story_id: PWT-999\n"
        "    titulo: \"Sem arquivo\"\n"
        "    modulo: home\n"
        "    arquivo: knowledge/stories/PWT-999.md\n",
        encoding="utf-8",
    )

    result = validate_knowledge_consistency(tmp_path)
    assert result.ok is False
    assert any("PWT-999" in e for e in result.errors)


def test_module_in_story_not_in_registry_fails(tmp_path):
    _setup_knowledge(tmp_path)
    (tmp_path / "stories_index.yaml").write_text(
        "version: 1\nupdated_at: 2026-01-01\nstories:\n"
        "  - story_id: PWT-1\n"
        "    titulo: \"Teste\"\n"
        "    modulo: modulo_inexistente\n"
        "    arquivo: knowledge/stories/PWT-1.md\n",
        encoding="utf-8",
    )
    # story file exists with different module
    (tmp_path / "stories" / "PWT-1.md").write_text(
        "# PWT-1\n\n## Story metadata\n\n- modulo: home\n", encoding="utf-8"
    )

    result = validate_knowledge_consistency(tmp_path)
    assert result.ok is False
