import { isSignupEnabled } from "@/lib/auth/signup-flag";

import LoginPageClient from "./login-client";

// A flag precisa ser avaliada a cada request (env de runtime do
// container) — sem isto o valor seria congelado no prerender do build
// e a imagem Docker genérica não conseguiria alterá-lo.
export const dynamic = "force-dynamic";

/**
 * Página de login — server component fino que lê a flag de signup em
 * runtime e delega a UI ao componente client.
 */
export default function LoginPage() {
  return <LoginPageClient signupEnabled={isSignupEnabled()} />;
}
