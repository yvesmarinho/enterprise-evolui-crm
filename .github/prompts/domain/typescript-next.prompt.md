---
mode: agent
description: "Layer 2 Profile — Next.js TypeScript. Ative declarando 'Modo: NEXT. Projeto: [nome].'"
---

# ⬛ Layer 2 Profile — TypeScript Next.js

> **Como ativar**: no início da sessão declare:
> ```
> Modo: NEXT. Projeto: [nome]. Stack: Next.js 15 + TypeScript strict + Jest.
> ```
> Este perfil complementa `devops-programming.prompt.md` — ambos devem estar ativos.

---

## 🎯 Contexto do Perfil

Você está no modo **Next.js TypeScript**. O trabalho envolve construir aplicações web com Next.js usando App Router, priorizando:
- **TypeScript strict**: sem `any` implícito, sem `ts-ignore` sem justificativa
- **App Router** (`app/`): Server Components por padrão, Client Components apenas quando necessário
- **Server Actions** para mutações de dados (evitar API Routes desnecessárias)
- **Testabilidade**: Jest + React Testing Library para componentes, `vitest` para lógica pura

---

## 📋 O que o Copilot precisa saber neste modo

| Informação | Exemplos | Obrigatório? |
|------------|----------|-------------|
| **Versão Next.js** | `>=15` | ✅ |
| **Versão Node.js** | `>=20 LTS` | ✅ |
| **Package manager** | `pnpm` (recomendado), `npm`, `yarn` | ✅ |
| **Auth** | NextAuth.js v5, Auth.js, Clerk, nenhuma | ✅ |
| **Banco de dados** | Prisma + PostgreSQL, Drizzle + SQLite, sem banco | ✅ |
| **CSS** | Tailwind CSS, CSS Modules, styled-components | ✅ |
| **Deploy alvo** | Vercel, Docker (self-hosted), AWS Amplify | Recomendado |
| **Testes E2E** | Playwright, Cypress, nenhum | Opcional |

---

## 🏗️ Estrutura de Pastas Padrão (App Router)

```
{project_name}/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Home page (Server Component)
│   ├── globals.css
│   └── api/
│       └── health/
│           └── route.ts        # GET /api/health
├── components/                 # Componentes React reutilizáveis
│   ├── ui/                     # Primitivos (Button, Input, etc.)
│   └── shared/                 # Compostos e layouts
├── lib/                        # Utilitários e helpers (puro TS, sem JSX)
│   └── utils.ts
├── types/                      # Tipos TypeScript globais
│   └── index.d.ts
├── public/                     # Assets estáticos
├── tests/
│   ├── unit/                   # Jest: lógica pura
│   └── integration/            # Jest + React Testing Library: componentes
├── .env.example
├── next.config.ts
├── tsconfig.json               # strict mode
├── package.json
├── .eslintrc.json
├── prettier.config.ts
├── jest.config.ts
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── docs/
```

---

## 🔧 Convenções Next.js Obrigatórias

### Server vs. Client Components

```tsx
// Server Component (padrão — sem "use client")
// app/page.tsx
export default async function HomePage() {
  const data = await fetch("https://api.example.com/data").then(r => r.json())
  return <main>{JSON.stringify(data)}</main>
}

// Client Component (apenas quando necessário: hooks, eventos, browser APIs)
// components/ui/Counter.tsx
"use client"
import { useState } from "react"

export function Counter() {
  const [count, setCount] = useState(0)
  return <button onClick={() => setCount(c => c + 1)}>{count}</button>
}
```

### API Routes (App Router)

```ts
// app/api/health/route.ts
import { NextResponse } from "next/server"

export async function GET() {
  return NextResponse.json({ status: "ok" })
}
```

### Variáveis de ambiente tipadas

```ts
// lib/env.ts — validar com zod no startup
import { z } from "zod"

const envSchema = z.object({
  NODE_ENV: z.enum(["development", "production", "test"]),
  DATABASE_URL: z.string().url().optional(),
  // NEXT_PUBLIC_* são expostas ao browser
  NEXT_PUBLIC_APP_URL: z.string().url().default("http://localhost:3000"),
})

export const env = envSchema.parse(process.env)
```

### TypeScript strict — regras

- `"strict": true` em `tsconfig.json` — nunca desabilitar
- Proibido: `any`, `@ts-ignore`, `as unknown as T` sem comentário explicativo
- Prefer `satisfies` operator sobre type assertions quando possível
- Tipos de retorno explícitos em funções exportadas

---

## 🧪 Padrão de Testes

### jest.config.ts

```ts
import type { Config } from "jest"
import nextJest from "next/jest.js"

const createJestConfig = nextJest({ dir: "./" })

const config: Config = {
  coverageProvider: "v8",
  testEnvironment: "jsdom",
  setupFilesAfterEach: ["<rootDir>/tests/setup.ts"],
  collectCoverageFrom: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.ts"],
}

export default createJestConfig(config)
```

### Smoke test API route

```ts
// tests/unit/health.test.ts
import { GET } from "@/app/api/health/route"

describe("GET /api/health", () => {
  it("returns 200 with status ok", async () => {
    const response = await GET()
    const body = await response.json()
    expect(response.status).toBe(200)
    expect(body).toEqual({ status: "ok" })
  })
})
```

### Regras de teste
- Cobertura mínima: 80% — `jest --coverage`
- Componentes: testar comportamento (o que o usuário vê), não implementação
- Mocks de `fetch`: `jest.spyOn(global, "fetch")` ou `msw`
- Sem snapshot tests de componentes (frágil) — preferir assertions semânticas

---

## 🔐 Segurança

- [ ] Variáveis de ambiente: validar com `zod` no startup — crash rápido se inválidas
- [ ] `NEXT_PUBLIC_*`: nunca colocar segredos — são expostas ao browser
- [ ] Headers de segurança em `next.config.ts`: CSP, HSTS, X-Frame-Options
- [ ] Sanitização de input: `DOMPurify` para conteúdo HTML, nunca `dangerouslySetInnerHTML` sem sanitizar
- [ ] CSRF: Next.js App Router com Server Actions mitiga automaticamente via `SameSite` cookie
- [ ] Dependências: `pnpm audit` no CI
- [ ] Rate limiting em API Routes: `@upstash/ratelimit` ou middleware customizado

### next.config.ts — headers de segurança

```ts
const securityHeaders = [
  { key: "X-DNS-Prefetch-Control", value: "on" },
  { key: "X-Frame-Options", value: "SAMEORIGIN" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
]
```

---

## 🚀 Quick-start

```bash
git clone <repo>
cd {project_name}
pnpm install               # instala deps
cp .env.example .env.local # preencher vars obrigatórias
make dev                   # pnpm dev
```

---

## 📦 Dependências Padrão

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "typescript": "^5.5.0",
    "@types/react": "^19.0.0",
    "@types/node": "^22.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.0.0",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "prettier": "^3.3.0",
    "jest": "^29.0.0",
    "jest-environment-jsdom": "^29.0.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.0"
  }
}
```

---

## 🔗 Referências

- [Perfil base](devops-programming.prompt.md) — regras genéricas de programação
- [Segurança](devops-security.prompt.md) — controles transversais
- [Profile Descriptor](../../profile-descriptors/typescript-next.yaml)
- Next.js docs: https://nextjs.org/docs
