# REQUIREMENTS — AQuA-QE Playwright

> Requisitos funcionais, não-funcionais e metodológicos do assistente de qualidade
> para automação de testes Playwright/TypeScript com metodologia PPOM.

---

## Requisitos Funcionais

| ID | Requisito | Prioridade |
|----|-----------|-----------|
| RF-01 | O sistema DEVE gerar prompts contextuais a partir de histórias de usuário em texto livre | Alta |
| RF-02 | O sistema DEVE incluir nos prompts a metodologia PPOM com definição das 3 camadas | Alta |
| RF-03 | O sistema DEVE gerar templates de `.spec.ts`, `Page.ts` e `.locators.ts` válidos e funcionais | Alta |
| RF-04 | O sistema DEVE incluir no template de Spec: `test.describe`, `test.beforeEach`, `async/await`, `{ tag: [...] }` | Alta |
| RF-05 | O sistema DEVE incluir no template de Page: classe TypeScript, `constructor(private readonly page: Page)`, métodos `async` retornando `Promise<this>` | Alta |
| RF-06 | O sistema DEVE incluir no template de Locators: apenas constantes `LOC_*` e `URL_*` exportadas | Alta |
| RF-07 | O sistema DEVE analisar snapshots HTML e extrair atributos `data-testid`, `aria-label`, `role` para sugestão de locators | Alta |
| RF-08 | O sistema DEVE gerar locators priorizando: `getByRole()` > `getByTestId()` > `getByLabel()` > `locator('[data-testid]')` | Alta |
| RF-09 | O sistema DEVE detectar mudanças entre snapshots DOM e classificá-las como `BREAKING`, `RISCO` ou `INFO` | Alta |
| RF-10 | O sistema DEVE registrar histórias na base de conhecimento com critérios de aceite, regras de negócio e mapeamento PPOM | Alta |
| RF-11 | O sistema DEVE validar se a cadeia PPOM está correta: spec importa Page, page importa Locators | Alta |
| RF-12 | O sistema DEVE manter um registro de delta de regras de negócio por módulo | Média |
| RF-13 | O sistema DEVE oferecer CLI com subcomandos: `context`, `dom`, `knowledge`, `register`, `validate` | Alta |

---

## Requisitos Não-Funcionais

| ID | Requisito | Prioridade |
|----|-----------|-----------|
| RNF-01 | A CLI DEVE responder em menos de 2 segundos para operações locais (leitura de arquivo, geração de prompt) | Alta |
| RNF-02 | O código Python DEVE ter cobertura de testes superior a 80% medida por `pytest-cov` | Alta |
| RNF-03 | O projeto DEVE ser compatível com Python 3.12+ e gerenciado com `uv` | Alta |
| RNF-04 | Os templates gerados DEVEM ser válidos TypeScript — importações corretas, tipos explícitos | Alta |
| RNF-05 | A base de conhecimento DEVE ser portável: apenas arquivos YAML/Markdown/JSON | Média |
| RNF-06 | O projeto DEVE ter zero dependências de LLM em runtime — é um gerador de prompts, não um cliente de IA | Alta |

---

## Requisitos da Metodologia PPOM

| ID | Requisito | Descrição |
|----|-----------|-----------|
| RPPOM-01 | **Spec é delegação pura** | A Spec NÃO deve conter seletores inline nem lógica de UI — apenas instancia Page e delega |
| RPPOM-02 | **Page encapsula ações e asserções** | Todo `expect()` está na Page, não na Spec |
| RPPOM-03 | **Locators é fonte única de verdade** | Nenhuma string de seletor deve aparecer na Page ou na Spec — somente constantes de `.locators.ts` |
| RPPOM-04 | **Métodos Page são async** | Todo método da Page é `async` e retorna `Promise<this>` para encadeamento |
| RPPOM-05 | **Imports entre camadas seguem direção única** | Spec → Page → Locators; jamais Locators importa Page |
| RPPOM-06 | **Tags via objeto de opção** | Tags no Playwright seguem `{ tag: ['@smoke', '@modulo'] }` — não em describe string |

---

## Dependências do Projeto

| Pacote | Versão | Finalidade |
|--------|--------|-----------|
| `pyyaml` | `>=6.0` | Leitura/escrita de `modules_registry.yaml` e `stories_index.yaml` |
| `rich` | `>=13.0` | Formatação colorida de prompts no terminal |
| `typer` | via workspace | CLI |
| `pytest` | via workspace | Testes unitários |
| `pytest-cov` | via workspace | Cobertura de código |

---

## Dependências do Projeto Playwright Alvo

O AQuA-QE Playwright não instala estas dependências — ele gera código para projetos que as utilizam:

| Pacote | Versão | Finalidade |
|--------|--------|-----------|
| `@playwright/test` | `^1.40` | Framework de testes E2E |
| `typescript` | `^5.x` | Compilação TypeScript |
| `@types/node` | `^20` | Tipos Node.js |

---

## Critérios de Aceite de Cada Subcomando

### `context`
- [x] Recebe texto de história, módulo e story-id
- [x] Retorna prompt com cabeçalho PPOM + contexto da história
- [x] Prompt menciona `spec.ts`, `Page.ts`, `locators.ts`

### `dom`
- [x] Recebe arquivo HTML ou stdin
- [x] Extrai `data-testid`, `aria-label`, botões, campos, headings
- [x] Sugere constantes `LOC_*` com estratégia Playwright
- [x] Classifica mudanças BREAKING/RISCO/INFO quando `--diff` fornecido

### `knowledge`
- [x] Recebe query em linguagem natural
- [x] Retorna contexto da base de conhecimento relevante formatado

### `register`
- [x] Cria arquivo `stories/{ID}.md`
- [x] Atualiza `stories_index.yaml`
- [x] Cria/atualiza `rules_delta/{modulo}_rules_delta.md` se houver regras

### `validate`
- [x] Escopo `ppom`: verifica existência e imports das 3 camadas
- [x] Escopo `knowledge`: verifica consistência YAML ↔ arquivos de histórias
- [x] Escopo `all`: executa ambas as validações
- [x] Saída com lista de erros e status PASS/FAIL

---

*Eduardo Felizardo Cândido | Senior QA Automation Engineer | AI-driven Testing | Robot Framework*
