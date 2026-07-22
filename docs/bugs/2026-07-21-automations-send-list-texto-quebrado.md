<!--
Criado em: 22/07/2026 09:59
Modificado em: 22/07/2026 10:15
-->

# Bug Report — Texto do "body message" exibido um caractere por linha (Automations → Send List)

| Campo | Valor |
|---|---|
| **Severidade** | 🔴 Alta |
| **Componente/Área** | Automations |
| **Status** | ✅ Corrigido |
| **Relator** | Yves Marinho |
| **Data do relato** | 21/07/2026 |
| **URL de reprodução** | https://evolui-crm.vya.digital/automations/b7c0a99b-fc8e-4d84-b940-b1123e36689e/edit |

## Sintoma

Ao criar/editar uma Automação, dentro de "Adicionar novo item de automação
→ Send List", ao clicar em um item existente (ou adicionar um novo), o
texto do "body message" não é exibido corretamente: aparece **um
caractere por linha**, tornando o conteúdo ilegível. O problema ocorre
em todos os itens do combo/lista.

## Passos para reproduzir

1. Acessar uma Automação existente (ex.: URL acima) ou criar uma nova.
2. Adicionar um novo item de automação e selecionar "Send List".
3. Selecionar/abrir um item da lista (existente ou recém-criado).
4. Observar o campo de "body message": o texto é renderizado com um
   caractere por linha em vez de fluir normalmente.

## Comportamento esperado

O texto do "body message" deve ser exibido normalmente (quebra de linha
por palavra/parágrafo, não por caractere).

## Comportamento atual

Texto quebrado a cada caractere, tornando o conteúdo ilegível.

## Hipótese de causa raiz

Sintoma típico de renderização de string como array/iterável em vez de
texto — por exemplo, um componente React que itera `body.split("")` ou
recebe a string diretamente como `children` de um container `flex-col`
sem um wrapper de texto (cada caractere vira um item flex, quebrando
linha a cada um).

**Investigação de código (22/07/2026)**: revisada toda a cadeia de
componentes envolvida em Automations → Send List:

- `src/components/automations/automation-builder.tsx` (`StepEditor`,
  `previewFor`) — delega para `InteractiveBuilder`; preview truncado
  via `interactivePayloadPreviewText(...)` dentro de
  `<div className="truncate text-[11px] ...">` (string única).
- `src/components/interactive/interactive-builder.tsx` (linhas
  107-115) — campo Body é `<Textarea value={value.body}
  onChange={(e) => setField({ body: e.target.value })} />`, binding
  padrão de string.
- `src/components/interactive/interactive-preview.tsx` (linhas
  37-41) — preview renderiza `<p className="whitespace-pre-wrap
  break-words text-sm">{payload.body || <span>...</span>}</p>`, string
  inteira como único child.
- `src/lib/whatsapp/interactive.ts` (`interactivePayloadPreviewText`,
  linhas 233-239) — retorna `payload.body?.trim()` sem manipulação
  caractere a caractere.
- Equivalente em Flows (`src/components/flows/forms/node-config-form.tsx`
  `SendListForm`, `src/components/flows/forms/fields.tsx`,
  `src/components/ui/textarea.tsx`) — mesmo padrão correto.

Busca em todo o repositório por `.split('')`, `.split("")`,
`Array.from(`, spread de string (`[...texto]`) e `.map((c,`/
`.map((char` não encontrou nenhuma ocorrência aplicada a campos de
`body`/`text`/mensagem — os únicos usos de `Array.from` no projeto são
para placeholders de skeleton/testes.

**Conclusão**: no HEAD atual não há trecho de JSX que explique o
sintoma. Hipóteses restantes a verificar (fora do alcance de leitura de
código):

1. **Bug já corrigido** — pode ter existido antes do commit `78b42df`
   ("feat: WhatsApp interactive messages") e o usuário estar com
   build/cache antigo (`.next` stale) ou branch desatualizada no
   momento do print.
2. **CSS externo** aplicando `writing-mode: vertical-lr` ou
   `flex-direction: column` sobre o `<p>`/`<textarea>` do modal — não
   encontrado `writing-mode` em nenhum arquivo do projeto, mas vale
   inspecionar estilos computados no DevTools durante nova reprodução.
3. **Extensão de navegador / tradução automática** interferindo no DOM
   (menos provável).

**Próximo passo**: reproduzir novamente em `main` atualizado, sem
cache, e se persistir, inspecionar o elemento no DevTools (estilos
computados do `<p>`/`<textarea>` do body) durante a reprodução.

## Evidências

- `docs/bugs/attachments/2026-07-21-automations-send-list/image-1.png`
- `docs/bugs/attachments/2026-07-21-automations-send-list/image-2.png`
- HTML da página capturado no momento do bug (ver anexo
  `page-source.html` na mesma pasta) — omitido aqui por tamanho.

## Impacto

- **Usuários afetados**: todos que usam Automations → Send List.
- **Risco de regressão da correção**: baixo (isolado ao componente de
  exibição de texto).

## Causa raiz confirmada

Print de reprodução (22/07/2026) mostrou o campo "Body" com largura
colapsada para poucos pixels, com o painel "Preview" sobreposto ao
lado — confirmando quebra de layout, não bug de JSX/string.

`src/components/ui/textarea.tsx:10` aplicava a classe Tailwind
`field-sizing-content` (CSS `field-sizing: content`) no `<textarea>`
base, usado por 9 componentes do projeto (`InteractiveBuilder`
incluso). Essa propriedade faz o elemento se auto-dimensionar ao
conteúdo. Dentro do editor de "Send List"
(`src/components/interactive/interactive-builder.tsx`), o campo Body
fica em um container `flex-1 min-w-0` ao lado do painel de Preview com
largura fixa (`md:w-[280px]`). Quando o espaço disponível é pequeno
(popup estreito), `field-sizing: content` colapsava a largura do
`<textarea>` para quase zero em vez de respeitar `w-full`, forçando o
texto a quebrar a cada caractere para caber.

## Correção aplicada

Removida a classe `field-sizing-content` de
`src/components/ui/textarea.tsx` (22/07/2026), mantendo `w-full` +
`min-h-16`. O textarea continua crescendo em altura normalmente ao
digitar; apenas o auto-dimensionamento de largura (causador do bug) foi
removido. Nenhum dos 9 usos do componente dependia desse comportamento
de largura.

## Prevenção

Evitar `field-sizing-content`/`field-sizing: auto` em campos dentro de
containers flex com painéis de largura fixa ao lado, sem testar em
contêineres estreitos (popups, drawers, sidebars) — o comportamento de
auto-sizing pode entrar em conflito com `w-full`/`flex-1 min-w-0`
nesses casos.

## Atualização (22/07/2026) — causa raiz real e correção definitiva

O fix acima (remover `field-sizing-content`) não resolveu — novo print
mostrou TODOS os campos do painel (Header, List button label, Rows),
não só o Body, espremidos e sobrepostos. Isso indicava causa
estrutural no container pai, não isolada no `Textarea`.

**Causa raiz real**: `InteractiveBuilder`
(`src/components/interactive/interactive-builder.tsx:91`) usa layout
`flex flex-col gap-4 md:flex-row`, alternando para lado-a-lado
(campos + painel de Preview fixo em `md:w-[280px]`) a partir do
breakpoint `md` (768px) do **viewport do navegador** — não da largura
do container onde está inserido.

Em Automations, o `StepEditor` (`automation-builder.tsx`) renderiza o
`InteractiveBuilder` dentro do card de step, que é limitado a
`max-w-[320px] sm:w-80` (320px). Em qualquer tela desktop (viewport
≥768px), o `md:flex-row` ativava mesmo com o card tendo só 320px de
largura, forçando os campos a dividirem espaço com o painel de Preview
de 280px fixos — sobrando poucos pixels para tudo, causando a quebra
de texto caractere a caractere e sobreposição de labels.

**Correção aplicada**: `InteractiveBuilder` já aceita a prop
`showPreview` (default `true`). Passado `showPreview={false}` na
chamada dentro de `StepEditor`
(`src/components/automations/automation-builder.tsx`, caso
`send_buttons`/`send_list`), já que não há espaço útil para preview
lado a lado dentro do card de 320px. Sem a coluna de Preview, o
`InteractiveBuilder` ocupa a largura total do card normalmente.

**Status**: ambas as correções (remoção do `field-sizing-content` +
`showPreview={false}` no contexto do step editor) aplicadas. Aguardando
nova build/print de confirmação do usuário.
