export type PapelMensagem = "usuario" | "agente";

export const PERFIS = ["estudante", "profissional", "cidadao"] as const;
export type Perfil = (typeof PERFIS)[number];

export const TIPOS_DOCUMENTO = [
  "peticao_inicial",
  "contrato",
  "notificacao",
  "requerimento",
  "declaracao",
  "parecer",
  "resumo",
] as const;
export type TipoDocumento = (typeof TIPOS_DOCUMENTO)[number];

export interface Referencia {
  id: string;
  tipo: "legislacao";
  verificada: boolean;
  norma: string | null;
  numero: string | null;
  ano: string | null;
  artigo: string | null;
  tribunal: string | null;
  processo: string | null;
  relator: string | null;
  data_decisao: string | null;
  url: string | null;
  consultado_em: string;
  situacao: string;
  tipo_texto: string | null;
  vigencia_confirmada: boolean;
  notas_fonte: string[];
  aviso: string;
}

export interface Mensagem {
  id: string;
  papel: PapelMensagem;
  conteudo: string;
  criadaEm: string;
  referencias?: Referencia[];
}

export interface Conversa {
  id: string;
  titulo: string;
  criadaEm: string;
  mensagens: Mensagem[];
  tipoDocumento?: TipoDocumento | null;
}

export interface RespostaConversa {
  resposta: string;
  referencias?: Referencia[];
}
