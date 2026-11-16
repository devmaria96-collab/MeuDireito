import type { Perfil, Referencia, RespostaConversa, TipoDocumento } from "../types/chat.ts";

export const URL_API = import.meta.env.VITE_API_URL || "/api";

const LIMITE_PERGUNTA = 8000;

export class ErroApi extends Error {
  status?: number;

  constructor(mensagem: string, status?: number) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
  }
}

function textoSeguro(valor: unknown): string | null {
  if (typeof valor !== "string") {
    return null;
  }
  const texto = valor.trim();
  if (!texto || texto.length > 240) {
    return null;
  }
  if (/sk-|AIza|AQ\./.test(texto)) {
    return null;
  }
  return texto;
}

const TEMPO_LIMITE_MS = 130_000;

function mensagemDeStatus(status: number): string {
  if (status === 401) {
    return "A chave do Gemini foi recusada. Verifique a configuração no backend.";
  }
  if (status === 402) {
    return "A conta do Gemini está sem créditos ou cota disponível.";
  }
  if (status === 429) {
    return "O limite de requisições do Gemini foi excedido. Aguarde um instante e tente novamente.";
  }
  if (status === 503) {
    return "O Gemini está temporariamente indisponível. Tente novamente em instantes.";
  }
  if (status === 504) {
    return "A resposta excedeu o tempo limite. Tente novamente.";
  }
  if (status >= 500) {
    return "O backend encontrou um erro interno ao processar a resposta.";
  }
  return "Não foi possível enviar a pergunta.";
}

function mensagemDeRede(falha: unknown): string {
  const nome = falha instanceof DOMException || falha instanceof Error ? falha.name : "";
  if (nome === "AbortError" || nome === "TimeoutError") {
    return "A resposta excedeu o tempo limite. Tente novamente.";
  }
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return "Falha de conexão com a rede. Verifique sua internet e tente novamente.";
  }
  if (falha instanceof TypeError) {
    return "Falha de conexão com o servidor. Verifique se o backend está em execução.";
  }
  return "O backend está indisponível. Inicie a API e tente novamente.";
}

export async function verificarBackend(): Promise<boolean> {
  const controle = new AbortController();
  const timer = window.setTimeout(() => controle.abort(), 4000);
  try {
    const resposta = await fetch(`${URL_API}/openapi.json`, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: controle.signal,
    });
    return resposta.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

export interface PedidoConversa {
  pergunta: string;
  perfil?: Perfil;
  tipoDocumento?: TipoDocumento | null;
}

export interface FonteOficial {
  nome: string;
  url: string;
  descricao: string;
}

export interface CatalogoFontes {
  verificacao_em_tempo_real: boolean;
  aviso: string;
  fontes: FonteOficial[];
}

export async function obterFontesOficiais(): Promise<CatalogoFontes> {
  const resposta = await fetch(`${URL_API}/fontes-oficiais`, {
    headers: { Accept: "application/json" },
  });
  if (!resposta.ok) {
    throw new ErroApi("Não foi possível carregar as fontes oficiais.");
  }
  const dados = (await resposta.json()) as Partial<CatalogoFontes>;
  if (!Array.isArray(dados.fontes) || typeof dados.aviso !== "string") {
    throw new ErroApi("A lista de fontes oficiais veio incompleta.");
  }
  return {
    verificacao_em_tempo_real: false,
    aviso: dados.aviso,
    fontes: dados.fontes.filter(
      (fonte): fonte is FonteOficial =>
        Boolean(fonte) &&
        typeof fonte.nome === "string" &&
        typeof fonte.url === "string" &&
        typeof fonte.descricao === "string" &&
        fonte.url.startsWith("https://"),
    ),
  };
}

export interface ResultadoLegislacao {
  verificada: boolean;
  norma: string | null;
  numero: string | null;
  ano: string | null;
  artigo: string | null;
  texto_oficial: string | null;
  url: string | null;
  consultado_em: string;
  aviso: string;
  explicacao: string | null;
  aviso_explicacao: string | null;
  situacao?: string;
  tipo_texto?: string | null;
  vigencia_confirmada?: boolean;
  notas_fonte?: string[];
}

export async function consultarLegislacao(consulta: string, perfil?: Perfil): Promise<ResultadoLegislacao> {
  const texto = consulta.trim();
  if (!texto) {
    throw new ErroApi("Digite a lei ou o artigo que deseja consultar.");
  }
  let resposta: Response;
  try {
    resposta = await fetch(`${URL_API}/consultar-legislacao`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ consulta: texto, perfil }),
      signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
    });
  } catch (falha) {
    throw new ErroApi(mensagemDeRede(falha));
  }
  let corpo: unknown = null;
  try {
    corpo = await resposta.json();
  } catch {
    corpo = null;
  }
  if (!resposta.ok) {
    const detalhe =
      corpo && typeof corpo === "object" && "detail" in corpo ? textoSeguro(corpo.detail) : null;
    throw new ErroApi(detalhe ?? mensagemDeStatus(resposta.status), resposta.status);
  }
  const dados = corpo as Partial<ResultadoLegislacao> | null;
  if (!dados || typeof dados.verificada !== "boolean" || typeof dados.aviso !== "string") {
    throw new ErroApi("A consulta à legislação veio incompleta.");
  }
  const url = typeof dados.url === "string" && dados.url.startsWith("https://www.planalto.gov.br/") ? dados.url : null;
  return {
    verificada: dados.verificada && url !== null && typeof dados.texto_oficial === "string",
    norma: typeof dados.norma === "string" ? dados.norma : null,
    numero: typeof dados.numero === "string" ? dados.numero : null,
    ano: typeof dados.ano === "string" ? dados.ano : null,
    artigo: typeof dados.artigo === "string" ? dados.artigo : null,
    texto_oficial: dados.verificada && typeof dados.texto_oficial === "string" ? dados.texto_oficial : null,
    url,
    consultado_em: typeof dados.consultado_em === "string" ? dados.consultado_em : "",
    aviso: dados.aviso,
    explicacao: typeof dados.explicacao === "string" ? dados.explicacao : null,
    aviso_explicacao: typeof dados.aviso_explicacao === "string" ? dados.aviso_explicacao : null,
    situacao: typeof dados.situacao === "string" ? dados.situacao : "nao_verificada",
    tipo_texto: typeof dados.tipo_texto === "string" ? dados.tipo_texto : null,
    vigencia_confirmada: false,
    notas_fonte: Array.isArray(dados.notas_fonte)
      ? dados.notas_fonte.filter((nota): nota is string => typeof nota === "string").slice(0, 12)
      : [],
  };
}

function referenciaValida(valor: unknown): Referencia | null {
  if (!valor || typeof valor !== "object") {
    return null;
  }
  const item = valor as Partial<Referencia>;
  if (typeof item.id !== "string" || typeof item.aviso !== "string" || typeof item.verificada !== "boolean") {
    return null;
  }
  const url =
    item.verificada && typeof item.url === "string" && item.url.startsWith("https://www.planalto.gov.br/")
      ? item.url
      : null;
  return {
    id: item.id,
    tipo: "legislacao",
    verificada: item.verificada && url !== null,
    norma: typeof item.norma === "string" ? item.norma : null,
    numero: typeof item.numero === "string" ? item.numero : null,
    ano: typeof item.ano === "string" ? item.ano : null,
    artigo: typeof item.artigo === "string" ? item.artigo : null,
    tribunal: null,
    processo: null,
    relator: null,
    data_decisao: null,
    url,
    consultado_em: typeof item.consultado_em === "string" ? item.consultado_em : "",
    situacao: item.verificada && url ? (typeof item.situacao === "string" ? item.situacao : "texto_recuperado") : "nao_verificada",
    tipo_texto: typeof item.tipo_texto === "string" ? item.tipo_texto : null,
    vigencia_confirmada: false,
    notas_fonte: Array.isArray(item.notas_fonte)
      ? item.notas_fonte.filter((nota): nota is string => typeof nota === "string").slice(0, 12)
      : [],
    aviso: item.aviso,
  };
}

export function lerReferencias(valor: unknown): Referencia[] {
  if (!Array.isArray(valor)) {
    return [];
  }
  return valor.map(referenciaValida).filter((item): item is Referencia => item !== null);
}

export async function conversar(pedido: PedidoConversa): Promise<RespostaConversa> {
  const texto = pedido.pergunta.trim();
  if (!texto) {
    throw new ErroApi("Digite uma pergunta antes de enviar.");
  }
  if (texto.length > LIMITE_PERGUNTA) {
    throw new ErroApi("A pergunta é longa demais. Reduza o texto e tente novamente.");
  }

  const envio: {
    pergunta: string;
    perfil?: Perfil;
    tipo_documento?: TipoDocumento;
  } = { pergunta: texto };
  if (pedido.perfil) {
    envio.perfil = pedido.perfil;
  }
  if (pedido.tipoDocumento) {
    envio.tipo_documento = pedido.tipoDocumento;
  }

  let resposta: Response;
  try {
    resposta = await fetch(`${URL_API}/conversar`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(envio),
      signal: AbortSignal.timeout(TEMPO_LIMITE_MS),
    });
  } catch (falha) {
    throw new ErroApi(mensagemDeRede(falha));
  }

  let corpo: unknown = null;
  try {
    corpo = await resposta.json();
  } catch {
    corpo = null;
  }

  if (!resposta.ok) {
    const detalhe =
      corpo && typeof corpo === "object" && "detail" in corpo
        ? textoSeguro(corpo.detail)
        : null;
    throw new ErroApi(detalhe ?? mensagemDeStatus(resposta.status), resposta.status);
  }

  const dados = corpo as Partial<RespostaConversa> | null;
  if (!dados || typeof dados.resposta !== "string" || !dados.resposta.trim()) {
    throw new ErroApi("O agente não retornou uma resposta válida.");
  }
  return { resposta: dados.resposta, referencias: lerReferencias(dados.referencias) };
}

const MOTIVOS_AVALIACAO = ["incorreta", "desatualizada", "incompleta", "confusa", "outro"] as const;
export type MotivoAvaliacao = (typeof MOTIVOS_AVALIACAO)[number];

export async function enviarAvaliacao(avaliacao: "positiva" | "negativa", motivo?: MotivoAvaliacao): Promise<void> {
  const corpo: { avaliacao: "positiva" | "negativa"; motivo?: MotivoAvaliacao } = { avaliacao };
  if (avaliacao === "negativa" && motivo) {
    corpo.motivo = motivo;
  }
  let resposta: Response;
  try {
    resposta = await fetch(`${URL_API}/feedback`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
      signal: AbortSignal.timeout(15000),
    });
  } catch (falha) {
    throw new ErroApi(mensagemDeRede(falha));
  }
  if (!resposta.ok && resposta.status !== 204) {
    throw new ErroApi(mensagemDeStatus(resposta.status), resposta.status);
  }
}

