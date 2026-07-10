import pytest
from pathlib import Path
from aqua_qe_playwright.prompt_builder import AQuAPromptBuilder


@pytest.fixture
def builder(tmp_path):
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    return AQuAPromptBuilder(knowledge_root=knowledge_root)


def test_header_contains_ppom(builder):
    prompt = builder.story_context(story_text="Historia de teste", module="home")
    assert "PPOM" in prompt


def test_header_contains_locators(builder):
    prompt = builder.story_context(story_text="Historia de teste", module="home")
    assert "locators" in prompt.lower()


def test_header_contains_async(builder):
    prompt = builder.story_context(story_text="Historia de teste", module="home")
    assert "async" in prompt


def test_header_contains_promise(builder):
    prompt = builder.story_context(story_text="Historia de teste", module="home")
    assert "Promise" in prompt


def test_story_context_contains_story_text(builder):
    story = "HISTORIA: o usuario deve logar"
    prompt = builder.story_context(story_text=story, module="home")
    assert story in prompt


def test_story_context_contains_story_id(builder):
    prompt = builder.story_context(story_text="Historia", story_id="PWT-10", module="home")
    assert "PWT-10" in prompt


def test_dom_context_contains_html_snippet(builder):
    html = "<div data-testid='home-title'>Home</div>"
    prompt = builder.dom_context(module="home", html_snippet=html)
    assert "data-testid" in prompt


def test_dom_context_mentions_playwright_or_locators(builder):
    prompt = builder.dom_context(module="home", html_snippet="<h1>Teste</h1>")
    assert "Playwright" in prompt or "locator" in prompt.lower()


def test_knowledge_context_contains_query(builder):
    query = "Quais historias afetam o modulo home?"
    prompt = builder.knowledge_context(query=query)
    assert query in prompt


def test_format_for_terminal_returns_string(builder):
    prompt = builder.story_context(story_text="test", module="home")
    formatted = builder.format_for_terminal(prompt)
    assert isinstance(formatted, str)
    assert len(formatted) > len(prompt)


def test_story_context_with_generate_task(builder):
    prompt = builder.story_context(
        story_text="historia qualquer", module="home", task="generate"
    )
    assert "spec.ts" in prompt or "Page.ts" in prompt


def test_dom_context_references_locators_layer(builder):
    prompt = builder.dom_context(
        module="home", html_snippet="<button data-testid='btn'>OK</button>"
    )
    assert ".locators.ts" in prompt or "LOC_" in prompt or "locators" in prompt.lower()


def test_story_context_with_knowledge_base(tmp_path):
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    (knowledge_root / "modules_registry.yaml").write_text(
        "modulos:\n  - nome: home\n", encoding="utf-8"
    )
    builder = AQuAPromptBuilder(knowledge_root=knowledge_root)
    prompt = builder.story_context(story_text="Historia", module="home")
    assert "modules_registry" in prompt or "home" in prompt
