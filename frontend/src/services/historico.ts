import { ErroApi, URL_API, lerReferencias } from "./api.ts";
import { TIPOS_DOCUMENTO, type Conversa, type Mensagem, type TipoDocumento } from "../types/chat.ts";

export class ErroHistorico extends ErroApi {
  conversa?: Conversa;

  constructor(mensagem: string, status?: number, conversa?: Conversa) {
    super(mensagem, status);
    this.name = "ErroHistorico";
    this.conversa = conversa;
  }
}

function tipoValido(valor: unknown): valor is TipoDocumento {
  return typeof valor === "string" && TIPOS_DOCUMENTO.some((tipo) => tipo === valor);
}

function lerMensagem(valor: unknown): Mensagem | null {
  if (!valor || typeof valor !== "object") {
    return null;
  }
  const item = valor as Record<string, unknown>;
  if ((item.papel !== "usuario" && item.papel !== "agente") || typeof item.conteudo !== "string") {
    return null;
  }
  return {
    id: typeof item.id === "string" ? item.id : crypto.randomUUID(),
    papel: item.papel,
    conteudo: item.conteudo,
    criadaEm: typeof item.criada_em === "string" ? item.criada_em : new Date().toISOString(),
    referencias: lerReferencias(item.referencias),
  };
}

export function lerConversaServidor(valor: unknown): Conversa | null {
  if (!valor || typeof valor !== "object") {
    return null;
  }
  const item = valor as Record<string, unknown>;
  if (typeof item.id !== "string" || typeof item.titulo !== "string") {
    return null;
  }
  const brutas = Array.isArray(item.mensagens) ? item.mensagens : null;
  return {
    id: item.id,
    titulo: item.titulo,
    criadaEm: typeof item.criada_em === "string" ? item.criada_em : new Date().toISOString(),
    atualizadaEm: typeof item.atualizada_em === "string" ? item.atualizada_em : undefined,
    origemLocal: typeof item.origem_local === "string" ? item.origem_local : null,
    tipoDocumento: tipoValido(item.tipo_documento) ? item.tipo_documento : null,
    carregada: brutas !== null,
    naConta: true,
    mensagens: (brutas ?? []).flatMap((mensagem: unknown) => {
      const lida = lerMensagem(mensagem);
      return lida ? [lida] : [];
    }),
  };
}

async function lerJson(resposta: Response): Promise<unknown> {
  try {
    return await resposta.json();
  } catch {
    return null;
  }
}

function detalheTexto(corpo: unknown, reserva: string): string {
  if (!corpo || typeof corpo !== "object" || !("detail" in corpo)) {
    return reserva;
  }
  const detalhe = corpo.detail;
  if (typeof detalhe === "string" && detalhe.trim()) {
    return detalhe;
  }
  if (detalhe && typeof detalhe === "object" && "mensagem" in detalhe && typeof detalhe.mensagem === "string") {
    return detalhe.mensagem;
  }
  return reserva;
}

function conversaDoErro(corpo: unknown): Conversa | undefined {
  if (!corpo || typeof corpo !== "object" || !("detail" in corpo)) {
    return undefined;
  }
  const detalhe = corpo.detail;
  if (!detalhe || typeof detalhe !== "object" || !("conversa" in detalhe)) {
    return undefined;
  }
  return lerConversaServidor(detalhe.conversa) ?? undefined;
}

async function pedido(caminho: string, init: RequestInit): Promise<Response> {
  return fetch(`${URL_API}${caminho}`, {
    ...init,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });
}

export async function listarConversas(): Promise<Conversa[]> {
  const resposta = await pedido("/conta/conversas", { method: "GET" });
  const corpo = await lerJson(resposta);
  if (!resposta.ok || !corpo || typeof corpo !== "object" || !("conversas" in corpo) || !Array.isArray(corpo.conversas)) {
    throw new ErroHistorico(detalheTexto(corpo, "Não foi possível carregar as conversas."), resposta.status);
  }
  return corpo.conversas.flatMap((item) => {
    const conversa = lerConversaServidor(item);
    return conversa ? [conversa] : [];
  });
}

export async function obterConversa(id: string): Promise<Conversa> {
  const resposta = await pedido(`/conta/conversas/${id}`, { method: "GET" });
  const corpo = await lerJson(resposta);
  const conversa = corpo && typeof corpo === "object" && "conversa" in corpo ? lerConversaServidor(corpo.conversa) : null;
  if (!resposta.ok || !conversa) {
    throw new ErroHistorico(detalheTexto(corpo, "Não foi possível abrir a conversa."), resposta.status);
  }
  return conversa;
}

export interface PedidoPerguntaConta {
  pergunta: string;
  csrf: string;
  conversaId?: string | null;
  titulo?: string;
  perfil?: string;
  tipoDocumento?: string | null;
}

export async function perguntarConta(envio: PedidoPerguntaConta): Promise<Conversa> {
  let resposta: Response;
  try {
    resposta = await pedido("/conta/conversas/perguntar", {
      method: "POST",
      headers: { "X-CSRF-Token": envio.csrf },
      body: JSON.stringify({
        pergunta: envio.pergunta,
        conversa_id: envio.conversaId || null,
        titulo: envio.titulo,
        perfil: envio.perfil,
        tipo_documento: envio.tipoDocumento || null,
      }),
      signal: AbortSignal.timeout(130_000),
    });
  } catch {
    throw new ErroHistorico("Falha de conexão. A pergunta continua nesta conversa.");
  }
  const corpo = await lerJson(resposta);
  const conversa = corpo && typeof corpo === "object" && "conversa" in corpo ? lerConversaServidor(corpo.conversa) : null;
  if (!resposta.ok || !conversa) {
    throw new ErroHistorico(detalheTexto(corpo, "Não foi possível enviar a pergunta."), resposta.status, conversaDoErro(corpo));
  }
  return conversa;
}

export async function renomearConversa(csrf: string, id: string, titulo: string): Promise<Conversa> {
  const resposta = await pedido(`/conta/conversas/${id}`, {
    method: "PATCH",
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify({ titulo }),
  });
  const corpo = await lerJson(resposta);
  const conversa = corpo && typeof corpo === "object" && "conversa" in corpo ? lerConversaServidor(corpo.conversa) : null;
  if (!resposta.ok || !conversa) {
    throw new ErroHistorico(detalheTexto(corpo, "Não foi possível renomear a conversa."), resposta.status);
  }
  return conversa;
}

export async function apagarConversa(csrf: string, id: string): Promise<void> {
  const resposta = await pedido(`/conta/conversas/${id}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrf },
  });
  if (!resposta.ok) {
    throw new ErroHistorico(detalheTexto(await lerJson(resposta), "Não foi possível excluir a conversa."), resposta.status);
  }
}

export async function apagarHistoricoConta(csrf: string): Promise<void> {
  const resposta = await pedido("/conta/conversas", {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrf },
  });
  if (!resposta.ok) {
    throw new ErroHistorico(detalheTexto(await lerJson(resposta), "Não foi possível apagar o histórico da conta."), resposta.status);
  }
}

export async function importarConversas(csrf: string, conversas: Conversa[]): Promise<{ importadas: number; origens: string[] }> {
  const resposta = await pedido("/conta/conversas/importar", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify({
      conversas: conversas.slice(0, 30).map((conversa) => ({
        id: conversa.id,
        titulo: conversa.titulo,
        tipo_documento: conversa.tipoDocumento ?? null,
        mensagens: conversa.mensagens.slice(0, 80).map((mensagem) => ({
          papel: mensagem.papel,
          conteudo: mensagem.conteudo,
          referencias: mensagem.referencias ?? [],
        })),
      })),
    }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok || !corpo || typeof corpo !== "object") {
    throw new ErroHistorico(detalheTexto(corpo, "Não foi possível importar as conversas."), resposta.status);
  }
  const dados = corpo as { importadas?: unknown; origens?: unknown };
  return {
    importadas: typeof dados.importadas === "number" ? dados.importadas : 0,
    origens: Array.isArray(dados.origens) ? dados.origens.filter((item): item is string => typeof item === "string") : [],
  };
}
