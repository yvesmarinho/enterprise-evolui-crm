"""
lib/git_session.py — Operações Git para o workflow de sessão.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


def _run_git(
    root: Path,
    *args: str,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=check,
    )


@dataclass(frozen=True)
class GitState:
    """Resumo do estado atual do repositório."""

    is_repo: bool
    branch: str | None
    status_lines: tuple[str, ...]
    recent_commits: tuple[str, ...]
    upstream_summary: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_git_state(root: Path | str) -> GitState:
    """Coleta estado do git sem modificar o repositório."""

    root_path = Path(root).resolve()
    try:
        inside = _run_git(root_path, "rev-parse", "--is-inside-work-tree", check=True)
    except FileNotFoundError:
        return GitState(
            is_repo=False,
            branch=None,
            status_lines=(),
            recent_commits=(),
            upstream_summary=None,
            error="git não encontrado no PATH",
        )
    except subprocess.CalledProcessError:
        return GitState(
            is_repo=False,
            branch=None,
            status_lines=(),
            recent_commits=(),
            upstream_summary=None,
            error=None,
        )

    if inside.stdout.strip() != "true":
        return GitState(
            is_repo=False,
            branch=None,
            status_lines=(),
            recent_commits=(),
            upstream_summary=None,
            error=None,
        )

    branch_result = _run_git(root_path, "branch", "--show-current")
    status_result = _run_git(root_path, "status", "--short")
    status_short_result = _run_git(root_path, "status", "-sb")
    log_result = _run_git(root_path, "log", "--oneline", "-5")

    upstream_summary = None
    short_lines = status_short_result.stdout.splitlines()
    if short_lines:
        upstream_summary = short_lines[0]

    return GitState(
        is_repo=True,
        branch=branch_result.stdout.strip() or None,
        status_lines=tuple(line for line in status_result.stdout.splitlines() if line),
        recent_commits=tuple(line for line in log_result.stdout.splitlines() if line),
        upstream_summary=upstream_summary,
    )


def commit_all(
    root: Path | str,
    *,
    title: str,
    body_lines: list[str],
) -> dict[str, Any]:
    """Cria commit usando arquivo de mensagem temporário."""

    root_path = Path(root).resolve()
    git_state = collect_git_state(root_path)
    if not git_state.is_repo:
        return {"ok": False, "status": "skipped", "reason": "não é repositório git"}

    _run_git(root_path, "add", "-A", check=True)
    message = title.strip() + "\n\n" + "\n".join(line.rstrip() for line in body_lines) + "\n"

    message_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="session-manager-",
            suffix=".txt",
            delete=False,
        ) as handle:
            handle.write(message)
            message_path = handle.name

        result = _run_git(root_path, "commit", "-F", message_path)
    finally:
        if message_path is not None:
            Path(message_path).unlink(missing_ok=True)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "nothing to commit" in stderr:
            return {"ok": True, "status": "skipped", "reason": "nada para commitar"}
        return {"ok": False, "status": "error", "reason": stderr}

    return {"ok": True, "status": "created", "stdout": result.stdout.strip()}


def push_current_branch(root: Path | str) -> dict[str, Any]:
    """Executa git push origin <branch> na branch atual."""

    root_path = Path(root).resolve()
    git_state = collect_git_state(root_path)
    if not git_state.is_repo or not git_state.branch:
        return {
            "ok": False,
            "status": "skipped",
            "reason": "branch atual indisponível",
        }

    result = _run_git(root_path, "push", "origin", git_state.branch)
    if result.returncode != 0:
        return {"ok": False, "status": "error", "reason": result.stderr.strip()}

    return {"ok": True, "status": "pushed", "stdout": result.stdout.strip()}
