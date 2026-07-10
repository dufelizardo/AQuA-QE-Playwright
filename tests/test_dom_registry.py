import json
import pytest
from pathlib import Path
from aqua_qe_playwright.dom_registry import DomKnowledgeRegistry, build_dom_summary


HTML_SAMPLE = """
<html>
<body>
  <h1 data-testid="home-title">Home</h1>
  <button data-testid="btn-login" aria-label="Fazer login" role="button">Login</button>
  <input data-testid="campo-email" aria-label="E-mail" placeholder="Digite seu e-mail" />
  <div data-testid="card-produto">Card</div>
</body>
</html>
"""

HTML_V2 = """
<html>
<body>
  <h1 data-testid="home-title">Home</h1>
  <button data-testid="btn-login" aria-label="Fazer login" role="button">Login</button>
  <input data-testid="campo-email-novo" aria-label="E-mail" placeholder="Digite seu e-mail" />
</body>
</html>
"""


@pytest.fixture
def registry(tmp_path):
    knowledge_root = tmp_path / "knowledge"
    knowledge_root.mkdir()
    return DomKnowledgeRegistry(knowledge_root=knowledge_root)


def test_register_saves_snapshot(registry, tmp_path):
    registry.register_snapshot(module="home", html=HTML_SAMPLE, source_label="sprint-1")
    snapshots = list(
        (tmp_path / "knowledge" / "dom" / "modules" / "home" / "snapshots").glob("*.html")
    )
    assert len(snapshots) == 1


def test_build_dom_summary_extracts_heading_h1():
    summary = build_dom_summary(HTML_SAMPLE)
    assert summary.get("heading_h1") == "Home"


def test_build_dom_summary_extracts_data_testid():
    summary = build_dom_summary(HTML_SAMPLE)
    testid_attrs = summary.get("data_testid_attrs", [])
    assert "home-title" in testid_attrs
    assert "btn-login" in testid_attrs


def test_build_dom_summary_extracts_buttons():
    summary = build_dom_summary(HTML_SAMPLE)
    buttons = summary.get("buttons", [])
    assert any("login" in b.lower() for b in buttons)


def test_build_dom_summary_extracts_aria_labels():
    summary = build_dom_summary(HTML_SAMPLE)
    aria = summary.get("aria_labels", [])
    assert any("login" in a.lower() for a in aria)


def test_register_creates_locators_map(registry, tmp_path):
    registry.register_snapshot(module="home", html=HTML_SAMPLE, source_label="sprint-1")
    lmap_path = (
        tmp_path / "knowledge" / "dom" / "modules" / "home" / "locators" / "locators_map.json"
    )
    assert lmap_path.exists()
    lmap = json.loads(lmap_path.read_text(encoding="utf-8"))
    assert "selector_strategy" in lmap
    strategy = lmap["selector_strategy"]
    assert "getByRole" in strategy or "getByTestId" in strategy


def test_locators_map_contains_data_testid_suggestions(registry, tmp_path):
    registry.register_snapshot(module="home", html=HTML_SAMPLE, source_label="sprint-1")
    lmap_path = (
        tmp_path / "knowledge" / "dom" / "modules" / "home" / "locators" / "locators_map.json"
    )
    lmap = json.loads(lmap_path.read_text(encoding="utf-8"))
    suggestions = lmap.get("suggested_from_dom", [])
    assert len(suggestions) > 0
    first = suggestions[0]
    assert "data-testid" in first.get("selector", "")
    assert first.get("name", "").startswith("LOC_")


def test_register_creates_dom_contract(registry, tmp_path):
    registry.register_snapshot(module="home", html=HTML_SAMPLE, source_label="sprint-1")
    contract_path = (
        tmp_path / "knowledge" / "dom" / "modules" / "home" / "contracts" / "dom_contract.json"
    )
    assert contract_path.exists()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    assert contract.get("module") == "home"


def test_register_second_snapshot_creates_diff(registry, tmp_path):
    registry.register_snapshot(module="home", html=HTML_SAMPLE, source_label="v1")
    registry.register_snapshot(module="home", html=HTML_V2, source_label="v2")
    diffs_dir = tmp_path / "knowledge" / "dom" / "modules" / "home" / "diffs"
    diff_files = list(diffs_dir.glob("*.diff"))
    assert len(diff_files) >= 1
