import pytest
from pathlib import Path
from aqua_qe_playwright.story_registry import register_story_artifacts, StoryRegistrationResult


@pytest.fixture
def knowledge_root(tmp_path):
    root = tmp_path / "knowledge"
    root.mkdir()
    return root


def test_register_creates_story_file(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-1",
        module="home",
        title="Usuário vê home",
        tags=["@smoke"],
    )
    assert (knowledge_root / "stories" / "PWT-1.md").exists()


def test_story_file_contains_playwright_paths(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-2",
        module="checkout",
        title="Checkout funciona",
        tags=["@regressao"],
    )
    content = (knowledge_root / "stories" / "PWT-2.md").read_text(encoding="utf-8")
    assert "tests/e2e" in content
    assert ".spec.ts" in content


def test_story_file_contains_page_reference(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-3",
        module="login",
        title="Login funciona",
        tags=["@smoke"],
    )
    content = (knowledge_root / "stories" / "PWT-3.md").read_text(encoding="utf-8")
    assert "Page.ts" in content or "LoginPage" in content


def test_story_file_contains_locators_reference(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-4",
        module="login",
        title="Login com locators",
        tags=["@smoke"],
    )
    content = (knowledge_root / "stories" / "PWT-4.md").read_text(encoding="utf-8")
    assert ".locators.ts" in content


def test_index_is_updated(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-5",
        module="home",
        title="Index atualizado",
        tags=["@smoke"],
    )
    index_file = knowledge_root / "stories_index.yaml"
    assert index_file.exists()
    assert "PWT-5" in index_file.read_text(encoding="utf-8")


def test_rules_delta_mentions_playwright(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-6",
        module="home",
        title="Regra nova",
        tags=["@smoke"],
    )
    delta_files = list((knowledge_root / "rules_delta").glob("*.md"))
    assert len(delta_files) > 0
    content = delta_files[0].read_text(encoding="utf-8")
    assert "Playwright" in content or "spec" in content or "locators" in content


def test_result_has_created_list(knowledge_root):
    result = register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-7",
        module="home",
        title="Teste resultado",
        tags=["@smoke"],
    )
    assert isinstance(result, StoryRegistrationResult)
    assert len(result.created) > 0


def test_register_twice_skips_story_file(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-8",
        module="home",
        title="Primeira vez",
        tags=["@smoke"],
    )
    result = register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-8",
        module="home",
        title="Segunda vez",
        tags=["@smoke"],
    )
    assert any("PWT-8" in s for s in result.skipped)


def test_index_entry_contains_locators_ppom(knowledge_root):
    register_story_artifacts(
        knowledge_root=knowledge_root,
        story_id="PWT-9",
        module="checkout",
        title="Checkout PPOM",
        tags=["@smoke"],
    )
    content = (knowledge_root / "stories_index.yaml").read_text(encoding="utf-8")
    assert "locators/checkout.locators.ts" in content
