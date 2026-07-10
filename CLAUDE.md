# CLAUDE.md — AQuA-QE Playwright

Instruções para o Claude Code ao trabalhar neste projeto.

## Comandos essenciais

```powershell
# Instalar dependências (rodar na raiz do workspace AI-Engineering)
uv sync

# Rodar todos os testes
uv run pytest

# Rodar com cobertura
uv run pytest --cov=src --cov-report=term-missing

# Rodar testes de um módulo específico
uv run pytest tests/test_templates.py -v

# Verificar CLI
uv run aqua-qe-playwright --help
uv run aqua-qe-playwright validate --help
```

## Arquitetura do projeto

| Módulo | Arquivo | Responsabilidade |
|--------|---------|-----------------|
| `config.py` | `AQuAConfig` | Configuração do projeto alvo e caminho da knowledge base |
| `templates.py` | `PPOMTemplates` | Geração de código TypeScript (spec, page, locators) |
| `prompt_builder.py` | `PromptBuilder` | Montagem de prompts contextuais com metodologia PPOM |
| `story_registry.py` | `StoryRegistry` | CRUD da base de conhecimento (histórias, regras, índice) |
| `dom_registry.py` | `DOMRegistry` | Análise de HTML, diff de DOM, geração de locators_map |
| `validator.py` | `validate_ppom_chain`, `validate_knowledge_consistency` | Validação estrutural |
| `cli.py` | CLI Typer | Ponto de entrada: `aqua-qe-playwright` |

## Regras da metodologia PPOM

### 1. A Spec é delegação pura
```typescript
// CORRETO: Spec apenas delega
test('HOME - CA1', { tag: ['@smoke'] }, async ({ page }) => {
  await home.verificarCarregamento();
  await home.cardDeveEstarDesabilitado(loc.LOC_CARD);
});

// ERRADO: Spec com seletor inline ou expect()
test('CA1', async ({ page }) => {
  await expect(page.locator('[data-testid="card"]')).toBeVisible(); // NÃO!
});
```

### 2. Page encapsula ações e asserções, sempre async
```typescript
// CORRETO
async verificarCarregamento(): Promise<this> {
  await expect(this.page.locator(loc.LOC_TITULO)).toBeVisible();
  return this;
}

// ERRADO: sem async, sem retorno this, locator inline
verificarCarregamento() {
  this.page.locator('[data-testid="title"]').isVisible(); // NÃO!
}
```

### 3. Locators é fonte única de verdade
```typescript
// CORRETO em locators/home.locators.ts
export const LOC_TITULO_HOME = '[data-testid="home-title"]';
export const URL_HOME = '/home';

// ERRADO: string de seletor direto na Page
await this.page.locator('[data-testid="home-title"]') // NÃO! Use LOC_*
```

### 4. Estratégia de locators (ordem de preferência)
1. `page.getByRole('button', { name: 'Confirmar' })` — semântica acessível
2. `page.getByTestId('confirm-btn')` — `data-testid` estável
3. `page.getByLabel('E-mail')` — campos de formulário
4. `page.getByText('Texto visível')` — como último recurso
5. `page.locator('[data-testid="..."]')` — constante `LOC_*` no arquivo locators

### 5. Tags no Playwright via objeto de opção
```typescript
// CORRETO
test('nome', { tag: ['@smoke', '@home', '@PWT-10'] }, async ({ page }) => {});

// ERRADO (Cypress way — não funciona no Playwright)
it('nome @smoke', () => {});
```

## Como adicionar um novo projeto

1. Criar diretório em `knowledge/{nome-projeto}/`
2. Copiar `modules_registry.yaml` e `stories_index.yaml` de `projeto_playwright_piloto/`
3. Usar `--project nome-projeto` nos subcomandos CLI

## Como adicionar um novo subcomando

1. Criar função no módulo relevante em `src/aqua_qe_playwright/`
2. Registrar como `@app.command()` em `cli.py`
3. Adicionar testes em `tests/test_{modulo}.py`

## Regras do validador PPOM

O `validate_ppom_chain(target_root, module)` verifica:

1. Existe pelo menos um `.spec.ts` em `tests/e2e/{module_slug}/`
2. Existe `pages/{ModulePascal}Page.ts`
3. Existe `locators/{module_slug}.locators.ts`
4. A Page importa `../locators/{module_slug}.locators`
5. Ao menos uma Spec importa `{ModulePascal}Page`

Qualquer item ausente → `valid: False` com erro descritivo em `errors[]`.

## Avisos importantes

- **Nunca usar `pip`** — apenas `uv add`, `uv sync`, `uv run`
- **Nunca importar LLM SDK** — este projeto é gerador de prompts, não cliente de IA
- **Templates TypeScript** devem ser válidos — testar import paths manualmente ao editar `templates.py`
- **Base de conhecimento em `knowledge/`** — nunca fazer hardcode de dados de projeto piloto no código
