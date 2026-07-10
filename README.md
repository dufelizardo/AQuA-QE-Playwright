# AQuA-QE Playwright

> **Artificial Quality Assurance — Quality Engineering**
> Assistente de IA especializado em geração e governança de testes Playwright/TypeScript
> seguindo a metodologia **PPOM** (Playwright Page Object Model).

---

## O que é

O **AQuA-QE Playwright** é uma ferramenta CLI em Python que atua como copiloto de qualidade para equipes que utilizam Playwright com TypeScript. Ele:

- Gera prompts ricos e estruturados para assistentes de IA gerarem testes reais
- Governa uma base de conhecimento local com histórias, regras de negócio e contratos DOM
- Valida se a estrutura PPOM está correta no projeto alvo
- Rastreia mudanças de DOM e avalia impacto nos locators e pages
- Extrai locators inteligentes com estratégia Playwright nativa

---

## Metodologia PPOM — 3 camadas

| Camada | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| **Spec** | `tests/e2e/{modulo}/{story}.spec.ts` | `test.describe()`/`test()` com `async/await` — delegação pura |
| **Page** | `pages/{Modulo}Page.ts` | Classe com `readonly page: Page`; métodos `async` retornam `Promise<this>` |
| **Locators** | `locators/{modulo}.locators.ts` | Apenas constantes `LOC_*` e `URL_*` exportadas |

### Estratégia de Locators

```
getByRole() > getByTestId() > getByLabel() > getByText() > locator('[data-testid="..."]')
```

### Exemplo de Spec

```typescript
import { test, expect } from '@playwright/test';
import { HomePage } from '../../pages/HomePage';
import * as loc from '../../locators/home.locators';

test.describe('Home @home', () => {
  let home: HomePage;

  test.beforeEach(async ({ page }) => {
    home = new HomePage(page);
    await home.navegar();
    await home.verificarCarregamento();
  });

  test('HOME - CA1 - Cards com EM BREVE estão desabilitados',
    { tag: ['@smoke', '@home', '@PWT-10'] },
    async ({ page }) => {
      await home.cardDeveEstarDesabilitado(loc.LOC_CARD_MINHA_OPERACAO);
    }
  );
});
```

### Exemplo de Page

```typescript
import { type Page, expect } from '@playwright/test';
import * as loc from '../locators/home.locators';

export class HomePage {
  constructor(private readonly page: Page) {}

  async navegar(): Promise<this> {
    await this.page.goto(loc.URL_HOME);
    return this;
  }

  async verificarCarregamento(): Promise<this> {
    await expect(this.page.locator(loc.LOC_TITULO_HOME)).toBeVisible();
    return this;
  }
}
```

### Exemplo de Locators

```typescript
export const URL_HOME = '/home';
export const LOC_TITULO_HOME = '[data-testid="home-title"]';
export const LOC_CARD_MINHA_OPERACAO = '[data-testid="card-minha-operacao"]';
```

---

## Instalação

```bash
# A partir do workspace AI-Engineering
uv sync

# Verificar instalação
uv run aqua-qe-playwright --help
```

---

## CLI — Subcomandos

### `context` — Gerar prompt a partir de história Jira

```bash
uv run aqua-qe-playwright context \
  --story "Como usuário quero ver meus cards na home" \
  --module home \
  --story-id PWT-10
```

### `dom` — Analisar snapshot HTML e gerar locators

```bash
uv run aqua-qe-playwright dom \
  --html snapshot.html \
  --module home
```

### `knowledge` — Consultar a base de conhecimento

```bash
uv run aqua-qe-playwright knowledge \
  --query "Quais histórias afetam o módulo checkout?" \
  --project projeto_playwright_piloto
```

### `register` — Registrar nova história na base

```bash
uv run aqua-qe-playwright register \
  --story-id PWT-42 \
  --module checkout \
  --title "Checkout de produto único" \
  --criteria "CA1 - Formulário visível" "CA2 - Totais corretos" \
  --tags "@smoke" "@regressao"
```

### `validate` — Validar estrutura PPOM

```bash
# Validar toda a estrutura
uv run aqua-qe-playwright validate \
  --target /caminho/do/projeto-playwright \
  --module checkout \
  --scope all

# Apenas validar cadeia PPOM
uv run aqua-qe-playwright validate \
  --target . --module home --scope ppom

# Apenas validar base de conhecimento
uv run aqua-qe-playwright validate --scope knowledge
```

---

## Estrutura do Projeto

```
aqua_qe_playwright/
├── pyproject.toml
├── requirements.txt
├── README.md
├── REQUIREMENTS.md
├── CLAUDE.md
├── WHITEPAPER.md
├── src/
│   └── aqua_qe_playwright/
│       ├── __init__.py
│       ├── config.py          ← AQuAConfig (projeto piloto, knowledge_root)
│       ├── templates.py       ← PPOMTemplates (spec, page, locators)
│       ├── prompt_builder.py  ← PromptBuilder (context, dom, knowledge)
│       ├── story_registry.py  ← StoryRegistry (register, index, rules_delta)
│       ├── dom_registry.py    ← DOMRegistry (snapshot, diff, locators_map)
│       ├── validator.py       ← validate_ppom_chain, validate_knowledge_consistency
│       └── cli.py             ← CLI Typer (aqua-qe-playwright)
├── tests/
│   ├── test_config.py
│   ├── test_templates.py
│   ├── test_prompt_builder.py
│   ├── test_story_registry.py
│   ├── test_dom_registry.py
│   └── test_validator.py
├── prompts/
│   ├── orchestrator.md
│   ├── story_analyzer.md
│   ├── test_generator.md
│   ├── dom_watcher.md
│   └── knowledge_agent.md
└── knowledge/
    └── projeto_playwright_piloto/
        ├── modules_registry.yaml
        ├── stories_index.yaml
        ├── stories/
        ├── rules_delta/
        └── dom/
```

---

## Rodar Testes

```bash
cd projetos/aqua_qe_playwright
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
```

---

## Licença

MIT

---

*Eduardo Felizardo Cândido | Senior QA Automation Engineer | AI-driven Testing | Robot Framework*
