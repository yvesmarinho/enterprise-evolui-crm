<!-- Criado em: 13/07/2026 11:17 -->
<!-- Modificado em: 13/07/2026 15:51 -->

# Atividades — 13/07/2026

## Admin padrão no boot, SMTP no-reply e flag de signup

- **Horário/Status**: 11:00–11:20 — concluído (aguardando PR).
- **Objetivo**: (1) criar usuário admin padrão no início do stack; (2) configurar envio de e-mail via SMTP com conta no-reply; (3) variável de ambiente para desativar a auto-criação de usuários (signup público).
- **Contexto**: auth é Supabase/GoTrue self-hosted (`deploy/docker-compose.yml`). O admin era criado manualmente por `scripts/create_admin_user.py`; `GOTRUE_DISABLE_SIGNUP` e `GOTRUE_MAILER_AUTOCONFIRM` estavam hard-coded; nenhum SMTP configurado; a página `/signup` continuava visível mesmo com signup bloqueado no backend.
- **Passos/Resultado**:
  - Novo serviço one-shot `admin-bootstrap` no compose (imagem `curlimages/curl`, rede interna) executando `deploy/scripts/bootstrap-admin.sh`: espera o `/health` do GoTrue, cria o usuário via Admin API (`POST /admin/users`, ignora o bloqueio de signup); idempotente (HTTP 422 = já existe); desativado se `ADMIN_EMAIL`/`ADMIN_PASSWORD` vazios; token e senha nunca em argv (arquivos temporários).
  - SMTP no GoTrue: `GOTRUE_SMTP_HOST/PORT/USER/PASS/ADMIN_EMAIL/SENDER_NAME` vindos de `SMTP_*` do `.env`; `GOTRUE_MAILER_AUTOCONFIRM` agora configurável (padrão `true` enquanto não houver SMTP). Somente envio — sem IMAP (decisão do usuário).
  - Signup público: `GOTRUE_DISABLE_SIGNUP: ${DISABLE_SIGNUP:-true}` (backend) + `NEXT_PUBLIC_SIGNUP_ENABLED` (frontend, padrão `false`): middleware redireciona `/signup` → `/login` (exceto com `?invite=`), link "criar conta" oculto no `/login`; placeholder novo no `Dockerfile` + substituição no `docker-entrypoint.sh`.
- **Decisões**: bootstrap como serviço one-shot no compose (escolha do usuário) em vez de etapa no entrypoint do app; signup desabilitado por padrão; e-mail apenas via GoTrue (nenhum mailer no app Next.js).
- **Arquivos modificados**: `deploy/docker-compose.yml`, `deploy/env.example`, `deploy/Dockerfile`, `deploy/docker-entrypoint.sh`, `deploy/scripts/bootstrap-admin.sh` (novo), `src/middleware.ts`, `src/app/(auth)/login/page.tsx`, `src/lib/auth/signup-flag.ts` (novo), `.env.local.example`.
- **Verificação**: `docker compose --env-file env.example config` OK; `sh -n` nos scripts OK; `npm run lint` sem erros novos (26 pré-existentes na main); `tsc --noEmit` limpo.
- **Commits**: branch `359-admin-bootstrap-smtp-signup-flag` — PR https://github.com/yvesmarinho/enterprise-evolui-crm/pull/1.

## Teste local do stack de deploy

- **Horário/Status**: 11:30–11:50 — concluído.
- **Objetivo**: validar em máquina local o stack do deploy (Postgres + GoTrue + admin-bootstrap + storage) com segredos descartáveis.
- **Passos/Resultado** (projeto compose isolado `evolui-test`, dados em scratchpad, tudo removido ao final):
  - `admin-bootstrap` criou o admin no 1º boot (HTTP 200) e foi idempotente na reexecução (HTTP 422 "já existe").
  - Signup público recusado pelo GoTrue: `{"error_code":"signup_disabled"}` — `DISABLE_SIGNUP=true` funcionando.
  - Variáveis `GOTRUE_SMTP_*` corretamente injetadas no container do GoTrue a partir de `SMTP_*`.
  - 35 migrations aplicadas (37 tabelas); trigger `handle_new_user` criou profile + conta `owner` para usuário novo criado pelo bootstrap; login via password grant HTTP 200.
- **Bug encontrado e corrigido**: `deploy/scripts/apply-migrations.sh` falhava com "no password supplied" — o init `zz-align-role-passwords.sh` define senha para `supabase_admin` e o socket local do container exige autenticação. Fix: o script agora injeta `PGPASSWORD` (do ambiente ou de `deploy/.env`) no `docker compose exec`.
- **Observação operacional**: aplicar as migrations **antes** de definir `ADMIN_EMAIL` (ou recriar o admin depois) para que o trigger crie profile/conta; a migration 008 exige o serviço `supabase-storage` já iniciado (ele migra o schema `storage`).
- **Arquivos modificados**: `deploy/scripts/apply-migrations.sh`.

## Build da imagem e correção da flag de signup (runtime)

- **Horário/Status**: 11:50–11:58 — concluído (push ao Docker Hub pendente de autorização).
- **Contexto**: no build de teste da imagem 0.0.3 descobriu-se que a abordagem placeholder+sed para `NEXT_PUBLIC_SIGNUP_ENABLED` não funciona: o Next inlina a variável no build e o minificador dobra `"PLACEHOLDER" === "true"` para `false`, eliminando o placeholder do bundle — a flag ficava travada em "desabilitado".
- **Correção** (conforme doc local do Next, environment-variables.md — "dynamic lookups will not be inlined"):
  - `src/lib/auth/signup-flag.ts` usa lookup dinâmico (`const env = process.env`) — avaliado em runtime no servidor.
  - `/login` virou server component fino (`page.tsx`, `force-dynamic`) que injeta `signupEnabled` por prop no novo `login-client.tsx`.
  - Placeholder de signup removido do `deploy/Dockerfile` e do `docker-entrypoint.sh` (que só normaliza a env agora).
  - Bug adicional: `build-push.sh` publicava `enterprise-evoli-crm` (typo) enquanto o compose consome `enterprise-evolui-crm` — nomes unificados.
- **Validação na imagem 0.0.3 (local)**: flag `false` → `/signup` 307 para `/login` e link ausente; flag `true` → `/signup` 200 e link presente. `tsc --noEmit` limpo; lint sem erros novos.
- **Arquivos modificados**: `src/lib/auth/signup-flag.ts`, `src/middleware.ts`, `src/app/(auth)/login/page.tsx` (novo), `src/app/(auth)/login/login-client.tsx` (renomeado), `deploy/Dockerfile`, `deploy/docker-entrypoint.sh`, `deploy/scripts/build-push.sh`.

## Fix crash-loop do Realtime + revisão do papel do admin

- **Horário/Status**: 15:20–15:51 — concluído.
- **Contexto**: no deploy do wfdb01 o supabase-db logava em loop `no schema has been selected to create in` e o admin aparecia como usuário comum.
- **Fix 1 — schema _realtime**: o supabase-realtime conecta com `SET search_path TO _realtime`, schema que o compose oficial cria via `realtime.sql` e o nosso não criava. Novo init `deploy/supabase/init/zz-realtime-schema.sh` (primeiro boot) cria `_realtime` e `realtime`. Validado local: zero erros.
- **Revisão do papel do admin**: não existe papel global no CRM — papéis são por conta (`owner` > `admin` > `agent` > `viewer`); o bootstrap já produz `owner` (máximo). Dois problemas reais encontrados:
  1. Admin criado ANTES das migrations (ordem do primeiro `up`) fica sem profile/conta → backfill idempotente adicionado ao `apply-migrations.sh` (cria conta + profile `owner` para usuários de `auth.users` sem profile). Validado reproduzindo o cenário: admin terminou `owner`.
  2. A tela de perfil exibia a coluna legada `profiles.role` (default `'user'`) em vez do papel real → agora exibe `account_role` com fallback.
- **Arquivos modificados**: `deploy/supabase/init/zz-realtime-schema.sh` (novo), `deploy/docker-compose.yml`, `deploy/scripts/apply-migrations.sh`, `src/components/settings/profile-form.tsx`.
