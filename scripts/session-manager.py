#!/usr/bin/env python3
"""
session-manager.py — CLI unificado para rituais de sessão.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from lib.session_workflow import (  # noqa: E402
    run_end,
    run_recover,
    run_security_scan,
    run_start,
    run_status,
)


def _print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _print_human(payload: dict[str, Any]) -> int:
    command = payload["command"]
    print(f"✅ session-manager: {command}")
    print(f"Raiz: {payload['root']}")
    if "date" in payload:
        print(f"Data: {payload['date']}")

    mcp = payload.get("mcp")
    if mcp:
        if mcp["ok"]:
            print("MCP: memory ✅ | sequential-thinking ✅")
        else:
            missing = ", ".join(mcp.get("missing_servers", [])) or "desconhecido"
            print(f"MCP: atenção — faltando {missing}")

    context = payload.get("context")
    if context:
        latest = context.get("latest_session_date") or "N/A"
        pending = context.get("pending_todos", [])
        print(f"Última sessão: {latest}")
        print(f"Pendências: {len(pending)}")

    security = payload.get("security")
    if security:
        status = "🟢 LIMPO" if security["clean"] else "🔴 ATENÇÃO"
        print(f"Segurança: {status}")

    workspace_security = payload.get("workspace_security")
    if workspace_security:
        status = "🟢 LIMPO" if workspace_security["clean"] else "🔴 ATENÇÃO"
        print(f"Workspace: {status}")

    session_docs_security = payload.get("session_docs_security")
    if session_docs_security:
        status = "🟢 PASSED" if session_docs_security["clean"] else "🔴 ATENÇÃO"
        print(f"Session docs: {status}")

    docs = payload.get("docs")
    if docs:
        statuses = docs.get("statuses", {})
        if statuses:
            summary = ", ".join(f"{name}={status}" for name, status in statuses.items())
            print(f"Docs: {summary}")

    git = payload.get("git")
    if git and git.get("is_repo"):
        branch = git.get("branch") or "(sem branch)"
        print(f"Git: {branch} | alterações pendentes={len(git.get('status_lines', []))}")

    daily_validation = payload.get("daily_validation")
    if daily_validation:
        print(
            "DAILY_ACTIVITIES: "
            + ("válido ✅" if daily_validation.get("valid") else "inválido ❌")
        )

    if payload.get("ready") is not None:
        print("Pronto para trabalhar." if payload["ready"] else "Há pendências antes de iniciar.")

    if payload.get("ready_for_next_session") is not None:
        if payload["ready_for_next_session"]:
            print("Pronto para a próxima sessão.")
        else:
            print("Encerramento concluído com alertas de segurança/validação.")

    commit_result = payload.get("commit")
    if commit_result:
        status = commit_result.get("status", "desconhecido")
        print(f"Commit: {status}")

    push_result = payload.get("push")
    if push_result:
        status = push_result.get("status", "desconhecido")
        print(f"Push: {status}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Workflow unificado de sessão para start, recover, status, security-scan e end.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Raiz do workspace (default: diretório atual)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída estruturada em JSON",
    )
    parser.add_argument(
        "--today",
        help="Sobrescreve a data da sessão (YYYY-MM-DD)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start", help="Início de sessão recorrente")
    subparsers.add_parser("start-first", help="Início de primeira sessão")
    subparsers.add_parser("recover", help="Recupera contexto da sessão")
    subparsers.add_parser("security-scan", help="Executa scans de segurança")
    subparsers.add_parser("status", help="Resume o estado atual")
    end_parser = subparsers.add_parser("end", help="Encerramento de sessão")
    end_parser.add_argument(
        "--commit",
        action="store_true",
        help="Cria commit automático do encerramento",
    )
    end_parser.add_argument(
        "--push",
        action="store_true",
        help="Executa push da branch atual",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "start":
        payload = run_start(args.root, today=args.today)
    elif args.command == "start-first":
        payload = run_start(args.root, first_time=True, today=args.today)
    elif args.command == "recover":
        payload = run_recover(args.root, today=args.today)
    elif args.command == "security-scan":
        payload = run_security_scan(args.root)
    elif args.command == "status":
        payload = run_status(args.root, today=args.today)
    elif args.command == "end":
        payload = run_end(
            args.root,
            today=args.today,
            commit=args.commit,
            push=args.push,
        )
    else:
        parser.error(f"Comando não suportado: {args.command}")

    if args.json:
        return _print_json(payload)
    return _print_human(payload)


if __name__ == "__main__":
    sys.exit(main())
