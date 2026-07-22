<!--
Criado em: 22/07/2026 12:40
Modificado em: 22/07/2026 12:40
-->

# Bug Report — Automations: editar/excluir/mover step dentro de um branch não funciona (silenciosamente)

| Campo | Valor |
|---|---|
| **Severidade** | 🔴 Alta |
| **Componente/Área** | Automations — builder visual (Condition If/Else) |
| **Status** | ✅ Corrigido |
| **Relator** | Yves Marinho |
| **Data do relato** | 22/07/2026 |

## Sintoma

Dentro de um branch (YES/NO) de uma Condition (If/Else), o botão
"Delete" de um step não remove o step — e nenhum erro aparece no
console nem na UI.

## Causa raiz

`ConditionBranches` (`src/components/automations/automation-builder.tsx`)
monta `yesPath`/`noPath` acrescentando um segmento **placeholder** ao
path do step Condition:

```ts
const yesPath: StepPath = [
  ...parentPath,
  { kind: "branch", parentCid: step.cid, branch: "yes", index: 0 },
]
```

O comentário no código deixa claro a intenção: esse `index: 0` é só um
placeholder porque `StepList` deriva o `parentScope` do **último**
elemento do path — "the tail's index doesn't matter — it's replaced
per child during walks".

Só que `StepRenderer` (mesmo arquivo) não *substituía* esse segmento
placeholder pelo segmento real do step filho — ele *acrescentava* mais
um:

```ts
const path: StepPath = [
  ...parentPath,
  parentScope.kind === "root"
    ? { kind: "root", index }
    : { kind: "branch", parentCid: parentScope.parentCid, branch: parentScope.branch, index },
]
```

Resultado: todo step dentro de um branch termina com **dois**
segmentos `branch` consecutivos no path em vez de um só — um a mais do
que a árvore real tem de profundidade. As funções de navegação
recursiva (`removeAt`/`removeFromBranches`, `mapAtPath`/`walkBranches`,
`moveAt`/`moveInBranches`) tratam cada segmento do path como "descer
mais um nível" — com o segmento extra, elas processam o **placeholder**
como se fosse a seleção do filho real (usando seu índice fixo `0`) e
recursam mais um nível do que deveriam, entrando em `child.branches`
(que é `undefined` para um step que não é Condition) e retornando sem
fazer nada — silenciosamente.

**Por que "funcionava" no exemplo do print**: o branch tinha só 1 item
(índice real 0), que por coincidência é igual ao índice do placeholder
(sempre 0). Editar o texto do "Message text" funcionava (também por
essa coincidência). Qualquer step que não seja o **primeiro** do
branch nunca teria suas edições salvas, nunca seria excluído, e nunca
seria movido — sem erro visível, porque a função apenas retorna uma
árvore estruturalmente idêntica.

## Correção aplicada

Em `StepRenderer`, quando `parentScope.kind === "branch"`, o path
agora **substitui** o último segmento de `parentPath` (o placeholder)
pelo segmento real, em vez de concatenar mais um:

```ts
const path: StepPath =
  parentScope.kind === "root"
    ? [...parentPath, { kind: "root", index }]
    : [
        ...parentPath.slice(0, -1),
        { kind: "branch", parentCid: parentScope.parentCid, branch: parentScope.branch, index },
      ]
```

Isso corrige `updateStep`, `deleteStepAt` e `moveStepAt` para
**qualquer** step dentro de um branch, em qualquer posição — não só
para o índice 0 — e também para Conditions aninhadas dentro de
branches (o path acumula corretamente um segmento por nível de
aninhamento).

Validado com `pnpm typecheck` (sem erros).

## Impacto

- **Usuários afetados**: todos que usam branches (If/Else) com mais de
  um step em algum branch — edição, exclusão e reordenação do 2º step
  em diante simplesmente não tinham efeito, sem nenhum aviso.
- **Risco de regressão**: baixo — mudança isolada na construção do
  path, sem alterar a estrutura de dados nem as funções de navegação.

## Prevenção

- Ao adicionar um "marcador" (placeholder) a uma estrutura que será
  posteriormente completada/substituída por outro nível do código,
  preferir tornar essa relação explícita no tipo (ex.: um campo
  `index?: number` opcional, ou um tipo `ScopeMarker` distinto de
  `PathSegment`) em vez de reaproveitar o mesmo tipo com um valor
  sentinela (`index: 0`) — isso evita que o código consumidor esqueça
  de substituir e apenas concatene.
- Testar manualmente branches com **2+ steps** ao alterar a lógica de
  `StepPath`/navegação da árvore de Automations — o bug só se
  manifesta a partir do 2º item.
