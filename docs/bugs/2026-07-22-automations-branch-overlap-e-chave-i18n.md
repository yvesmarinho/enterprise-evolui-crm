<!--
Criado em: 22/07/2026 11:20
Modificado em: 22/07/2026 11:35
-->

# Bug Report — Automations: card expandido sobrepõe branch vizinho + chave i18n crua no botão Delete

| Campo | Valor |
|---|---|
| **Severidade** | 🟠 Média |
| **Componente/Área** | Automations — builder visual (Condition If/Else) |
| **Status** | ✅ Corrigido |
| **Relator** | Yves Marinho |
| **Data do relato** | 22/07/2026 |

## Sintoma

Ao expandir um step "Send Message" dentro do branch **YES** de uma
Condition (If/Else), o card expandido (borda roxa, com o textarea
"Message text") cresce além da própria coluna e **sobrepõe** o card do
branch **NO** ao lado, cobrindo parte dele.

Além disso, o botão de exclusão do step expandido exibe o texto cru
`Automations.builder.delete` em vez de "Delete" — a chave de tradução
aparece sem ser resolvida.

## Passos para reproduzir

1. Em uma Automação, adicionar um step "Condition (If/Else)".
2. Adicionar um step "Send Message" no branch YES.
3. Expandir esse step (clicar no card).
4. Observar: (a) o card expandido se estende sobre a coluna do branch
   NO; (b) o botão de deletar mostra `Automations.builder.delete` em
   vez de "Delete".

## Comportamento esperado

- O card expandido deve permanecer contido dentro da largura da sua
  própria coluna (branch YES), sem sobrepor o branch NO.
- O botão de exclusão deve exibir o texto traduzido "Delete" (ou
  equivalente no idioma ativo).

## Causa raiz

### 1. Sobreposição de coluna (overflow)

`ConditionBranches` (`src/components/automations/automation-builder.tsx:1203-1215`)
organiza os branches YES/NO em `grid grid-cols-1 sm:grid-cols-2` — duas
colunas a partir do breakpoint `sm` (640px) do **viewport**.

Cada card de step (`StepRenderer`, mesmo arquivo, linha ~1093) usa
largura fixa `w-full max-w-[320px] sm:w-80` (320px a partir de `sm`) —
também amarrada ao breakpoint de **viewport**, não à largura real da
coluna do grid onde está inserido.

Quando o container do canvas de Automations é mais estreito que
`2 × 320px + gap` (~650px) mas o viewport do navegador já passou de
640px, o grid tenta caber duas colunas de 320px cada numa área menor —
e como os cards têm `z-10` e nenhum `overflow-hidden` no grid/coluna,
o card expandido da esquerda (YES) simplesmente estica sobre a coluna
da direita (NO) em vez de encolher ou quebrar linha.

Este é o **mesmo padrão de causa raiz** documentado em
`docs/bugs/2026-07-21-automations-send-list-texto-quebrado.md`:
larguras fixas amarradas a breakpoints de viewport (`sm:`, `md:`)
dentro de um canvas/painel cuja largura real de container é menor que
o viewport.

### 2. Chave i18n crua no botão Delete

`src/components/automations/automation-builder.tsx:1157`:

```tsx
{t("delete", { defaultValue: "Delete" })}
```

`next-intl` (v4, ver `package.json`) **não suporta** a opção
`defaultValue` — esse é um padrão do `i18next`, não do `next-intl`. O
segundo argumento de `t()` no next-intl são valores de interpolação
ICU, não opções de fallback. Como a chave `Automations.builder.delete`
não existe em `messages/en.json`, o `next-intl` cai no comportamento
padrão de mensagem ausente: renderiza a **chave completa** como texto
(`Automations.builder.delete`) em vez de qualquer fallback.

Mesmo padrão incorreto encontrado em outro ponto do arquivo (linha
1487, `config.closeConversationHint`) — mesmo bug, ainda não
reproduzido em print mas com a mesma causa.

## Evidências

- Print anexado pelo usuário em 22/07/2026 (chat), mostrando o card do
  branch YES sobreposto ao branch NO e o botão
  "Automations.builder.delete".

## Impacto

- **Usuários afetados**: todos que usam branches condicionais
  (If/Else) em Automations com steps expandidos, em containers/canvas
  mais estreitos que ~650px.
- **Risco de regressão da correção**: baixo — ajuste de CSS/grid e
  correção de chave de tradução, isolados.

## Correção proposta

1. **Overlap**: trocar a estratégia de largura fixa por breakpoint de
   viewport por algo resiliente ao container real — ex.: usar
   `min-width: 0` nas colunas do grid + `w-full` sem `sm:w-80` fixo
   nos cards (deixando o grid controlar a largura da coluna), ou migrar
   para container queries (`@container`) em vez de `sm:`/`md:` do
   Tailwind, consistente com a correção já aplicada no bug do Send
   List.
2. **Chave i18n**: substituir `t("delete", { defaultValue: "Delete" })`
   por uma chamada válida — adicionar a chave `delete` (e
   `config.closeConversationHint`) em `messages/en.json` e usar
   `t("delete")` sem `defaultValue`; se o texto de fallback for
   necessário antes de existir a chave, usar `useTranslations` com
   `getMessageFallback` centralizado em `src/i18n/request.ts` (não por
   chamada).

## Correção aplicada (22/07/2026)

1. **Overlap**: em `StepRenderer`
   (`src/components/automations/automation-builder.tsx`), a largura do
   card mudou de `w-full max-w-[320px] sm:w-80` /
   `w-full max-w-[400px] sm:w-[400px]` para `w-full max-w-80` /
   `w-full max-w-[400px]` — sem largura fixa por breakpoint, o card
   nunca ultrapassa a largura real do seu container (grid column).
   Adicionado também `min-w-0` em `BranchColumn` para permitir que a
   coluna do grid encolha corretamente em vez de manter o tamanho
   mínimo de conteúdo.
2. **Chave i18n**: `t("delete", { defaultValue: "Delete" })` →
   `t("delete")`, com a chave `Automations.builder.delete: "Delete"`
   adicionada em `messages/en.json`. `t("config.closeConversationHint", { defaultValue: ... })`
   → `t("config.closeConversationHint")` (a chave já existia no JSON,
   só o `defaultValue` supérfluo foi removido).

Validado com `pnpm typecheck` (sem erros) e `python3 -m json.tool` no
`messages/en.json` (JSON válido).

## Atualização (22/07/2026) — overlap persistiu, causa raiz adicional

Após deploy da correção acima, o usuário reportou (novo print) que o
overlap **persistia mesmo com os cards colapsados** (não só
expandidos). Causa raiz adicional: `StepList` e `BranchColumn`
(`src/components/automations/automation-builder.tsx`) usam
`items-center` (cross-axis, não `stretch`) **sem `w-full` explícito**
em nenhum nível da cadeia. Sem uma largura imposta, o card
(`w-full max-w-80`/`w-full max-w-[400px]`) resolvia seu `w-full` contra
um container pai que não estava, ele mesmo, limitado à largura real da
coluna do grid — renderizando o card no seu tamanho **máximo**
(320px/400px) independentemente de quão estreita a coluna realmente
era, extravasando sobre a coluna vizinha.

**Correção**: adicionado `w-full min-w-0` tanto em `StepList`
(`flex flex-col items-center` → `flex w-full min-w-0 flex-col
items-center`) quanto em `BranchColumn` (mesma mudança), forçando
cada nível da árvore a herdar a largura real de seu container em vez
de depender do comportamento implícito de dimensionamento em
cross-axis de flexbox com `items-center`.

## Prevenção

- Auditar o restante do arquivo por outros usos de
  `{ defaultValue: ... }` com `next-intl` (não é uma opção válida da
  lib) — grep `defaultValue:` em `src/` antes de cada PR que mexa em
  i18n.
- Ao usar breakpoints Tailwind (`sm:`, `md:`) em componentes que podem
  ser embutidos em canvases/painéis mais estreitos que o viewport,
  preferir container queries ou testar explicitamente em larguras de
  container reduzidas, não apenas redimensionando a janela do
  navegador.
