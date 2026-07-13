#!/usr/bin/env bash
# Criado em: 13/07/2026 16:05
# Modificado em: 13/07/2026 16:05
#
# Executado DENTRO do container one-shot db-migrations (imagem
# supabase/postgres) a cada `docker compose up`. Aplica as migrations
# do CRM montadas em /migrations no Postgres do serviço supabase-db.
#
# Ordem garantida pelo compose: supabase-db healthy e supabase-storage
# iniciado antes deste serviço; app e admin-bootstrap só sobem depois
# deste serviço terminar com sucesso (service_completed_successfully).
#
# Idempotência: controle na tabela public._migrations (mesma usada
# pelo apply-migrations.sh manual — os dois caminhos são equivalentes).
# Inclui o backfill de profiles/contas para usuários criados sem o
# trigger handle_new_user (ex.: admin de deploys antigos).

set -euo pipefail

: "${PGPASSWORD:?PGPASSWORD não definido (POSTGRES_PASSWORD no .env)}"
export PGPASSWORD

PSQL=(psql -h supabase-db -U supabase_admin -d postgres -v ON_ERROR_STOP=1 --quiet)

echo "[migrate-db] aguardando Postgres aceitar conexões..."
for _ in $(seq 1 60); do
  if "${PSQL[@]}" -tAc "SELECT 1" >/dev/null 2>&1; then break; fi
  sleep 2
done
"${PSQL[@]}" -tAc "SELECT 1" >/dev/null

# A migration 008 usa colunas de storage.buckets criadas pelas
# migrations internas do supabase-storage — espera até elas existirem.
echo "[migrate-db] aguardando migrations internas do storage-api..."
storage_ok=0
for _ in $(seq 1 60); do
  ok="$("${PSQL[@]}" -tAc "SELECT 1 FROM information_schema.columns
    WHERE table_schema='storage' AND table_name='buckets'
      AND column_name='public'" || true)"
  if [[ "${ok}" == "1" ]]; then storage_ok=1; break; fi
  sleep 2
done
if [[ "${storage_ok}" != "1" ]]; then
  echo "[migrate-db] ERRO: storage-api não migrou o schema storage em 120s." >&2
  exit 1
fi

shopt -s nullglob
arquivos=(/migrations/*.sql)
if [[ ${#arquivos[@]} -eq 0 ]]; then
  echo "[migrate-db] ERRO: nenhuma migration em /migrations — verifique o volume MIGRATIONS_DIR." >&2
  exit 1
fi

"${PSQL[@]}" -c "CREATE TABLE IF NOT EXISTS public._migrations (
  name text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);"

aplicadas=0
puladas=0
for arquivo in "${arquivos[@]}"; do
  nome="$(basename "${arquivo}")"
  ja_existe="$("${PSQL[@]}" -tAc \
    "SELECT 1 FROM public._migrations WHERE name = '${nome}'")"
  if [[ "${ja_existe}" == "1" ]]; then
    puladas=$((puladas + 1))
    continue
  fi
  echo "[migrate-db] aplicando ${nome}"
  "${PSQL[@]}" -f "${arquivo}"
  "${PSQL[@]}" -c "INSERT INTO public._migrations (name) VALUES ('${nome}');"
  aplicadas=$((aplicadas + 1))
done
echo "[migrate-db] migrations: ${aplicadas} aplicadas, ${puladas} já existentes."

# Backfill: usuários de auth.users sem profile (criados antes do
# trigger handle_new_user existir) ganham conta própria + profile
# com account_role 'owner'. Idempotente.
echo "[migrate-db] backfill de profiles/contas..."
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

echo "[migrate-db] concluído com sucesso."
