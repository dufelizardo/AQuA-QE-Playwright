"""Constrói prompts ricos com contexto da base de conhecimento para uso no chat."""

from __future__ import annotations

import json
from pathlib import Path

_AQUA_HEADER = """\
# AQuA-QE Playwright — Contexto de Quality Engineering

Você é o **AQuA-QE Playwright** (Artificial Quality Assurance - Quality Engineering), \
especialista em automação de testes Playwright seguindo a metodologia \
**PPOM (Playwright Page Object Model)**.

## Metodologia PPOM — 3 camadas

| Camada | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| **Spec** | `tests/e2e/{modulo}/{story_id}.spec.ts` | Casos de teste com `test.describe()`/`test()`; importa Page |
| **Page** | `pages/{Modulo}Page.ts` | Classe com `readonly page: Page`; métodos `async` de ação e asserção |
| **Locators** | `locators/{modulo}.locators.ts` | Apenas constantes exportadas — fonte única de verdade para seletores |

Camada opcional:
| **Fixtures** | `fixtures/{modulo}.fixtures.ts` | Fixtures Playwright para setup/teardown reutilizável entre specs |

## Regras de nomenclatura por camada

### Locators (`locators/{modulo}.locators.ts`)
- **Fonte única de verdade** para seletores do módulo — quando o DOM mudar, só este arquivo é editado.
- Contém apenas constantes exportadas — sem lógica, sem chamadas Playwright.
- Estratégia em ordem de preferência:
  `getByRole()` > `getByTestId()` > `getByLabel()` > `getByText()` > `locator('[data-testid="..."]')`
- Para constantes de string (usadas com `page.locator()`): UPPER_CASE com prefixo `LOC_`.
- Para URLs: prefixo `URL_`.
  ```typescript
  // URL
  export const URL_HOME = '/home';

  // Títulos
  export const LOC_TITULO_SECAO_1 = '[data-testid="section-1-title"]';

  // Cards
  export const LOC_CARD_MINHA_OPERACAO = '[data-testid="card-minha-operacao"]';

  // Botões
  export const LOC_BTN_ACESSAR = '[data-testid="card-cta-acessar"]';
  export const LOC_BADGE_EM_BREVE = '[data-testid="badge-em-breve"]';
  ```
- Quando usar `getByRole()` diretamente na Page (sem constante), documente com comentário.

### Page (`pages/{Modulo}Page.ts`)
- Classe TypeScript que recebe `page: Page` no construtor.
- Todos os métodos são `async` e retornam `Promise<this>` para encadeamento.
- Importa seletores **somente** do arquivo Locators correspondente.
- Usa `expect()` do `@playwright/test` para asserções — nunca Chai ou Jest.
- Preferência de locators na Page:
  1. `this.page.getByRole('button', { name: 'Confirmar' })` — para elementos semânticos
  2. `this.page.getByTestId('btn-confirmar')` — para elementos com data-testid
  3. `this.page.locator(loc.LOC_BTN_CONFIRMAR)` — com constante do Locators
  ```typescript
  import {{ type Page, expect }} from '@playwright/test';
  import * as loc from '../locators/home.locators';

  export class HomePage {{
    constructor(private readonly page: Page) {{}}

    async navegar(): Promise<this> {{
      await this.page.goto(loc.URL_HOME);
      return this;
    }}

    async verificarCarregamento(): Promise<this> {{
      await expect(this.page.locator(loc.LOC_TITULO_SECAO_1)).toBeVisible();
      return this;
    }}

    async cardDeveEstarDesabilitado(locatorCard: string): Promise<this> {{
      await expect(this.page.locator(locatorCard)).toHaveAttribute('aria-disabled', 'true');
      return this;
    }}

    async cardNaoDevePermitirNavegacao(locatorCard: string): Promise<this> {{
      await expect(
        this.page.locator(locatorCard).locator(loc.LOC_BTN_ACESSAR)
      ).toBeDisabled();
      return this;
    }}
  }}
  ```

### Spec (`tests/e2e/{modulo}/{story_id}.spec.ts`)
- Importa a Page do módulo via fixture ou instanciação no `beforeEach`.
- `test.describe('{Módulo} @{modulo}')` como bloco pai (tag no describe).
- `test.beforeEach` instancia a Page e chama pré-condição de navegação.
- Padrão do `test()`: `'{MODULO_UPPER} - CA{n} - Descrição do critério de aceite'`.
- Tags via segundo argumento: `{{ tag: ['@smoke', '@{story_id}'] }}`.
- Tags disponíveis: `@smoke`, `@regressao`, `@critico`, `@em-breve`, `@{modulo}`, `@{story_id}`.
- Asserções com `expect()` — nunca strings de seletor inline fora da Page/Locators:
  ```typescript
  import {{ test, expect }} from '@playwright/test';
  import {{ HomePage }} from '../../pages/HomePage';
  import * as loc from '../../locators/home.locators';

  test.describe('Home @home', () => {{
    let home: HomePage;

    test.beforeEach(async ({{ page }}) => {{
      home = new HomePage(page);
      await home.navegar();
      await home.verificarCarregamento();
    }});

    test('HOME - CA10 - Cards com EM BREVE não permitem navegação',
      {{ tag: ['@regressao', '@smoke', '@home'] }},
      async ({{ page }}) => {{
        const cardsEmBreve = [
          loc.LOC_CARD_MINHA_OPERACAO,
          loc.LOC_CARD_ATENDE_B3,
          loc.LOC_CARD_TRADEMATE,
        ];
        for (const card of cardsEmBreve) {{
          await home.cardDeveEstarDesabilitado(card);
          await home.cardNaoDevePermitirNavegacao(card);
        }}
      }}
    );

    test('HOME - CA5 - Título da seção 2 exibe Comunicação B3',
      {{ tag: ['@smoke', '@home'] }},
      async ({{ page }}) => {{
        await expect(page.locator(loc.LOC_TITULO_SECAO_2)).toContainText('Comunicação B3');
      }}
    );
  }});
  ```

## Cadeia completa — exemplo com lista de cards (módulo Home, CA10)

```
locators/home.locators.ts  [apenas constantes exportadas]
  export const LOC_CARD_MINHA_OPERACAO = '[data-testid="card-minha-operacao"]';
  export const LOC_CARD_ATENDE_B3 = '[data-testid="card-comunicado-atende-b3"]';
  export const LOC_BTN_ACESSAR = '[data-testid="card-cta-acessar"]';

pages/HomePage.ts  [recebe page: Page; métodos async que retornam Promise<this>]
  async cardDeveEstarDesabilitado(locatorCard: string): Promise<this> {{
    await expect(this.page.locator(locatorCard)).toHaveAttribute('aria-disabled', 'true');
    return this;
  }}
  async cardNaoDevePermitirNavegacao(locatorCard: string): Promise<this> {{
    await expect(this.page.locator(locatorCard).locator(loc.LOC_BTN_ACESSAR)).toBeDisabled();
    return this;
  }}

Spec tests/e2e/home/{{story_id}}.spec.ts
  test.describe('Home @home', () => {{
    test('HOME - CA10 - ...', {{ tag: ['@regressao'] }}, async ({{ page }}) => {{
      for (const card of [loc.LOC_CARD_MINHA_OPERACAO, loc.LOC_CARD_ATENDE_B3]) {{
        await home.cardDeveEstarDesabilitado(card);    ← Page method
        await home.cardNaoDevePermitirNavegacao(card); ← Page method
      }}
    }});
  }});
```

- **Linguagem**: TypeScript
- **Framework**: Playwright (latest)
- **Padrão async**: `async/await` — nunca `.then()` ou callbacks
- **Idioma**: português brasileiro em todo o código (métodos, descrições, comentários)

## Documentação do projeto

Localizada em `{projeto_alvo}/doc/` — referenciar ao gerar testes ou sugerir onde registrar decisões.

| Arquivo | Conteúdo |
|---------|----------|
| `README.md` | Visão geral, estrutura e quick start |
| `doc/onboarding/visao_geral.md` | Contexto, perfis e módulos cobertos |
| `doc/onboarding/como_executar.md` | Instalação, variáveis e comandos Playwright |
| `doc/onboarding/contribuindo.md` | Passo a passo para novos testes + checklist |
| `doc/arquitetura/ppom.md` | As 3 camadas PPOM, regras e cadeia completa |
| `doc/arquitetura/estrutura_diretorios.md` | Árvore de diretórios comentada |
| `doc/convencoes/nomenclatura.md` | Classes, métodos, constantes, specs, tags, arquivos |
| `doc/convencoes/locators.md` | Estratégia getByRole/getByTestId/locator e agrupamento |
| `doc/modulos/{modulo}.md` | Componentes e regras ativas por módulo |
"""

_TASK_ANALYZE = """\
## Tarefa

Analise a história abaixo e produza:

1. **Objetivo** — o que o usuário final precisa
2. **Módulo(s) afetado(s)** — com base no registro de módulos
3. **Critérios de aceite** — lista numerada, cada um mapeável a um caso de teste Playwright
4. **Regras de negócio** — novas ou alteradas
5. **Regras descontinuadas** — comportamentos que deixam de valer
6. **Riscos de QA** — regressões prováveis, integrações afetadas
7. **Tags sugeridas** — para organização (`@smoke`, `@regressao`, `@critico`, `@em-breve`)
8. **Mapeamento PPOM** — quais arquivos das 3 camadas serão criados/alterados

> Após a análise, **pergunte ao usuário** em qual projeto Playwright os \
testes devem ser criados (caminho completo da raiz do projeto).
"""

_TASK_GENERATE = """\
## Tarefa

Com base na análise da história e no contexto de conhecimento acima, gere os \
arquivos Playwright/TypeScript completos seguindo PPOM.

Para **cada arquivo**, apresente:
1. O caminho completo relativo à raiz do projeto alvo (ex: `tests/e2e/home/pwt-1.spec.ts`)
2. O conteúdo completo em bloco de código TypeScript

> **Antes de gerar**: confirme com o usuário o caminho raiz do projeto Playwright \
onde os arquivos serão criados.
"""

_TASK_DOM = """\
## Tarefa

Analise o snapshot DOM abaixo e produza:

1. **Módulo detectado** — com base no conteúdo da página
2. **Contrato DOM** — headings, botões, campos, tabelas encontrados
3. **Mudanças detectadas** — comparar com o contrato anterior (se fornecido)
   - `BREAKING`: elemento removido ou locator alterado (testes vão falhar)
   - `RISCO`: elemento movido ou renomeado
   - `INFO`: novo elemento (oportunidade de cobertura)
4. **Locators sugeridos** — priorizando:
   `getByRole()` > `getByTestId()` > `getByLabel()` > `getByText()` > `locator('[data-testid="..."]')`
5. **Impacto nos testes** — quais arquivos `.spec.ts` e `Page.ts` precisam ser atualizados

> Após a análise, **pergunte ao usuário** o caminho do projeto Playwright \
para indicar os arquivos exatos a atualizar.
"""

_TASK_KNOWLEDGE = """\
## Tarefa

Responda à consulta abaixo com base exclusivamente no contexto de conhecimento fornecido acima.
Cite as fontes (arquivo e seção) de onde extraiu a informação.
Se a informação não existir na base, informe claramente e sugira o que registrar.
"""


class AQuAPromptBuilder:
    """Monta prompts contextualizados para uso no chat."""

    def __init__(self, knowledge_root: Path) -> None:
        self.knowledge_root = Path(knowledge_root)

    def story_context(
        self,
        story_text: str,
        story_id: str = "",
        module: str = "",
        task: str = "analyze",
    ) -> str:
        parts = [_AQUA_HEADER]
        knowledge = self._load_knowledge(scope="all", hint_module=module)
        if knowledge:
            parts.append("## Base de conhecimento\n\n" + knowledge)
        parts.append("## História\n")
        if story_id:
            parts.append(f"**ID:** {story_id}\n")
        if module:
            parts.append(f"**Módulo:** {module}\n")
        parts.append(story_text.strip())
        task_section = _TASK_GENERATE if task == "generate" else _TASK_ANALYZE
        parts.append(task_section)
        return "\n\n---\n\n".join(parts)

    def dom_context(
        self,
        module: str,
        html_snippet: str,
        story_id: str = "",
        previous_contract: dict | None = None,
    ) -> str:
        parts = [_AQUA_HEADER]
        module_info = self._load_module_info(module)
        if module_info:
            parts.append(f"## Módulo: {module}\n\n{module_info}")
        if previous_contract:
            parts.append(
                "## Contrato DOM anterior\n\n```json\n"
                + json.dumps(previous_contract, ensure_ascii=False, indent=2)
                + "\n```"
            )
        dom_section = f"## Módulo: {module} — Snapshot HTML capturado"
        if story_id:
            dom_section += f" (história: {story_id})"
        dom_section += f"\n\n```html\n{html_snippet[:6000]}\n```"
        parts.append(dom_section)
        parts.append(_TASK_DOM)
        return "\n\n---\n\n".join(parts)

    def knowledge_context(self, query: str, scope: str = "all") -> str:
        parts = [_AQUA_HEADER]
        knowledge = self._load_knowledge(scope=scope)
        if knowledge:
            parts.append("## Base de conhecimento\n\n" + knowledge)
        parts.append(f"## Consulta\n\n{query}")
        parts.append(_TASK_KNOWLEDGE)
        return "\n\n---\n\n".join(parts)

    def format_for_terminal(self, prompt: str) -> str:
        separator = "=" * 72
        return f"\n{separator}\n{prompt}\n{separator}\n"

    def _load_knowledge(self, scope: str = "all", hint_module: str = "") -> str:
        parts: list[str] = []
        root = self.knowledge_root

        if scope in ("all", "modules"):
            modules_file = root / "modules_registry.yaml"
            if modules_file.exists():
                parts.append(
                    "### Módulos registrados (`modules_registry.yaml`)\n\n"
                    f"```yaml\n{modules_file.read_text(encoding='utf-8')}\n```"
                )

        if scope in ("all", "stories"):
            stories_file = root / "stories_index.yaml"
            if stories_file.exists():
                parts.append(
                    "### Índice de histórias (`stories_index.yaml`)\n\n"
                    f"```yaml\n{stories_file.read_text(encoding='utf-8')}\n```"
                )
            if hint_module:
                story_texts = self._load_module_stories(hint_module, max_stories=3)
                if story_texts:
                    parts.append(
                        "### Histórias do módulo (para referência de padrões)\n\n"
                        + story_texts
                    )

        if scope in ("all", "rules"):
            rules_dir = root / "rules_delta"
            if rules_dir.exists():
                if hint_module:
                    slug = hint_module.lower().replace(" ", "_")
                    candidates = [rules_dir / f"{slug}_rules_delta.md"]
                else:
                    candidates = sorted(rules_dir.glob("*.md"))[:2]
                for f in candidates:
                    if f.exists():
                        parts.append(
                            f"### Rules delta: `{f.name}`\n\n{f.read_text(encoding='utf-8')}"
                        )

        if scope in ("all", "dom"):
            dom_index = root / "dom" / "index.json"
            if dom_index.exists():
                parts.append(
                    "### DOM index\n\n```json\n"
                    + dom_index.read_text(encoding="utf-8")
                    + "\n```"
                )

        return "\n\n".join(parts)

    def _load_module_info(self, module: str) -> str:
        parts: list[str] = []
        root = self.knowledge_root
        module_slug = module.lower().replace(" ", "_")
        contract_path = (
            root / "dom" / "modules" / module_slug / "contracts" / "dom_contract.json"
        )
        if contract_path.exists():
            parts.append(
                "**Contrato DOM atual:**\n```json\n"
                + contract_path.read_text(encoding="utf-8")
                + "\n```"
            )
        return "\n\n".join(parts)

    def _load_module_stories(self, module: str, max_stories: int = 3) -> str:
        module_slug = module.lower().replace(" ", "_")
        stories_dir = self.knowledge_root / "stories"
        if not stories_dir.exists():
            return ""
        index_path = self.knowledge_root / "stories_index.yaml"
        relevant_ids: list[str] = []
        if index_path.exists():
            relevant_ids = self._parse_module_story_ids(index_path, module_slug, max_stories)
        texts: list[str] = []
        for sid in relevant_ids:
            f = stories_dir / f"{sid}.md"
            if f.exists():
                texts.append(f"#### {sid}\n\n{f.read_text(encoding='utf-8')}")
        return "\n\n".join(texts)

    def _parse_module_story_ids(
        self, index_path: Path, module_slug: str, max_stories: int
    ) -> list[str]:
        ids: list[str] = []
        current_id: str | None = None
        for line in index_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- story_id:"):
                current_id = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("modulo:") and current_id:
                if stripped.split(":", 1)[1].strip() == module_slug:
                    ids.append(current_id)
                    if len(ids) >= max_stories:
                        break
                current_id = None
        return ids
