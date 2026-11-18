import { lerReferencias } from "./api.ts";
import type { Conversa, Mensagem, PapelMensagem, Referencia, TipoDocumento } from "../types/chat.ts";
import { TIPOS_DOCUMENTO } from "../types/chat.ts";

const CHAVE_CONVERSAS = "meu-direito.conversas";
const CHAVE_ATIVA = "meu-direito.conversa-ativa";
const CHAVE_CONVERSAS_ANTIGA = "meu-ia.conversas";
const CHAVE_ATIVA_ANTIGA = "meu-ia.conversa-ativa";

function tipoValido(valor: unknown): valor is TipoDocumento {
  return typeof valor === "string" && TIPOS_DOCUMENTO.some((tipo) => tipo === valor);
}

function mensagemValida(valor: unknown): valor is Mensagem {
  if (!valor || typeof valor !== "object") {
    return false;
  }
  const mensagem = valor as Partial<Mensagem>;
  return (
    typeof mensagem.id === "string" &&
    (mensagem.papel === "usuario" || mensagem.papel === "agente") &&
    typeof mensagem.conteudo === "string" &&
    typeof mensagem.criadaEm === "string"
  );
}

function lerLista(chave: string): Conversa[] {
  try {
    const bruto = localStorage.getItem(chave);
    if (!bruto) {
      return [];
    }
    const dados: unknown = JSON.parse(bruto);
    if (!Array.isArray(dados)) {
      return [];
    }
    return dados.flatMap((item) => {
      if (!item || typeof item !== "object") {
        return [];
      }
      const conversa = item as Partial<Conversa>;
      if (
        typeof conversa.id !== "string" ||
        typeof conversa.titulo !== "string" ||
        typeof conversa.criadaEm !== "string" ||
        !Array.isArray(conversa.mensagens) ||
        !conversa.mensagens.every(mensagemValida)
      ) {
        return [];
      }
      return [
        {
          id: conversa.id,
          titulo: conversa.titulo,
          criadaEm: conversa.criadaEm,
          mensagens: conversa.mensagens.map((mensagem) => ({
            ...mensagem,
            referencias: lerReferencias(mensagem.referencias),
          })),
          tipoDocumento: tipoValido(conversa.tipoDocumento) ? conversa.tipoDocumento : null,
          atualizadaEm: typeof conversa.atualizadaEm === "string" ? conversa.atualizadaEm : undefined,
        },
      ];
    });
  } catch {
    return [];
  }
}

export function lerConversas(): Conversa[] {
  const atuais = lerLista(CHAVE_CONVERSAS);
  if (atuais.length > 0) {
    return atuais;
  }
  return lerLista(CHAVE_CONVERSAS_ANTIGA);
}

export function salvarConversas(conversas: Conversa[]): void {
  localStorage.setItem(CHAVE_CONVERSAS, JSON.stringify(conversas));
}

export function lerConversaAtiva(): string | null {
  return localStorage.getItem(CHAVE_ATIVA) || localStorage.getItem(CHAVE_ATIVA_ANTIGA) || null;
}

export function salvarConversaAtiva(id: string | null): void {
  if (id) {
    localStorage.setItem(CHAVE_ATIVA, id);
  } else {
    localStorage.removeItem(CHAVE_ATIVA);
  }
}

export function apagarHistoricoLocal(): void {
  localStorage.removeItem(CHAVE_CONVERSAS);
  localStorage.removeItem(CHAVE_ATIVA);
  localStorage.removeItem(CHAVE_CONVERSAS_ANTIGA);
  localStorage.removeItem(CHAVE_ATIVA_ANTIGA);
}

export function criarMensagem(papel: PapelMensagem, conteudo: string, referencias?: Referencia[]): Mensagem {
  return {
    id: crypto.randomUUID(),
    papel,
    conteudo,
    criadaEm: new Date().toISOString(),
    referencias: referencias && referencias.length > 0 ? referencias : undefined,
  };
}

export function tituloDaPergunta(pergunta: string): string {
  const limpo = pergunta.replace(/\s+/g, " ").trim();
  if (limpo.length <= 42) {
    return limpo;
  }
  return `${limpo.slice(0, 42).trimEnd()}…`;
}
