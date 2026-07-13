#!/usr/bin/env bash
# Criado em: 13/07/2026 15:31
# Modificado em: 13/07/2026 15:31
#
# Executado pelo entrypoint do Postgres no PRIMEIRO boot (data dir
# vazio), via /docker-entrypoint-initdb.d/. Cria o schema _realtime,
# exigido pelo supabase-realtime (DB_AFTER_CONNECT_QUERY faz
# SET search_path TO _realtime) — sem ele o serviço entra em
# crash-loop com "no schema has been selected to create in".
# Equivale ao realtime.sql do compose oficial de self-hosting.

set -euo pipefail

echo "[init] criando schema _realtime para o supabase-realtime..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<-SQL
	CREATE SCHEMA IF NOT EXISTS _realtime AUTHORIZATION supabase_admin;
	CREATE SCHEMA IF NOT EXISTS realtime AUTHORIZATION supabase_admin;
SQL
echo "[init] schema _realtime criado."
