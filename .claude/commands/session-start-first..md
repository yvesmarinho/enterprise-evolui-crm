---
mode: agent
description: Ritual de primeira sessão em um projeto novo ou recém-clonado. Use apenas na primeira vez.
---

# 🌱 Session Start (First Time) — Ritual de Primeira Sessão

> Use este ritual apenas na primeira sessão de um projeto novo ou recém-clonado.

## Execução

1. Se a estrutura do projeto ainda não existe, inicialize com o scaffold:

```bash
uv run scripts/scaffold.py new
```

2. Depois rode o ritual enxuto:

```bash
python scripts/session-manager.py start-first --json
```

3. Interprete o retorno:
   - `mcp` valida `.vscode/mcp.json`
   - `security` faz o scan inicial
   - `docs` garante `SESSION_RECOVERY`, `DAILY_ACTIVITIES`, `SESSION_REPORT` e `FINAL_STATUS`
   - `context.pending_todos` mostra os primeiros itens do `docs/TODO.md`

4. Se o usuário estiver num projeto já scaffoldado, pule o passo 1 e execute só o CLI.

5. Só peça input humano para:
   - domínio/modo da sessão
   - objetivo da primeira sessão
   - confirmação manual do status dos MCP servers no VS Code

## Referências

- Verificação de links do scaffold: `uv run scripts/scaffold.py check`
- Guia de docs de sessão: `docs/guides/SESSION_DOCS_STYLE_GUIDE.md`
- Status rápido após scaffold: `python scripts/session-manager.py status --json`
