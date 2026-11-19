import { URL_API } from "./api.ts";

export interface ItemInventario {
  categoria: string;
  dados: string;
  finalidade: string;
  base_legal: string;
  retencao: string;
  armazenamento: string;
}

export interface Fornecedor {
  nome: string;
  papel: string;
  dados: string;
  observacao: string;
}

export interface CookieDescrito {
  nome: string;
  necessario: boolean;
  descricao: string;
}

export interface PanoramaLgpd {
  conformidade_declarada: false;
  aviso: string;
  controlador: string | null;
  marca_comercial: string | null;
  contato: string | null;
  requisicao_https: boolean;
  recuperacao_de_senha_configurada: boolean;
  dias_retencao_exclusao: number;
  modelos_gemini: string;
  fornecedores: Fornecedor[];
  inventario: ItemInventario[];
  cookies: CookieDescrito[];
  direitos: string[];
  criancas: string;
  sensiveis_e_terceiros: string;
  treinamento: string;
  incidentes: string;
  pendencias_administrador: string[];
  modo_demonstracao: boolean;
  identificacao: string | null;
  aviso_demonstracao: string | null;
  gemini: {
    provedor: string;
    enviado: string[];
    nao_enviado_por_esta_instalacao: string[];
    contrato: string;
    transferencia_internacional: string;
  } | null;
}

function texto(valor: unknown): string | null {
  return typeof valor === "string" && valor.trim() ? valor : null;
}

export async function lerPanorama(): Promise<PanoramaLgpd> {
  const resposta = await fetch(`${URL_API}/lgpd`, { credentials: "include" });
  const corpo = (await resposta.json()) as Partial<PanoramaLgpd> | null;
  if (!resposta.ok || !corpo || corpo.conformidade_declarada !== false || !Array.isArray(corpo.inventario)) {
    throw new Error("Não foi possível carregar a descrição do tratamento de dados.");
  }
  return {
    conformidade_declarada: false,
    aviso: texto(corpo.aviso) ?? "Este texto descreve o tratamento desta instalação. Ele não declara conformidade com a LGPD.",
    controlador: texto(corpo.controlador),
    marca_comercial: texto(corpo.marca_comercial),
    contato: texto(corpo.contato),
    requisicao_https: corpo.requisicao_https === true,
    recuperacao_de_senha_configurada: corpo.recuperacao_de_senha_configurada === true,
    dias_retencao_exclusao: typeof corpo.dias_retencao_exclusao === "number" ? corpo.dias_retencao_exclusao : 0,
    modelos_gemini: texto(corpo.modelos_gemini) ?? "",
    fornecedores: Array.isArray(corpo.fornecedores) ? corpo.fornecedores.filter(fornecedorValido) : [],
    inventario: corpo.inventario.filter(itemValido),
    cookies: Array.isArray(corpo.cookies) ? corpo.cookies.filter(cookieValido) : [],
    direitos: Array.isArray(corpo.direitos) ? corpo.direitos.filter((item): item is string => typeof item === "string") : [],
    criancas: texto(corpo.criancas) ?? "",
    sensiveis_e_terceiros: texto(corpo.sensiveis_e_terceiros) ?? "",
    treinamento: texto(corpo.treinamento) ?? "",
    incidentes: texto(corpo.incidentes) ?? "",
    pendencias_administrador: Array.isArray(corpo.pendencias_administrador)
      ? corpo.pendencias_administrador.filter((item): item is string => typeof item === "string")
      : [],
    modo_demonstracao: corpo.modo_demonstracao === true,
    identificacao: texto(corpo.identificacao),
    aviso_demonstracao: texto(corpo.aviso_demonstracao),
    gemini: geminiDe(corpo.gemini),
  };
}

function geminiDe(valor: unknown): PanoramaLgpd["gemini"] {
  if (!valor || typeof valor !== "object") {
    return null;
  }
  const item = valor as Partial<NonNullable<PanoramaLgpd["gemini"]>>;
  if (typeof item.provedor !== "string" || typeof item.contrato !== "string" || typeof item.transferencia_internacional !== "string") {
    return null;
  }
  return {
    provedor: item.provedor,
    enviado: Array.isArray(item.enviado) ? item.enviado.filter((linha): linha is string => typeof linha === "string") : [],
    nao_enviado_por_esta_instalacao: Array.isArray(item.nao_enviado_por_esta_instalacao)
      ? item.nao_enviado_por_esta_instalacao.filter((linha): linha is string => typeof linha === "string")
      : [],
    contrato: item.contrato,
    transferencia_internacional: item.transferencia_internacional,
  };
}

function itemValido(valor: unknown): valor is ItemInventario {
  if (!valor || typeof valor !== "object") {
    return false;
  }
  const item = valor as Partial<ItemInventario>;
  return [item.categoria, item.dados, item.finalidade, item.base_legal, item.retencao, item.armazenamento].every(
    (campo) => typeof campo === "string",
  );
}

function fornecedorValido(valor: unknown): valor is Fornecedor {
  if (!valor || typeof valor !== "object") {
    return false;
  }
  const item = valor as Partial<Fornecedor>;
  return [item.nome, item.papel, item.dados, item.observacao].every((campo) => typeof campo === "string");
}

function cookieValido(valor: unknown): valor is CookieDescrito {
  if (!valor || typeof valor !== "object") {
    return false;
  }
  const item = valor as Partial<CookieDescrito>;
  return typeof item.nome === "string" && typeof item.necessario === "boolean" && typeof item.descricao === "string";
}
