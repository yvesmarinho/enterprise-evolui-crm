"""
lib/session_workflow.py — Orquestração unificada do workflow de sessão.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .git_session import collect_git_state, commit_all, push_current_branch
from .session_context import SessionPaths, recover_context, validate_mcp_config
from .session_docs import (
    build_session_files,
    ensure_session_files,
    validate_daily_file,
    write_end_of_session_docs,
)
from .session_security import scan_session_documents, scan_workspace


def _today_iso() -> str:
    return date.today().isoformat()


def _prepare_common_state(root: Path | str, *, today: str | None = None) -> dict[str, Any]:
    session_date = today or _today_iso()
    paths = SessionPaths.from_root(root)
    mcp = validate_mcp_config(paths).to_dict()
    context = recover_context(paths, today=session_date)
    git_state = collect_git_state(paths.root).to_dict()
    return {
        "paths": paths,
        "session_date": session_date,
        "mcp": mcp,
        "context": context,
        "git": git_state,
    }


def run_start(
    root: Path | str,
    *,
    first_time: bool = False,
    today: str | None = None,
) -> dict[str, Any]:
    """Executa o ritual enxuto de início de sessão."""

    state = _prepare_common_state(root, today=today)
    paths: SessionPaths = state["paths"]
    security = scan_workspace(paths)
    docs = ensure_session_files(
        paths,
        state["session_date"],
        state["context"],
        branch=state["git"].get("branch"),
        first_time=first_time,
    )
    ready = bool(state["mcp"]["ok"] and security["clean"])
    return {
        "command": "start-first" if first_time else "start",
        "root": str(paths.root),
        "date": state["session_date"],
        "mcp": state["mcp"],
        "context": state["context"],
        "git": state["git"],
        "docs": docs,
        "security": security,
        "ready": ready,
    }


def run_recover(root: Path | str, *, today: str | None = None) -> dict[str, Any]:
    """Recupera contexto sem executar o fluxo completo."""

    state = _prepare_common_state(root, today=today)
    return {
        "command": "recover",
        "root": str(state["paths"].root),
        "date": state["session_date"],
        "mcp": state["mcp"],
        "context": state["context"],
        "git": state["git"],
    }


def run_security_scan(root: Path | str) -> dict[str, Any]:
    """Executa scans do workspace e dos docs de sessão."""

    paths = SessionPaths.from_root(root)
    workspace = scan_workspace(paths)
    session_docs = scan_session_documents(paths)
    clean = workspace["clean"] and session_docs["clean"]
    return {
        "command": "security-scan",
        "root": str(paths.root),
        "workspace": workspace,
        "session_docs": session_docs,
        "clean": clean,
    }


def run_status(root: Path | str, *, today: str | None = None) -> dict[str, Any]:
    """Resume o estado atual da sessão."""

    state = _prepare_common_state(root, today=today)
    files = build_session_files(state["paths"], state["session_date"])
    daily_validation = (
        validate_daily_file(files) if files.daily.exists() else {"valid": False, "errors": []}
    )
    return {
        "command": "status",
        "root": str(state["paths"].root),
        "date": state["session_date"],
        "mcp": state["mcp"],
        "context": state["context"],
        "git": state["git"],
        "session_files": files.as_dict(state["paths"].root),
        "daily_validation": daily_validation,
    }


def run_end(
    root: Path | str,
    *,
    today: str | None = None,
    commit: bool = False,
    push: bool = False,
) -> dict[str, Any]:
    """Executa encerramento de sessão com atualização de docs."""

    state = _prepare_common_state(root, today=today)
    paths: SessionPaths = state["paths"]
    docs = ensure_session_files(
        paths,
        state["session_date"],
        state["context"],
        branch=state["git"].get("branch"),
    )
    files = build_session_files(paths, state["session_date"])
    workspace_security = scan_workspace(paths)
    session_docs_security = scan_session_documents(paths)
    daily_validation = validate_daily_file(files)
    doc_updates = write_end_of_session_docs(
        paths,
        state["session_date"],
        context=state["context"],
        git_summary=state["git"],
        security_summary=workspace_security,
        session_docs_security=session_docs_security,
        daily_validation=daily_validation,
    )

    commit_result: dict[str, Any] | None = None
    push_result: dict[str, Any] | None = None
    if commit:
        commit_result = commit_all(
            paths.root,
            title=f"docs(sessao): encerramento {state['session_date']}",
            body_lines=[
                f"Sessão {state['session_date']} encerrada com resumo automático.",
                f"Pendências capturadas: {len(state['context'].get('pending_todos', []))}",
                (
                    "Segurança do workspace: LIMPO"
                    if workspace_security["clean"]
                    else "Segurança do workspace: ATENÇÃO"
                ),
                (
                    "Session docs: PASSED"
                    if session_docs_security["clean"]
                    else "Session docs: ATENÇÃO"
                ),
            ],
        )
    if push:
        push_result = push_current_branch(paths.root)

    return {
        "command": "end",
        "root": str(paths.root),
        "date": state["session_date"],
        "mcp": state["mcp"],
        "context": state["context"],
        "git": collect_git_state(paths.root).to_dict(),
        "docs": docs,
        "doc_updates": doc_updates,
        "workspace_security": workspace_security,
        "session_docs_security": session_docs_security,
        "daily_validation": daily_validation,
        "commit": commit_result,
        "push": push_result,
        "ready_for_next_session": bool(
            workspace_security["clean"] and session_docs_security["clean"]
        ),
    }
