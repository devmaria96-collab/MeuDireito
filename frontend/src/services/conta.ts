import type { Perfil } from "../types/chat.ts";
import type { Tema } from "../hooks/useTema.ts";
import { ErroApi, URL_API } from "./api.ts";

export interface UsuarioConta {
  nome_exibicao: string;
  email: string;
  perfil_juridico: Perfil;
  tema: Tema | null;
  tipo_avatar: "biblioteca" | "imagem";
  avatar_codigo: string;
}

export interface SessaoConta {
  autenticado: boolean;
  contas_disponiveis: boolean;
  csrf: string | null;
  usuario: UsuarioConta | null;
}

async function lerJson(resposta: Response): Promise<unknown> {
  try {
    return await resposta.json();
  } catch {
    return null;
  }
}

function detalhe(corpo: unknown, reserva: string): string {
  if (corpo && typeof corpo === "object" && "detail" in corpo && typeof corpo.detail === "string") {
    return corpo.detail;
  }
  return reserva;
}

export async function lerSessao(): Promise<SessaoConta> {
  const resposta = await fetch(`${URL_API}/conta/sessao`, { credentials: "include" });
  const corpo = (await lerJson(resposta)) as Partial<SessaoConta> | null;
  if (!resposta.ok || !corpo) {
    return { autenticado: false, contas_disponiveis: false, csrf: null, usuario: null };
  }
  return {
    autenticado: Boolean(corpo.autenticado && corpo.usuario),
    contas_disponiveis: Boolean(corpo.contas_disponiveis),
    csrf: typeof corpo.csrf === "string" ? corpo.csrf : null,
    usuario: corpo.usuario ?? null,
  };
}

export async function cadastrarConta(email: string, senha: string, confirmar: string, nome: string): Promise<SessaoConta> {
  const resposta = await fetch(`${URL_API}/conta/cadastrar`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha, confirmar_senha: confirmar, nome: nome.trim() || null }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível criar a conta."));
  }
  return corpo as SessaoConta;
}

export async function entrarConta(email: string, senha: string): Promise<SessaoConta> {
  const resposta = await fetch(`${URL_API}/conta/entrar`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ email, senha }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "E-mail ou senha não conferem."));
  }
  return corpo as SessaoConta;
}

export async function sairConta(csrf: string): Promise<void> {
  await fetch(`${URL_API}/conta/sair`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
  });
}

export async function salvarPerfil(
  csrf: string,
  campos: { nome?: string; perfil_juridico?: Perfil; tema?: Tema | null; avatar_codigo?: string },
): Promise<SessaoConta> {
  const resposta = await fetch(`${URL_API}/conta/perfil`, {
    method: "PATCH",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify(campos),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível salvar o perfil."));
  }
  return corpo as SessaoConta;
}

export async function enviarFoto(csrf: string, arquivo: File): Promise<SessaoConta> {
  const dados = new FormData();
  dados.append("arquivo", arquivo);
  const resposta = await fetch(`${URL_API}/conta/avatar`, {
    method: "POST",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
    body: dados,
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível enviar a imagem."));
  }
  return corpo as SessaoConta;
}

export async function removerFoto(csrf: string): Promise<SessaoConta> {
  const resposta = await fetch(`${URL_API}/conta/avatar`, {
    method: "DELETE",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível remover a imagem."));
  }
  return corpo as SessaoConta;
}

export async function carregarFoto(): Promise<string | null> {
  const resposta = await fetch(`${URL_API}/conta/avatar`, { credentials: "include" });
  if (!resposta.ok) {
    return null;
  }
  return URL.createObjectURL(await resposta.blob());
}

export async function avisoRecuperacao(): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/recuperar-senha`, { method: "POST" });
  const corpo = await lerJson(resposta);
  return detalhe(corpo, "O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente.");
}
