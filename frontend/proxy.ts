import { next } from "@vercel/functions";
import { COOKIE_INTERFACE, cookieConfere, paginaDeAcesso, tokenDeAcesso } from "./src/acessoInterface.ts";

function ambienteDeHomologacao(): boolean {
  return (process.env.AMBIENTE || "").trim().toLowerCase() === "homologacao";
}

export default async function proxy(pedido: Request): Promise<Response> {
  if (!ambienteDeHomologacao()) {
    return next();
  }
  const segredo = (process.env.ACESSO_HOMOLOGACAO || "").trim();
  const url = new URL(pedido.url);
  if (url.pathname === "/acesso-interface" && pedido.method === "POST") {
    return responderAcesso(pedido, segredo);
  }
  if (segredo.length < 16) {
    return new Response("O acesso da interface de homologação não está configurado.", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
  const token = await tokenDeAcesso(segredo);
  if (cookieConfere(pedido.headers.get("cookie"), token)) {
    return next();
  }
  return new Response(paginaDeAcesso(process.env.URL_API_HOMOLOGACAO || ""), {
    status: 401,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-robots-tag": "noindex",
    },
  });
}

async function responderAcesso(pedido: Request, segredo: string): Promise<Response> {
  if (segredo.length < 16) {
    return new Response("incompleto", { status: 503, headers: { "cache-control": "no-store" } });
  }
  const corpo = (await pedido.json().catch(() => null)) as { senha?: unknown } | null;
  const senha = corpo && typeof corpo.senha === "string" ? corpo.senha : "";
  if (senha.length < 16 || senha.length > 128) {
    return new Response("recusado", { status: 401, headers: { "cache-control": "no-store" } });
  }
  const informado = await tokenDeAcesso(senha);
  const esperado = await tokenDeAcesso(segredo);
  if (!cookieConfere(`${COOKIE_INTERFACE}=${informado}`, esperado)) {
    return new Response("recusado", { status: 401, headers: { "cache-control": "no-store" } });
  }
  return new Response("ok", {
    status: 204,
    headers: {
      "cache-control": "no-store",
      "set-cookie": `${COOKIE_INTERFACE}=${esperado}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=43200`,
    },
  });
}
