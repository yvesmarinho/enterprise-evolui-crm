#!/usr/bin/env bash
# Criado em: 10/07/2026 12:40
# Modificado em: 13/07/2026 15:51
#
# Aplica as migrations do CRM (supabase/migrations/*.sql) no Postgres
# self-hosted, em ordem alfabética (001_, 002_, ...), via psql dentro
# do container supabase-db (usuário supabase_admin = superuser).
#
# Idempotência: registra cada migration aplicada na tabela
# public._migrations e pula as já executadas — rodar de novo é seguro.
#
# Uso (na pasta deploy/):
#   ./scripts/apply-migrations.sh [caminho/para/migrations]
# Sem argumento, procura em: <repo>/supabase/migrations,
# deploy/migrations e deploy/supabase/migrations.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "${SCRIPT_DIR}")"
REPO_ROOT="$(dirname "${DEPLOY_DIR}")"

# Localiza as migrations: 1º argumento > variável MIGRATIONS_DIR >
# locais conhecidos (repo completo ou cópia junto ao deploy/).
MIGRATIONS_DIR="${1:-${MIGRATIONS_DIR:-}}"
if [[ -z "${MIGRATIONS_DIR}" ]]; then
  for candidato in \
    "${REPO_ROOT}/supabase/migrations" \
    "${DEPLOY_DIR}/migrations" \
    "${DEPLOY_DIR}/supabase/migrations"; do
    if [[ -d "${candidato}" ]]; then
      MIGRATIONS_DIR="${candidato}"
      break
    fi
  done
fi
if [[ -z "${MIGRATIONS_DIR}" || ! -d "${MIGRATIONS_DIR}" ]]; then
  echo "ERRO: pasta de migrations não encontrada." >&2
  echo "No servidor sem o repositório completo, copie a pasta antes:" >&2
  echo "  scp -r supabase/migrations usuario@servidor:<caminho>/deploy/migrations" >&2
  echo "Ou informe o caminho: ./scripts/apply-migrations.sh /caminho/para/migrations" >&2
  exit 1
fi
echo "==> Usando migrations de: ${MIGRATIONS_DIR}"

# O init zz-align-role-passwords.sh define senha para supabase_admin e
# o socket local do container não é "trust" — o psql exige PGPASSWORD.
# Lê POSTGRES_PASSWORD do ambiente ou do deploy/.env.
if [[ -z "${POSTGRES_PASSWORD:-}" && -f "${DEPLOY_DIR}/.env" ]]; then
  POSTGRES_PASSWORD="$(sed -n 's/^POSTGRES_PASSWORD=//p' "${DEPLOY_DIR}/.env" | tail -1)"
fi
if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  echo "ERRO: POSTGRES_PASSWORD não definido (ambiente ou deploy/.env)." >&2
  exit 1
fi

# Em assignments bash não há word splitting — sem aspas é seguro; o
# `-e PGPASSWORD` (sem valor) repassa a variável do ambiente ao exec.
export PGPASSWORD=${POSTGRES_PASSWORD}

PSQL=(docker compose -f "${DEPLOY_DIR}/docker-compose.yml" exec -T \
  -e PGPASSWORD supabase-db \
  psql -U supabase_admin -d postgres -v ON_ERROR_STOP=1 --quiet)

echo "==> Criando tabela de controle (se não existir)"
"${PSQL[@]}" -c "CREATE TABLE IF NOT EXISTS public._migrations (
  name text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);"

aplicadas=0
puladas=0
for arquivo in "${MIGRATIONS_DIR}"/*.sql; do
  nome="$(basename "${arquivo}")"
  ja_existe="$("${PSQL[@]}" -tAc \
    "SELECT 1 FROM public._migrations WHERE name = '${nome}'")"
  if [[ "${ja_existe}" == "1" ]]; then
    puladas=$((puladas + 1))
    continue
  fi
  echo "==> Aplicando ${nome}"
  "${PSQL[@]}" -f - < "${arquivo}"
  "${PSQL[@]}" -c "INSERT INTO public._migrations (name) VALUES ('${nome}');"
  aplicadas=$((aplicadas + 1))
done

echo "==> Concluído: ${aplicadas} aplicadas, ${puladas} já existentes"

# Backfill de profiles/contas: usuários criados ANTES das migrations
# (ex.: admin-bootstrap no primeiro `up`, quando o trigger
# handle_new_user ainda não existia) ficam sem profile/conta — e sem
# eles o usuário não tem papel algum no CRM. Replica a lógica do
# trigger (conta própria + profile com account_role = 'owner', o papel
# máximo). Idempotente: só cria para quem não tem profile.
echo "==> Backfill de profiles/contas para usuários sem profile"
"${PSQL[@]}" <<'SQL'
DO $$
DECLARE
  r RECORD;
  v_account UUID;
  v_total INT := 0;
BEGIN
  FOR r IN
    SELECT u.id, u.email,
           COALESCE(u.raw_user_meta_data->>'full_name', '') AS full_name
    FROM auth.users u
    WHERE NOT EXISTS (
      SELECT 1 FROM public.profiles p WHERE p.user_id = u.id
    )
  LOOP
    INSERT INTO public.accounts (name, owner_user_id)
    VALUES (COALESCE(NULLIF(r.full_name, ''), r.email, 'My account'), r.id)
    RETURNING id INTO v_account;

    INSERT INTO public.profiles (user_id, full_name, email, account_id, account_role)
    VALUES (r.id, r.full_name, r.email, v_account, 'owner');

    v_total := v_total + 1;
    RAISE NOTICE 'profile/conta criados para % (owner)', r.email;
  END LOOP;
  RAISE NOTICE 'backfill: % usuário(s) corrigido(s)', v_total;
END $$;
SQL

echo "==> Verificação rápida:"
"${PSQL[@]}" -c "SELECT count(*) AS tabelas FROM information_schema.tables
  WHERE table_schema = 'public';"
"${PSQL[@]}" -c "SELECT p.email, p.account_role FROM public.profiles p ORDER BY p.created_at LIMIT 10;"
