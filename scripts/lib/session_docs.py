"""
lib/session_docs.py — Criação e atualização de documentos de sessão.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .session import validate_daily_activities_format
from .session_context import SessionPaths


def _render_bullets(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


@dataclass(frozen=True)
class SessionFiles:
    """Arquivos canônicos de uma sessão diária."""

    session_dir: Path
    recovery: Path
    daily: Path
    report: Path
    final_status: Path

    def as_dict(self, root: Path) -> dict[str, str]:
        return {
            "session_dir": str(self.session_dir.relative_to(root)),
            "recovery": str(self.recovery.relative_to(root)),
            "daily": str(self.daily.relative_to(root)),
            "report": str(self.report.relative_to(root)),
            "final_status": str(self.final_status.relative_to(root)),
        }


def build_session_files(paths: SessionPaths, session_date: str) -> SessionFiles:
    session_dir = paths.sessions_dir / session_date
    return SessionFiles(
        session_dir=session_dir,
        recovery=session_dir / f"SESSION_RECOVERY_{session_date}.md",
        daily=session_dir / f"DAILY_ACTIVITIES_{session_date}.md",
        report=session_dir / f"SESSION_REPORT_{session_date}.md",
        final_status=session_dir / f"FINAL_STATUS_{session_date}.md",
    )


def _ensure_file(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return "existing"
    path.write_text(content, encoding="utf-8")
    return "created"


def _build_recovery_content(
    session_date: str,
    context: dict[str, Any],
    branch: str | None,
    *,
    first_time: bool,
) -> str:
    latest_session = context.get("latest_session_date") or "N/A"
    pending = context.get("pending_todos", [])
    pending_block = _render_bullets(
        pending,
        "Nenhum item pendente identificado em docs/TODO.md.",
    )
    previous_label = "Primeira sessão" if first_time else latest_session

    return (
        f"# 🔄 Session Recovery — {session_date}\n\n"
        f"**Sessão anterior**: {previous_label}\n"
        f"**Branch**: {branch or '(não disponível)'}\n\n"
        "## Contexto Recuperado\n\n"
        f"- README: {'✅' if context.get('readme_exists') else '❌'}\n"
        f"- TODO: {'✅' if context.get('todo_exists') else '❌'}\n"
        f"- INDEX: {'✅' if context.get('index_exists') else '❌'}\n"
        f"- Rules: {'✅' if context.get('rules_exists') else '❌'}\n\n"
        "## Itens Prioritários\n\n"
        f"{pending_block}\n"
    )


def _build_daily_content(session_date: str) -> str:
    return (
        f"# 📅 Daily Activities — {session_date}\n\n"
        f"**Data**: {session_date}\n\n"
        "---\n"
    )


def _build_report_content(session_date: str) -> str:
    return (
        f"# 📘 Session Report — {session_date}\n\n"
        f"**Data**: {session_date}\n\n"
        "## Resumo automático\n\n"
        "- Sessão iniciada.\n"
    )


def _build_final_status_content(session_date: str) -> str:
    return (
        f"# 📊 Final Status — {session_date}\n\n"
        f"**Data**: {session_date}\n\n"
        "## Estado atual\n\n"
        "- Em preparação.\n"
    )


def ensure_session_files(
    paths: SessionPaths,
    session_date: str,
    context: dict[str, Any],
    *,
    branch: str | None = None,
    first_time: bool = False,
) -> dict[str, Any]:
    """Garante a existência dos arquivos da sessão atual."""

    files = build_session_files(paths, session_date)
    statuses = {
        "recovery": _ensure_file(
            files.recovery,
            _build_recovery_content(
                session_date,
                context,
                branch,
                first_time=first_time,
            ),
        ),
        "daily": _ensure_file(files.daily, _build_daily_content(session_date)),
        "report": _ensure_file(files.report, _build_report_content(session_date)),
        "final_status": _ensure_file(
            files.final_status,
            _build_final_status_content(session_date),
        ),
    }
    return {"files": files.as_dict(paths.root), "statuses": statuses}


def upsert_section(path: Path, heading: str, body: str) -> None:
    """Insere ou substitui uma seção `##` pelo mesmo título."""

    section_text = f"## {heading}\n\n{body.strip()}\n"
    if not path.exists():
        path.write_text(section_text, encoding="utf-8")
        return

    content = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?ms)^## {re.escape(heading)}\n.*?(?=^## |\Z)",
    )
    if pattern.search(content):
        updated = pattern.sub(section_text, content)
    else:
        separator = "\n\n" if not content.endswith("\n\n") else ""
        updated = f"{content.rstrip()}{separator}{section_text}"
    path.write_text(updated.rstrip() + "\n", encoding="utf-8")


def validate_daily_file(files: SessionFiles) -> dict[str, Any]:
    """Valida o DAILY_ACTIVITIES atual usando a lib canônica."""

    content = files.daily.read_text(encoding="utf-8")
    stripped = content.strip()
    if stripped.startswith("# 📅 Daily Activities") and stripped.endswith("---"):
        return {"valid": True, "errors": []}

    is_valid, errors = validate_daily_activities_format(files.daily)
    return {
        "valid": is_valid,
        "errors": errors,
    }


def write_end_of_session_docs(
    paths: SessionPaths,
    session_date: str,
    *,
    context: dict[str, Any],
    git_summary: dict[str, Any],
    security_summary: dict[str, Any],
    session_docs_security: dict[str, Any],
    daily_validation: dict[str, Any],
) -> dict[str, Any]:
    """Atualiza SESSION_REPORT e FINAL_STATUS com resumo automático."""

    files = build_session_files(paths, session_date)
    pending_todos = context.get("pending_todos", [])
    git_status_lines = git_summary.get("status_lines", [])
    branch = git_summary.get("branch") or "(não disponível)"
    security_clean = "🟢 LIMPO" if security_summary.get("clean") else "🔴 ATENÇÃO"
    docs_security_clean = (
        "🟢 PASSED" if session_docs_security.get("clean") else "🔴 ATENÇÃO"
    )

    report_body = (
        f"- Branch: {branch}\n"
        f"- Mudanças pendentes no Git: {len(git_status_lines)}\n"
        f"- Segurança do workspace: {security_clean}\n"
        f"- Segurança dos session docs: {docs_security_clean}\n"
        f"- DAILY_ACTIVITIES válido: {'✅' if daily_validation.get('valid') else '❌'}\n"
    )
    upsert_section(files.report, "Resumo automático", report_body)

    next_steps_body = _render_bullets(
        pending_todos,
        "Revisar docs/TODO.md e definir a próxima prioridade.",
    )
    upsert_section(files.final_status, "Próximas ações", next_steps_body)

    git_body = _render_bullets(
        git_status_lines[:10],
        "Nenhuma alteração pendente detectada no git status.",
    )
    upsert_section(files.final_status, "Estado do Git", git_body)

    security_body = (
        f"- Workspace: {security_clean}\n"
        f"- Session docs: {docs_security_clean}\n"
        f"- Findings workspace: {len(security_summary.get('findings', []))}\n"
        f"- Findings session docs: {len(session_docs_security.get('findings', []))}\n"
    )
    upsert_section(files.final_status, "Segurança", security_body)

    return {"updated": [str(files.report), str(files.final_status)]}
