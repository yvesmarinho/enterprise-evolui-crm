---
mode: agent
description: Ritual de início de sessão recorrente. Execute no começo de cada sessão de trabalho.
---

# 🚀 Session Start — Ritual de Início de Sessão

> Use este ritual no início de cada sessão recorrente.

## Execução

1. Rode:

```bash
python scripts/session-manager.py start --json
```

2. Interprete o retorno:
   - `mcp.ok == true` → configuração MCP válida
   - `security.clean == true` → sem arquivos sensíveis fora de `.secrets/`
   - `context.latest_session_date` → última sessão recuperada
   - `context.pending_todos` → prioridades imediatas
   - `docs.statuses` → arquivos canônicos da sessão garantidos

3. Se `security.clean == false`, pare e reporte.

4. Confirme manualmente no VS Code apenas se necessário:
   - `Command Palette → MCP: List Servers`
   - `Command Palette → MCP: Refresh Servers`

5. Depois do resumo automático, peça ao usuário apenas:
   - modo da sessão: `PROGRAMMING | INFRASTRUCTURE | ANALYSIS`
   - objetivo da sessão em 1 frase

## Referências

- Guia canônico de docs de sessão: `docs/guides/SESSION_DOCS_STYLE_GUIDE.md`
- Status rápido sem recriar contexto: `python scripts/session-manager.py status --json`
- Recuperação isolada: `python scripts/session-manager.py recover --json`
