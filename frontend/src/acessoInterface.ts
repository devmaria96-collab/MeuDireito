/** Decisão da interface de homologação. A senha não fica neste arquivo. */

export const COOKIE_INTERFACE = "md_acesso_interface";
const MENSAGEM = "md-acesso-homologacao-v1";

export async function tokenDeAcesso(segredo: string): Promise<string> {
  const chave = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(segredo),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const assinatura = await crypto.subtle.sign("HMAC", chave, new TextEncoder().encode(MENSAGEM));
  return [...new Uint8Array(assinatura)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function cookieConfere(cabecalho: string | null, token: string): boolean {
  if (!cabecalho || !token) {
    return false;
  }
  const prefixo = `${COOKIE_INTERFACE}=`;
  const encontrado = cabecalho
    .split(";")
    .map((parte) => parte.trim())
    .find((parte) => parte.startsWith(prefixo));
  if (!encontrado) {
    return false;
  }
  const valor = encontrado.slice(prefixo.length);
  if (valor.length !== token.length) {
    return false;
  }
  let diferenca = 0;
  for (let indice = 0; indice < valor.length; indice += 1) {
    diferenca |= valor.charCodeAt(indice) ^ token.charCodeAt(indice);
  }
  return diferenca === 0;
}

export function origemApiValida(valor: string | undefined): string {
  const texto = (valor || "").trim().replace(/\/$/, "");
  if (!/^https:\/\/[A-Za-z0-9.-]+(?::\d+)?$/.test(texto)) {
    return "";
  }
  return texto;
}

export function paginaDeAcesso(urlApi: string): string {
  const api = origemApiValida(urlApi);
  const destino = api ? `${api}/acesso/homologacao` : "";
  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex">
  <title>Acesso de homologação — Meu Direito</title>
  <style>
    body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #000; color: #fff; font-family: sans-serif; }
    form { width: min(100% - 2rem, 24rem); }
    h1 { font-size: 1.4rem; }
    p { line-height: 1.5; }
    input, button { width: 100%; min-height: 2.75rem; border-radius: 999px; font: inherit; }
    input { margin: 1rem 0; padding: 0 1rem; border: 1px solid rgba(255,255,255,.2); background: #000; color: #fff; }
    button { border: 0; background: #9f1239; color: #fff; }
    [role="alert"] { color: #fff; }
  </style>
</head>
<body>
  <form id="acesso">
    <h1>Acesso de homologação</h1>
    <p>Esta instalação de teste não fica aberta. A senha abaixo não é a senha de uma conta do Meu Direito.</p>
    <label for="senha">Senha de acesso</label>
    <input id="senha" name="senha" type="password" autocomplete="current-password" required minlength="16" maxlength="128">
    <button type="submit">Entrar na homologação</button>
    <p id="aviso" role="alert"></p>
  </form>
  <script>
    document.getElementById("acesso").addEventListener("submit", async (evento) => {
      evento.preventDefault();
      const aviso = document.getElementById("aviso");
      const senha = new FormData(evento.currentTarget).get("senha");
      aviso.textContent = "";
      const respostaInterface = await fetch("/acesso-interface", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ senha })
      });
      if (!respostaInterface.ok) {
        aviso.textContent = respostaInterface.status === 401
          ? "A senha de acesso da homologação está incorreta."
          : "O acesso da interface não está configurado.";
        return;
      }
      const destino = ${JSON.stringify(destino)};
      if (destino) {
        const api = await fetch(destino, {
          method: "POST",
          credentials: "include",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ senha })
        });
        if (!api.ok) {
          aviso.textContent = "A interface foi liberada, mas a API recusou o acesso. Abra o endereço e tente de novo.";
          return;
        }
      }
      location.replace("/");
    });
  </script>
</body>
</html>`;
}
