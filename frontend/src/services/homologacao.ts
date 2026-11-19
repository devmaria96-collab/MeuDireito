import { URL_API } from "./api.ts";

export interface EstadoAcesso {
  exigido: boolean;
  liberado: boolean;
  configurado: boolean;
  ambiente: string;
}

export function interpretarAcesso(status: number, corpo: unknown): EstadoAcesso {
  if (status === 404) {
    return { exigido: false, liberado: true, configurado: true, ambiente: "desenvolvimento" };
  }
  const dados = corpo && typeof corpo === "object" ? (corpo as Partial<EstadoAcesso>) : {};
  return {
    exigido: dados.exigido === true,
    liberado: dados.liberado === true,
    configurado: dados.configurado !== false,
    ambiente: typeof dados.ambiente === "string" ? dados.ambiente : "",
  };
}

export async function consultarAcesso(): Promise<EstadoAcesso> {
  try {
    const resposta = await fetch(`${URL_API}/acesso/homologacao`, { credentials: "include" });
    const corpo = await resposta.json().catch(() => null);
    return interpretarAcesso(resposta.status, corpo);
  } catch {
    return { exigido: false, liberado: true, configurado: true, ambiente: "desenvolvimento" };
  }
}

export async function entrarHomologacao(senha: string): Promise<string | null> {
  const resposta = await fetch(`${URL_API}/acesso/homologacao`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ senha }),
  });
  if (resposta.ok) {
    return null;
  }
  const corpo = (await resposta.json().catch(() => null)) as { detail?: unknown } | null;
  if (corpo && typeof corpo.detail === "string" && corpo.detail.trim()) {
    return corpo.detail;
  }
  return "Não foi possível liberar o acesso da homologação.";
}
