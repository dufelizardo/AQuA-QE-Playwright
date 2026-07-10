from pathlib import Path
from aqua_qe_playwright.config import AQuAConfig


def test_default_knowledge_root_ends_with_piloto():
    cfg = AQuAConfig()
    assert "projeto_playwright_piloto" in str(cfg.knowledge_root)


def test_from_project_overrides_project_name():
    cfg = AQuAConfig.from_project("meu_projeto")
    assert "meu_projeto" in str(cfg.knowledge_root)


def test_knowledge_root_is_path():
    cfg = AQuAConfig()
    assert isinstance(cfg.knowledge_root, Path)


def test_knowledge_root_parent_ends_with_knowledge():
    cfg = AQuAConfig()
    assert cfg.knowledge_root.parent.name == "knowledge"


def test_from_project_with_explicit_knowledge_root(tmp_path):
    cfg = AQuAConfig.from_project(knowledge_root=tmp_path)
    assert cfg.knowledge_root == tmp_path
