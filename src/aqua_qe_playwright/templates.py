from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class PPOMTemplates:
    module: str
    story_id: str = ""

    def _slug(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"[àáâãä]", "a", text)
        text = re.sub(r"[èéêë]", "e", text)
        text = re.sub(r"[ìíîï]", "i", text)
        text = re.sub(r"[òóôõö]", "o", text)
        text = re.sub(r"[ùúûü]", "u", text)
        text = re.sub(r"[ç]", "c", text)
        text = re.sub(r"[^a-z0-9]+", "_", text)
        return text.strip("_")

    def _pascal(self, text: str) -> str:
        return "".join(part.capitalize() for part in self._slug(text).split("_"))

    @property
    def module_slug(self) -> str:
        return self._slug(self.module)

    @property
    def module_pascal(self) -> str:
        return self._pascal(self.module)

    def spec(self) -> str:
        m = self.module_slug
        mp = self.module_pascal
        tag = self.story_id or m
        return f"""\
import {{ test, expect }} from '@playwright/test';
import {{ {mp}Page }} from '../../pages/{mp}Page';
import * as loc from '../../locators/{m}.locators';

test.describe('{self.module} @{m}', () => {{
  let page{mp}: {mp}Page;

  test.beforeEach(async ({{ page }}) => {{
    page{mp} = new {mp}Page(page);
    await page{mp}.navegar();
    await page{mp}.verificarCarregamento();
  }});

  test('{self.module.upper()} - CA1 - Smoke inicial', {{ tag: ['@smoke', '@{tag}'] }}, async ({{ page }}) => {{
    await page{mp}.verificarCarregamento();
  }});

  test('{self.module.upper()} - CA2 - Fluxo principal', {{ tag: ['@regressao', '@{tag}'] }}, async ({{ page }}) => {{
    // TODO: implementar fluxo principal conforme critérios de aceite
  }});
}});
"""

    def page(self) -> str:
        m = self.module_slug
        mp = self.module_pascal
        return f"""\
import {{ type Page, expect }} from '@playwright/test';
import * as loc from '../locators/{m}.locators';

export class {mp}Page {{
  constructor(private readonly page: Page) {{}}

  async navegar(): Promise<this> {{
    await this.page.goto(loc.URL_{m.upper()});
    return this;
  }}

  async verificarCarregamento(): Promise<this> {{
    await expect(this.page.locator(loc.LOC_TITULO_{m.upper()})).toBeVisible();
    return this;
  }}

  async verificarTexto(locator: string, texto: string): Promise<this> {{
    await expect(this.page.locator(locator)).toContainText(texto);
    return this;
  }}

  async clicarElemento(locator: string): Promise<this> {{
    await this.page.locator(locator).click();
    return this;
  }}
}}
"""

    def locators(self) -> str:
        m = self.module_slug
        return f"""\
// URL
export const URL_{m.upper()} = '/{m}';

// Títulos
export const LOC_TITULO_{m.upper()} = '[data-testid="{m}-title"]';

// Botões de ação
// export const LOC_BTN_CONFIRMAR = '[data-testid="{m}-btn-confirmar"]';

// Campos de formulário
// export const LOC_CAMPO_BUSCA = '[data-testid="{m}-campo-busca"]';
"""

    def all_files(self) -> dict[str, str]:
        m = self.module_slug
        mp = self.module_pascal
        story = self.story_id.lower() if self.story_id else m
        return {
            f"tests/e2e/{m}/{story}.spec.ts": self.spec(),
            f"pages/{mp}Page.ts": self.page(),
            f"locators/{m}.locators.ts": self.locators(),
        }
