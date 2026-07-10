"""
lib/session_security.py — Scans de segurança do workflow de sessão.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .session_context import SessionPaths

SENSITIVE_FILE_PATTERNS = (
    "*.env",
    ".env*",
    "*.key",
    "*.pem",
    "*.crt",
    "*.p12",
    "*secret*",
    "*password*",
    "*token*",
    "*credentials*",
    "*.log",
)
EXCLUDED_DIR_NAMES = {
    ".git",
    ".secrets",
    ".venv",
    "__pycache__",
    "node_modules",
    "htmlcov",
    ".pytest_cache",
}
ENV_PLACEHOLDER_RE = re.compile(
    r"^(<.*>|.*example.*|.*changeme.*|.*placeholder.*|.*dummy.*|.*redacted.*|\*{3,})$",
    re.IGNORECASE,
)
SESSION_DOC_PATTERNS = {
    "github_token": re.compile(r"ghp_[0-9A-Za-z]{36}"),
    "github_pat": re.compile(r"github_pat_[0-9A-Za-z_]{82}"),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private_ip_10": re.compile(r"(?<!\.)10\.(\d{1,3}\.){2}\d{1,3}(?!\.)"),
    "private_ip_172": re.compile(
        r"(?<!\.)172\.(1[6-9]|2[0-9]|3[01])\.(\d{1,3}\.)\d{1,3}(?!\.)",
    ),
    "private_ip_192": re.compile(r"(?<!\.)192\.168\.(\d{1,3}\.)\d{1,3}(?!\.)"),
    "bearer": re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
}
SESSION_DOC_ALLOWLIST = (
    re.compile(r"<(TOKEN|API_KEY|SECRET|REDACTED|PRIVATE_IP)>"),
    re.compile(r"192\.0\.2\.\d+"),
    re.compile(r"198\.51\.100\.\d+"),
    re.compile(r"203\.0\.113\.\d+"),
)


@dataclass(frozen=True)
class SecurityFinding:
    """Achado do scan de segurança."""

    kind: str
    path: str
    detail: str
    severity: str = "warning"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _should_skip_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def _matches_sensitive_pattern(path: Path) -> bool:
    return any(
        fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(str(path), pattern)
        for pattern in SENSITIVE_FILE_PATTERNS
    )


def _env_value_looks_safe(value: str) -> bool:
    stripped = value.strip().strip("'\"")
    if not stripped:
        return True
    return bool(ENV_PLACEHOLDER_RE.match(stripped))


def _check_env_examples(paths: SessionPaths) -> list[SecurityFinding]:
    findings: list[SecurityFinding] = []
    for env_file in paths.root.rglob(".env.example"):
        if _should_skip_path(env_file.relative_to(paths.root)):
            continue
        for line_number, line in enumerate(
            env_file.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            _, value = stripped.split("=", 1)
            if _env_value_looks_safe(value):
                continue
            findings.append(
                SecurityFinding(
                    kind="env-example-value",
                    path=str(env_file.relative_to(paths.root)),
                    detail=f"Linha {line_number} contém valor real ou ambíguo",
                    severity="high",
                ),
            )
    return findings


def scan_workspace(paths: SessionPaths) -> dict[str, Any]:
    """Executa scan leve por nomes de arquivos sensíveis e .env.example."""

    findings: list[SecurityFinding] = []

    for file_path in paths.root.rglob("*"):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(paths.root)
        if _should_skip_path(relative_path):
            continue
        if file_path.name == ".env.example":
            continue
        if _matches_sensitive_pattern(relative_path):
            findings.append(
                SecurityFinding(
                    kind="sensitive-file",
                    path=str(relative_path),
                    detail="Arquivo sensível fora de .secrets/",
                    severity="high",
                ),
            )

    findings.extend(_check_env_examples(paths))
    gitignore_has_secrets = (
        paths.gitignore_file.exists()
        and ".secrets/" in paths.gitignore_file.read_text(encoding="utf-8")
    )
    if not gitignore_has_secrets:
        findings.append(
            SecurityFinding(
                kind="gitignore",
                path=str(paths.gitignore_file.relative_to(paths.root))
                if paths.gitignore_file.exists()
                else ".gitignore",
                detail=".secrets/ ausente no .gitignore",
                severity="high",
            ),
        )

    return {
        "clean": not findings,
        "gitignore_has_secrets": gitignore_has_secrets,
        "findings": [item.to_dict() for item in findings],
    }


def scan_session_documents(paths: SessionPaths) -> dict[str, Any]:
    """Varre docs/SESSIONS em busca de padrões sensíveis comuns."""

    findings: list[SecurityFinding] = []
    if not paths.sessions_dir.exists():
        return {"clean": True, "findings": []}

    for markdown_file in sorted(paths.sessions_dir.glob("*/*.md")):
        relative_path = markdown_file.relative_to(paths.root)
        content = markdown_file.read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if any(pattern.search(line) for pattern in SESSION_DOC_ALLOWLIST):
                continue
            for pattern_name, pattern in SESSION_DOC_PATTERNS.items():
                match = pattern.search(line)
                if not match:
                    continue
                findings.append(
                    SecurityFinding(
                        kind=f"session-doc-{pattern_name}",
                        path=str(relative_path),
                        detail=f"Linha {line_number}: {match.group(0)[:60]}",
                        severity="high",
                    ),
                )

    return {
        "clean": not findings,
        "findings": [item.to_dict() for item in findings],
    }
