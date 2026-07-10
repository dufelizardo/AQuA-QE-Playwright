import pytest
from aqua_qe_playwright.templates import PPOMTemplates


@pytest.fixture
def tpl():
    return PPOMTemplates(module="checkout", story_id="PWT-42")


def test_slug(tpl):
    assert tpl.module_slug == "checkout"


def test_pascal(tpl):
    assert tpl.module_pascal == "Checkout"


def test_spec_contains_describe(tpl):
    content = tpl.spec()
    assert "test.describe" in content


def test_spec_contains_beforeEach(tpl):
    content = tpl.spec()
    assert "beforeEach" in content


def test_spec_contains_story_id(tpl):
    content = tpl.spec()
    assert "PWT-42" in content


def test_spec_contains_locators_import(tpl):
    content = tpl.spec()
    assert "locators/checkout.locators" in content


def test_spec_contains_page_import(tpl):
    content = tpl.spec()
    assert "CheckoutPage" in content


def test_page_contains_class(tpl):
    content = tpl.page()
    assert "class CheckoutPage" in content


def test_page_contains_constructor(tpl):
    content = tpl.page()
    assert "constructor(private readonly page: Page)" in content


def test_page_contains_navegar(tpl):
    content = tpl.page()
    assert "navegar" in content


def test_page_contains_promise_return(tpl):
    content = tpl.page()
    assert "Promise<this>" in content


def test_page_imports_locators(tpl):
    content = tpl.page()
    assert "checkout.locators" in content


def test_locators_has_url(tpl):
    content = tpl.locators()
    assert "URL_CHECKOUT" in content


def test_locators_has_loc_titulo(tpl):
    content = tpl.locators()
    assert "LOC_TITULO_CHECKOUT" in content


def test_locators_uses_data_testid(tpl):
    content = tpl.locators()
    assert "data-testid" in content


def test_all_files_returns_three(tpl):
    files = tpl.all_files()
    assert len(files) == 3


def test_all_files_contains_spec_path(tpl):
    files = tpl.all_files()
    paths = list(files.keys())
    assert any("spec.ts" in p for p in paths)


def test_all_files_contains_page_path(tpl):
    files = tpl.all_files()
    paths = list(files.keys())
    assert any("CheckoutPage.ts" in p for p in paths)


def test_all_files_contains_locators_path(tpl):
    files = tpl.all_files()
    paths = list(files.keys())
    assert any(".locators.ts" in p for p in paths)


def test_module_with_hyphen():
    tpl = PPOMTemplates(module="meu-modulo", story_id="PWT-1")
    assert "meu-modulo" in tpl.module_slug or "meu_modulo" in tpl.module_slug
