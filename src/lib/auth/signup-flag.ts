// ============================================================
// Flag de signup público — NEXT_PUBLIC_SIGNUP_ENABLED.
//
// Padrão: desabilitado. O deploy self-hosted também bloqueia no
// backend via GOTRUE_DISABLE_SIGNUP (deploy/docker-compose.yml);
// esta flag apenas controla a UI (página /signup e link "criar
// conta" no /login). Mantenha as duas coerentes no .env.
//
// SERVER-ONLY na prática: o lookup abaixo é dinâmico de propósito
// (`const env = process.env`) para que o Next.js NÃO inline o valor
// no build — a imagem Docker é genérica e o valor vem do .env do
// compose em runtime. Referência: node_modules/next/dist/docs/
// 01-app/02-guides/environment-variables.md ("dynamic lookups will
// not be inlined"). Em bundle client `process.env` não existe em
// runtime, então componentes client devem receber o valor por prop
// de um server component (ver src/app/(auth)/login/page.tsx).
// ============================================================

/**
 * Indica se o cadastro público (signup aberto) está habilitado.
 * Avaliada em runtime no servidor — nunca inlinada no build.
 *
 * @returns `true` somente quando NEXT_PUBLIC_SIGNUP_ENABLED === "true".
 */
export function isSignupEnabled(): boolean {
  const env = process.env; // lookup dinâmico — evita inline no build
  return env.NEXT_PUBLIC_SIGNUP_ENABLED === "true";
}
