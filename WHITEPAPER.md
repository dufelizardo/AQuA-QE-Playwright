# WHITEPAPER — AQuA-QE Playwright

**Artificial Quality Assurance — Quality Engineering para Playwright/TypeScript**

*Versão 1.0 | Julho 2026*

---

## Resumo Executivo

O **AQuA-QE Playwright** é um sistema de assistência à qualidade de software que combina governança de conhecimento, geração de prompts e validação estrutural para equipes que adotam automação de testes com Playwright e TypeScript. A ferramenta implementa a metodologia **PPOM** (Playwright Page Object Model), uma arquitetura de 3 camadas que promove separação rigorosa de responsabilidades e máxima reutilização de código de teste.

---

## 1. Contexto e Motivação

A automação de testes com Playwright se tornou padrão para aplicações web modernas devido à sua confiabilidade, suporte nativo a múltiplos navegadores e API assíncrona de alto nível. Entretanto, equipes de QA frequentemente enfrentam três desafios recorrentes:

**1. Acoplamento de seletores**: Strings de CSS ou XPath espalhadas pelos arquivos de teste tornam o código frágil — uma mudança de `data-testid` quebra dezenas de testes.

**2. Lógica de UI na Spec**: Testes com `expect()` e `locator()` diretos nas specs violam o princípio de responsabilidade única e dificultam a manutenção.

**3. Ausência de memória institucional**: Regras de negócio, critérios de aceite e histórico de mudanças de DOM ficam dispersos em Jira, Confluence e cabeças de desenvolvedores.

O AQuA-QE Playwright foi criado para resolver esses três problemas simultaneamente.

---

## 2. Metodologia PPOM

### 2.1 Definição das 3 Camadas

A **PPOM (Playwright Page Object Model)** organiza o código de teste em três camadas com responsabilidades exclusivas:

```
┌─────────────────────────────────────────────────────────┐
│  SPEC  tests/e2e/{modulo}/{story}.spec.ts               │
│  ─ test.describe() com async/await                       │
│  ─ Delega tudo para Page; zero lógica de UI             │
│  ─ Tags via { tag: ['@smoke', '@modulo'] }               │
└────────────────────┬────────────────────────────────────┘
                     │ importa
┌────────────────────▼────────────────────────────────────┐
│  PAGE  pages/{Modulo}Page.ts                            │
│  ─ Classe TypeScript; constructor(readonly page: Page)  │
│  ─ Métodos async que retornam Promise<this>             │
│  ─ Encapsula expect() e lógica de interação UI          │
└────────────────────┬────────────────────────────────────┘
                     │ importa
┌────────────────────▼────────────────────────────────────┐
│  LOCATORS  locators/{modulo}.locators.ts                │
│  ─ Apenas constantes LOC_* e URL_* exportadas           │
│  ─ Fonte única de verdade para todos os seletores       │
│  ─ Nunca importa Page ou Spec                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Código de Referência Completo

#### `locators/home.locators.ts`
```typescript
export const URL_HOME = '/home';
export const LOC_TITULO_HOME = '[data-testid="home-title"]';
export const LOC_CARD_MINHA_OPERACAO = '[data-testid="card-minha-operacao"]';
export const LOC_BTN_ACESSAR = '[data-testid="card-cta-acessar"]';
```

#### `pages/HomePage.ts`
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

  async cardDeveEstarDesabilitado(locatorCard: string): Promise<this> {
    await expect(this.page.locator(locatorCard))
      .toHaveAttribute('aria-disabled', 'true');
    return this;
  }
}
```

#### `tests/e2e/home/pwt-10.spec.ts`
```typescript
import { test } from '@playwright/test';
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
    async () => {
      await home.cardDeveEstarDesabilitado(loc.LOC_CARD_MINHA_OPERACAO);
    }
  );
});
```

### 2.3 Estratégia de Locators

O Playwright oferece múltiplas formas de localizar elementos. A PPOM define uma hierarquia de preferência:

| Prioridade | Estratégia | Quando usar |
|-----------|-----------|------------|
| 1 | `getByRole('button', { name: 'X' })` | Botões e links com texto semântico |
| 2 | `getByTestId('data-testid-value')` | Atributo `data-testid` presente |
| 3 | `getByLabel('E-mail')` | Campos de formulário com label |
| 4 | `getByText('Texto')` | Elementos identificados por conteúdo |
| 5 | `locator('[data-testid="..."]')` | Constante `LOC_*` em `.locators.ts` |

---

## 3. Arquitetura do AQuA-QE Playwright

### 3.1 Módulos Python

```
src/aqua_qe_playwright/
├── config.py          ← AQuAConfig: caminho do projeto e knowledge base
├── templates.py       ← PPOMTemplates: geração de código TypeScript
├── prompt_builder.py  ← PromptBuilder: prompts para assistentes de IA
├── story_registry.py  ← StoryRegistry: CRUD da base de conhecimento
├── dom_registry.py    ← DOMRegistry: análise de HTML e diff de DOM
├── validator.py       ← Validação estrutural PPOM e conhecimento
└── cli.py             ← CLI: ponto de entrada `aqua-qe-playwright`
```

### 3.2 Agentes de IA (Prompts)

```
prompts/
├── orchestrator.md    ← Orquestrador: roteamento de intenções
├── story_analyzer.md  ← Análise de histórias Jira → JSON estruturado
├── test_generator.md  ← Geração de código Playwright PPOM
├── dom_watcher.md     ← Análise de DOM → locators e diff de impacto
└── knowledge_agent.md ← Consulta à base de conhecimento governada
```

---

## 4. Base de Conhecimento

A base de conhecimento é um conjunto de arquivos locais que persiste a memória institucional do projeto de testes:

```
knowledge/{projeto}/
├── modules_registry.yaml   ← Módulos PPOM registrados com aliases e área funcional
├── stories_index.yaml      ← Índice de histórias com módulo, tags e mapeamento PPOM
├── stories/                ← Documentação completa por história (Markdown)
│   └── PWT-XXX.md
├── rules_delta/            ← Ledger de regras novas e descontinuadas por módulo
│   └── {modulo}_rules_delta.md
└── dom/                    ← Contratos e snapshots de UI
    ├── index.json
    └── modules/{modulo}/
        ├── snapshots/      ← HTML capturado em cada versão
        ├── contracts/      ← dom_contract.json (estado atual da UI)
        └── locators/       ← locators_map.json (locators aprovados)
```

### 4.1 Governança DOM

O `DOMRegistry` processa snapshots HTML capturados em cada sprint ou release e:

1. Extrai o contrato DOM atual (headings, botões, campos, `data-testid`)
2. Compara com o snapshot anterior e classifica mudanças
3. Gera sugestões de locators em formato TypeScript
4. Mantém um índice de rastreabilidade entre UI e testes

---

## 5. Ciclo de Trabalho com IA

```
Jira Story
    │
    ▼
aqua-qe-playwright context → Prompt estruturado com PPOM
    │
    ▼
Assistente de IA (Claude, GPT, Gemini)
    │
    ▼
Código Playwright gerado (.spec.ts + Page.ts + .locators.ts)
    │
    ▼
aqua-qe-playwright validate → Verificação estrutural PPOM
    │
    ▼
aqua-qe-playwright register → Base de conhecimento atualizada
    │
    ▼
Pipeline CI/CD (playwright test --grep @smoke)
```

---

## 6. Benefícios Mensuráveis

| Benefício | Impacto Esperado |
|-----------|-----------------|
| Redução de seletores frágeis | 90%+ dos seletores via constantes `LOC_*` |
| Velocidade de geração de testes | De horas para minutos com IA contextualizada |
| Cobertura de critérios de aceite | Rastreabilidade 1:1 história → test case |
| Manutenção em mudanças de DOM | Impacto isolado ao arquivo `.locators.ts` |
| Onboarding de novos QEs | Prompts e base de conhecimento aceleram rampa |

---

## 7. Integração com CI/CD

O AQuA-QE Playwright não executa testes — gera o código. A integração CI/CD é no projeto alvo:

```yaml
# .github/workflows/playwright.yml (projeto alvo)
- name: Run smoke tests
  run: npx playwright test --grep @smoke

- name: Validate PPOM structure
  run: uv run aqua-qe-playwright validate --target . --scope all
```

---

## 8. Diferenças do AQuA-QE Cypress

| Aspecto | AQuA-QE Cypress | AQuA-QE Playwright |
|---------|----------------|-------------------|
| Metodologia | CPOM | PPOM |
| API de testes | `describe`/`it` (síncrono) | `test.describe`/`test` (async/await) |
| Seletores | `data-cy` prioritário | `data-testid` + `getByRole()` |
| Tags | Em string `{ tags: [] }` | Em objeto `{ tag: [] }` |
| Page pattern | `return this` síncrono | `async` + `Promise<this>` |
| Camada 3 | `.selectors.ts` | `.locators.ts` |

---

## Conclusão

O AQuA-QE Playwright implementa uma abordagem disciplinada e governada para automação de testes com Playwright. A metodologia PPOM garante que o código de teste seja legível, manutenível e resistente a mudanças de UI. A base de conhecimento local preserva a memória institucional do projeto. Os agentes de IA especializados transformam histórias Jira em código funcional em minutos.

---

*Eduardo Felizardo Cândido | Senior QA Automation Engineer | AI-driven Testing | Robot Framework*
