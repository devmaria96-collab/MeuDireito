import { URL_API } from "./api.ts";

export async function enviarSugestao(texto: string): Promise<void> {
  const resposta = await fetch(`${URL_API}/sugestoes`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ texto }),
  });
  if (resposta.ok || resposta.status === 204) {
    return;
  }
  const corpo = (await resposta.json().catch(() => null)) as { detail?: unknown } | null;
  if (corpo && typeof corpo.detail === "string" && corpo.detail.trim()) {
    throw new Error(corpo.detail);
  }
  throw new Error("Não foi possível enviar a sugestão.");
}
