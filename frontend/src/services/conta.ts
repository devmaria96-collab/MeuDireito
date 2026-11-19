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
  email_confirmado: boolean;
  confirmacao_motivo: "link" | "conta_anterior" | null;
}

export interface SessaoConta {
  autenticado: boolean;
  contas_disponiveis: boolean;
  csrf: string | null;
  usuario: UsuarioConta | null;
  correio_configurado: boolean;
  demonstracao: boolean;
  confirmacao_enviada?: boolean;
  confirmacao_mensagem?: string;
}

async function lerJson(resposta: Response): Promise<unknown> {
  try {
    return await resposta.json();
  } catch {
    return null;
  }
}

function usuarioDe(valor: unknown): UsuarioConta | null {
  if (!valor || typeof valor !== "object") {
    return null;
  }
  const usuario = valor as Partial<UsuarioConta>;
  if (typeof usuario.email !== "string" || typeof usuario.nome_exibicao !== "string") {
    return null;
  }
  const motivo = usuario.confirmacao_motivo === "link" || usuario.confirmacao_motivo === "conta_anterior" ? usuario.confirmacao_motivo : null;
  return {
    nome_exibicao: usuario.nome_exibicao,
    email: usuario.email,
    perfil_juridico: usuario.perfil_juridico === "estudante" || usuario.perfil_juridico === "profissional" ? usuario.perfil_juridico : "cidadao",
    tema: usuario.tema === "claro" || usuario.tema === "escuro" ? usuario.tema : null,
    tipo_avatar: usuario.tipo_avatar === "imagem" ? "imagem" : "biblioteca",
    avatar_codigo: typeof usuario.avatar_codigo === "string" ? usuario.avatar_codigo : "balanca",
    email_confirmado: usuario.email_confirmado === true,
    confirmacao_motivo: motivo,
  };
}

function sessaoDe(corpo: unknown): SessaoConta {
  const bruto = (corpo ?? {}) as Partial<SessaoConta>;
  return {
    autenticado: Boolean(bruto.autenticado && bruto.usuario),
    contas_disponiveis: bruto.contas_disponiveis !== false,
    csrf: typeof bruto.csrf === "string" ? bruto.csrf : null,
    usuario: usuarioDe(bruto.usuario),
    correio_configurado: bruto.correio_configurado === true,
    demonstracao: bruto.demonstracao === true,
    confirmacao_enviada: bruto.confirmacao_enviada === true,
    confirmacao_mensagem: typeof bruto.confirmacao_mensagem === "string" ? bruto.confirmacao_mensagem : undefined,
  };
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
    return { autenticado: false, contas_disponiveis: false, csrf: null, usuario: null, correio_configurado: false, demonstracao: false };
  }
  return sessaoDe(corpo);
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
  return sessaoDe(corpo);
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
  return sessaoDe(corpo);
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
  return sessaoDe(corpo);
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
  return sessaoDe(corpo);
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
  return sessaoDe(corpo);
}

export async function carregarFoto(): Promise<string | null> {
  const resposta = await fetch(`${URL_API}/conta/avatar`, { credentials: "include" });
  if (!resposta.ok) {
    return null;
  }
  return URL.createObjectURL(await resposta.blob());
}

export async function pedirRedefinicao(email: string): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/recuperar-senha`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível enviar a redefinição."));
  }
  return detalhe(corpo, "Se houver uma conta com esse e-mail, enviaremos um link de redefinição.");
}

export async function confirmarEmail(token: string): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/confirmar-email`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "O link de confirmação é inválido ou expirou."));
  }
  return detalhe(corpo, "E-mail confirmado.");
}

export async function reenviarConfirmacao(email: string): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/reenviar-confirmacao`, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível reenviar a confirmação."));
  }
  return detalhe(corpo, "Se houver uma conta com esse e-mail e ele ainda não estiver confirmado, enviaremos um link.");
}

export async function avisoRecuperacao(): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/recuperar-senha`, { method: "POST" });
  const corpo = await lerJson(resposta);
  return detalhe(corpo, "O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente.");
}

export async function alterarSenha(csrf: string, atual: string, nova: string, confirmar: string): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/senha`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ senha_atual: atual, nova_senha: nova, confirmar_senha: confirmar }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível alterar a senha."));
  }
  return detalheMensagem(corpo, "Senha alterada. As outras sessões foram encerradas.");
}

export async function redefinirSenha(token: string, nova: string, confirmar: string): Promise<string> {
  const resposta = await fetch(`${URL_API}/conta/redefinir-senha`, {
    method: "POST",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ token, nova_senha: nova, confirmar_senha: confirmar }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível redefinir a senha."));
  }
  return detalheMensagem(corpo, "Senha redefinida. Entre novamente com a nova senha.");
}

export interface SessaoAtiva {
  id: string;
  criada_em: string;
  expira_em: string;
  atual: boolean;
}

export async function listarSessoes(): Promise<SessaoAtiva[]> {
  const resposta = await fetch(`${URL_API}/conta/sessoes`, { credentials: "include" });
  const corpo = await lerJson(resposta);
  if (!resposta.ok || !corpo || typeof corpo !== "object" || !("sessoes" in corpo) || !Array.isArray(corpo.sessoes)) {
    throw new ErroApi(detalhe(corpo, "Não foi possível carregar as sessões."));
  }
  return corpo.sessoes.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const sessao = item as Partial<SessaoAtiva>;
    if (typeof sessao.id !== "string" || typeof sessao.criada_em !== "string") {
      return [];
    }
    return [{ id: sessao.id, criada_em: sessao.criada_em, expira_em: String(sessao.expira_em ?? ""), atual: Boolean(sessao.atual) }];
  });
}

async function encerrar(caminho: string, csrf: string): Promise<void> {
  const resposta = await fetch(`${URL_API}${caminho}`, {
    method: "DELETE",
    credentials: "include",
    headers: { "X-CSRF-Token": csrf },
  });
  if (!resposta.ok) {
    throw new ErroApi(detalhe(await lerJson(resposta), "Não foi possível encerrar a sessão."));
  }
}

export function encerrarOutrasSessoes(csrf: string): Promise<void> {
  return encerrar("/conta/sessoes/outras", csrf);
}

export function encerrarTodasSessoes(csrf: string): Promise<void> {
  return encerrar("/conta/sessoes", csrf);
}

export function encerrarSessao(csrf: string, id: string): Promise<void> {
  return encerrar(`/conta/sessoes/${id}`, csrf);
}

export interface TextoPrivacidade {
  apagados: string[];
  nao_armazenados: string[];
  retencao: string;
  treinamento: string;
}

export async function lerPrivacidade(): Promise<TextoPrivacidade> {
  const resposta = await fetch(`${URL_API}/conta/privacidade`, { credentials: "include" });
  const corpo = (await lerJson(resposta)) as Partial<TextoPrivacidade> | null;
  if (!resposta.ok || !corpo || !Array.isArray(corpo.apagados) || typeof corpo.retencao !== "string") {
    throw new ErroApi(detalhe(corpo, "Não foi possível carregar as informações de privacidade."));
  }
  return {
    apagados: corpo.apagados.filter((item): item is string => typeof item === "string"),
    nao_armazenados: Array.isArray(corpo.nao_armazenados) ? corpo.nao_armazenados.filter((item): item is string => typeof item === "string") : [],
    retencao: corpo.retencao,
    treinamento: typeof corpo.treinamento === "string" ? corpo.treinamento : "",
  };
}

export async function baixarDados(): Promise<void> {
  const resposta = await fetch(`${URL_API}/conta/dados`, { credentials: "include" });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível preparar os seus dados."));
  }
  const arquivo = new Blob([JSON.stringify(corpo, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(arquivo);
  const link = document.createElement("a");
  link.href = url;
  link.download = "meus-dados-meu-direito.json";
  link.click();
  URL.revokeObjectURL(url);
}

export async function excluirConta(csrf: string, senha: string, confirmacao: string): Promise<void> {
  const resposta = await fetch(`${URL_API}/conta`, {
    method: "DELETE",
    credentials: "include",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ senha, confirmacao }),
  });
  const corpo = await lerJson(resposta);
  if (!resposta.ok) {
    throw new ErroApi(detalhe(corpo, "Não foi possível excluir a conta."));
  }
}

function detalheMensagem(corpo: unknown, reserva: string): string {
  if (corpo && typeof corpo === "object" && "mensagem" in corpo && typeof corpo.mensagem === "string") {
    return corpo.mensagem;
  }
  return reserva;
}
