#!/usr/bin/env bash
# Criado em: 13/07/2026 16:18
# Modificado em: 13/07/2026 16:18
#
# Sincroniza a cópia deploy/migrations/ com a fonte canônica
# supabase/migrations/. A cópia existe porque o servidor recebe só a
# pasta deploy/ (symlink não sobrevive a todo método de sync).
#
# RODAR SEMPRE que criar/alterar uma migration, antes de commitar.
# Falha (exit 1) se detectar divergência ao usar --check (para CI).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "${SCRIPT_DIR}")"
REPO_ROOT="$(dirname "${DEPLOY_DIR}")"
FONTE="${REPO_ROOT}/supabase/migrations"
DESTINO="${DEPLOY_DIR}/migrations"

if [[ "${1:-}" == "--check" ]]; then
  if diff -rq "${FONTE}" "${DESTINO}" >/dev/null 2>&1; then
    echo "OK: deploy/migrations em sincronia com supabase/migrations."
    exit 0
  fi
  echo "ERRO: deploy/migrations divergente — rode scripts/sync-deploy-migrations.sh" >&2
  diff -rq "${FONTE}" "${DESTINO}" >&2 || true
  exit 1
fi

mkdir -p "${DESTINO}"
rsync -a --delete "${FONTE}/" "${DESTINO}/"
echo "Sincronizado: $(ls "${DESTINO}" | wc -l) migrations em deploy/migrations/."
