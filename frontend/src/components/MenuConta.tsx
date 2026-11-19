import { Eye, EyeOff, Scale, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Tema } from "../hooks/useTema.ts";
import {
  alterarSenha,
  baixarDados,
  confirmarEmail,
  pedirRedefinicao,
  reenviarConfirmacao,
  cadastrarConta,
  carregarFoto,
  encerrarOutrasSessoes,
  encerrarSessao,
  encerrarTodasSessoes,
  entrarConta,
  enviarFoto,
  excluirConta,
  lerPrivacidade,
  lerSessao,
  listarSessoes,
  redefinirSenha,
  removerFoto,
  sairConta,
  salvarPerfil,
  type SessaoAtiva,
  type TextoPrivacidade,
  type UsuarioConta,
} from "../services/conta.ts";
import { lerPanorama, type PanoramaLgpd } from "../services/lgpd.ts";
import type { Perfil } from "../types/chat.ts";
import { AVATARES_JURIDICOS, AvatarJuridico } from "./AvatarJuridico.tsx";
import { PainelArmazenamento } from "./PainelArmazenamento.tsx";

type Tela = "menu" | "entrar" | "cadastrar" | "perfil" | "conta" | "recuperar" | "senha" | "sessoes" | "privacidade" | "excluir" | "redefinir" | "confirmar";

interface PropriedadesMenu {
  perfil: Perfil;
  tema: Tema;
  tokenRedefinicao?: string | null;
  tokenConfirmacao?: string | null;
  onPerfil: (perfil: Perfil) => void;
  onTema: (tema: Tema) => void;
  onSessao: (usuario: UsuarioConta | null, csrf: string | null) => void;
  onTokenConsumido?: () => void;
  onAbrirDocumento?: (pagina: "privacidade" | "termos") => void;
}

const campo =
  "min-h-11 w-full rounded-xl border border-black/15 bg-white px-3 text-base text-black outline-none focus:border-[#e10600] sm:text-sm dark:border-white/15 dark:bg-black dark:text-white";
const botaoCheio = "min-h-11 w-full rounded-full bg-[#9f1239] text-sm font-medium text-white disabled:opacity-60";
const confirmacoesEmCurso = new Set<string>();
const PERFIS_CONTA: { id: Perfil; rotulo: string }[] = [
  { id: "estudante", rotulo: "Estudante" },
  { id: "profissional", rotulo: "Profissional" },
  { id: "cidadao", rotulo: "Cidadão" },
];

function Marca() {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#9f1239] text-white" aria-hidden="true">
        <Scale size={26} />
      </span>
      <div>
        <p className="text-sm font-semibold leading-5">Meu Direito</p>
        <p className="text-xs leading-5 text-[#5c5c5c] dark:text-white/70">O conhecimento jurídico ao seu alcance.</p>
      </div>
    </div>
  );
}

export function MenuConta({ perfil, tema, tokenRedefinicao, tokenConfirmacao, onPerfil, onTema, onSessao, onTokenConsumido, onAbrirDocumento }: PropriedadesMenu) {
  const [aberto, setAberto] = useState(false);
  const [tela, setTela] = useState<Tela>("menu");
  const [usuario, setUsuario] = useState<UsuarioConta | null>(null);
  const [csrf, setCsrf] = useState<string | null>(null);
  const [foto, setFoto] = useState<string | null>(null);
  const [contasDisponiveis, setContasDisponiveis] = useState(true);
  const [correioConfigurado, setCorreioConfigurado] = useState(false);
  const [emailRecuperacao, setEmailRecuperacao] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarNova, setConfirmarNova] = useState("");
  const [sessoes, setSessoes] = useState<SessaoAtiva[]>([]);
  const [privacidade, setPrivacidade] = useState<TextoPrivacidade | null>(null);
  const [panorama, setPanorama] = useState<PanoramaLgpd | null>(null);
  const [confirmacaoExclusao, setConfirmacaoExclusao] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [nome, setNome] = useState("");
  const fotoAtual = useRef<string | null>(null);

  function aplicarSessao(proxima: UsuarioConta | null, token: string | null) {
    setUsuario(proxima);
    setCsrf(token);
    onSessao(proxima, token);
  }

  function trocarFoto(proxima: string | null) {
    if (fotoAtual.current) {
      URL.revokeObjectURL(fotoAtual.current);
    }
    fotoAtual.current = proxima;
    setFoto(proxima);
  }

  useEffect(() => {
    if (!tokenRedefinicao) {
      return;
    }
    setAberto(true);
    setTela("redefinir");
    setErro(null);
    setAviso(null);
  }, [tokenRedefinicao]);

  useEffect(() => {
    if (!tokenConfirmacao || confirmacoesEmCurso.has(tokenConfirmacao)) {
      return;
    }
    confirmacoesEmCurso.add(tokenConfirmacao);
    setAberto(true);
    setTela("confirmar");
    setEnviando(true);
    void confirmarEmail(tokenConfirmacao)
      .then(async (mensagem) => {
        setAviso(mensagem);
        const sessao = await lerSessao();
        setCorreioConfigurado(sessao.correio_configurado);
        if (sessao.usuario && sessao.csrf) {
          aplicarSessao(sessao.usuario, sessao.csrf);
        }
        onTokenConsumido?.();
      })
      .catch((falha: unknown) => {
        setErro(falha instanceof Error ? falha.message : "O link de confirmação é inválido ou expirou.");
        onTokenConsumido?.();
      })
      .finally(() => setEnviando(false));
  }, [tokenConfirmacao, onTokenConsumido]);

  useEffect(() => {
    let ativo = true;
    void lerSessao().then(async (sessao) => {
      if (!ativo) {
        return;
      }
      setContasDisponiveis(sessao.contas_disponiveis);
      setCorreioConfigurado(sessao.correio_configurado);
      if (sessao.usuario && sessao.csrf) {
        guardarVisitante();
        aplicarPreferencias(sessao.usuario);
        aplicarSessao(sessao.usuario, sessao.csrf);
        if (sessao.usuario.tipo_avatar === "imagem") {
          trocarFoto(await carregarFoto());
        }
      } else {
        aplicarSessao(null, null);
      }
    });
    return () => {
      ativo = false;
      if (fotoAtual.current) {
        URL.revokeObjectURL(fotoAtual.current);
      }
    };
    // A leitura inicial acontece uma vez. Preferências posteriores passam pelos botões.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function guardarVisitante() {
    if (sessionStorage.getItem("md-perfil-visitante")) {
      return;
    }
    sessionStorage.setItem("md-perfil-visitante", perfil);
    sessionStorage.setItem("md-tema-visitante", tema);
  }

  function aplicarPreferencias(conta: UsuarioConta) {
    if (conta.perfil_juridico) {
      onPerfil(conta.perfil_juridico);
    }
    if (conta.tema === "claro" || conta.tema === "escuro") {
      onTema(conta.tema);
    }
  }

  function restaurarVisitante() {
    const perfilSalvo = sessionStorage.getItem("md-perfil-visitante");
    const temaSalvo = sessionStorage.getItem("md-tema-visitante");
    if (perfilSalvo === "estudante" || perfilSalvo === "profissional" || perfilSalvo === "cidadao") {
      onPerfil(perfilSalvo);
    }
    if (temaSalvo === "claro" || temaSalvo === "escuro") {
      onTema(temaSalvo);
    }
    sessionStorage.removeItem("md-perfil-visitante");
    sessionStorage.removeItem("md-tema-visitante");
  }

  function fechar() {
    setAberto(false);
    setErro(null);
    setAviso(null);
    setMostrarSenha(false);
    setTela("menu");
  }

  function abrirTela(proxima: Tela) {
    setErro(null);
    setAviso(null);
    setTela(proxima);
    setAberto(true);
  }

  async function aoCadastrar() {
    const nomeLimpo = nome.trim();
    if (nomeLimpo.includes("@") || nomeLimpo.length > 40) {
      setErro("O nome de exibição não pode ser um e-mail nem passar de 40 caracteres.");
      return;
    }
    if (senha.length < 8 || senha.length > 128) {
      setErro("A senha precisa ter entre 8 e 128 caracteres.");
      return;
    }
    if (senha !== confirmar) {
      setErro("A confirmação da senha não confere.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      guardarVisitante();
      const sessao = await cadastrarConta(email, senha, confirmar, nome);
      if (sessao.usuario && sessao.csrf) {
        aplicarPreferencias(sessao.usuario);
        aplicarSessao(sessao.usuario, sessao.csrf);
        setCorreioConfigurado(sessao.correio_configurado);
        setNome(sessao.usuario.nome_exibicao);
        setAviso(sessao.confirmacao_mensagem ?? null);
        setTela(sessao.usuario.email_confirmado ? "perfil" : "conta");
        setSenha("");
        setConfirmar("");
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível criar a conta.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoEntrar() {
    setEnviando(true);
    setErro(null);
    try {
      guardarVisitante();
      const sessao = await entrarConta(email, senha);
      if (sessao.usuario && sessao.csrf) {
        aplicarPreferencias(sessao.usuario);
        aplicarSessao(sessao.usuario, sessao.csrf);
        setCorreioConfigurado(sessao.correio_configurado);
        trocarFoto(sessao.usuario.tipo_avatar === "imagem" ? await carregarFoto() : null);
        setSenha("");
        fechar();
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "E-mail ou senha não conferem.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoSair() {
    if (csrf) {
      await sairConta(csrf);
    }
    aplicarSessao(null, null);
    trocarFoto(null);
    restaurarVisitante();
    setEmail("");
    setSenha("");
    fechar();
  }

  function dataDaSessao(iso: string): string {
    const data = new Date(iso);
    if (Number.isNaN(data.getTime())) {
      return "";
    }
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short" }).format(data);
  }

  async function aoAlterarSenha() {
    if (!csrf) {
      return;
    }
    if (novaSenha.length < 8 || novaSenha !== confirmarNova) {
      setErro(novaSenha.length < 8 ? "A senha precisa ter entre 8 e 128 caracteres." : "A confirmação da senha não confere.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      setAviso(await alterarSenha(csrf, senhaAtual, novaSenha, confirmarNova));
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarNova("");
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível alterar a senha.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoRedefinir() {
    if (!tokenRedefinicao) {
      return;
    }
    if (novaSenha.length < 8 || novaSenha !== confirmarNova) {
      setErro(novaSenha.length < 8 ? "A senha precisa ter entre 8 e 128 caracteres." : "A confirmação da senha não confere.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      setAviso(await redefinirSenha(tokenRedefinicao, novaSenha, confirmarNova));
      onTokenConsumido?.();
      aplicarSessao(null, null);
      setNovaSenha("");
      setConfirmarNova("");
      setTela("entrar");
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível redefinir a senha.");
    } finally {
      setEnviando(false);
    }
  }

  async function abrirSessoes() {
    abrirTela("sessoes");
    setEnviando(true);
    try {
      setSessoes(await listarSessoes());
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível carregar as sessões.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoEncerrarSessao(id: string, atual: boolean) {
    if (!csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await encerrarSessao(csrf, id);
      if (atual) {
        aplicarSessao(null, null);
        restaurarVisitante();
        fechar();
        return;
      }
      setSessoes(await listarSessoes());
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível encerrar a sessão.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoEncerrarOutras() {
    if (!csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await encerrarOutrasSessoes(csrf);
      setSessoes(await listarSessoes());
      setAviso("As outras sessões foram encerradas.");
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível encerrar as outras sessões.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoEncerrarTodas() {
    if (!csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await encerrarTodasSessoes(csrf);
      aplicarSessao(null, null);
      restaurarVisitante();
      fechar();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível encerrar as sessões.");
      setEnviando(false);
    }
  }

  async function abrirPrivacidade() {
    abrirTela("privacidade");
    setEnviando(true);
    try {
      const [contaPrivacidade, descricao] = await Promise.all([lerPrivacidade(), lerPanorama()]);
      setPrivacidade(contaPrivacidade);
      setPanorama(descricao);
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível carregar as informações de privacidade.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoBaixarDados() {
    setEnviando(true);
    setErro(null);
    try {
      await baixarDados();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível preparar os seus dados.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoExcluirConta() {
    if (!csrf || confirmacaoExclusao !== "EXCLUIR") {
      setErro("Digite EXCLUIR para confirmar.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await excluirConta(csrf, senhaAtual, confirmacaoExclusao);
      aplicarSessao(null, null);
      trocarFoto(null);
      restaurarVisitante();
      setSenhaAtual("");
      setConfirmacaoExclusao("");
      fechar();
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível excluir a conta.");
      setEnviando(false);
    }
  }

  async function escolherAvatar(codigo: string) {
    if (!csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const sessao = await salvarPerfil(csrf, { avatar_codigo: codigo });
      if (sessao.usuario) {
        aplicarSessao(sessao.usuario, sessao.csrf);
        trocarFoto(null);
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível trocar o avatar.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoEnviarFoto(arquivo: File | undefined) {
    if (!arquivo || !csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const sessao = await enviarFoto(csrf, arquivo);
      if (sessao.usuario) {
        aplicarSessao(sessao.usuario, sessao.csrf);
        trocarFoto(await carregarFoto());
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível enviar a imagem.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoRemoverFoto() {
    if (!csrf) {
      return;
    }
    setEnviando(true);
    try {
      const sessao = await removerFoto(csrf);
      if (sessao.usuario) {
        aplicarSessao(sessao.usuario, sessao.csrf);
        trocarFoto(null);
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível remover a imagem.");
    } finally {
      setEnviando(false);
    }
  }

  async function escolherPerfilJuridico(proximo: Perfil) {
    onPerfil(proximo);
    if (!csrf) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const sessao = await salvarPerfil(csrf, { perfil_juridico: proximo });
      if (sessao.usuario) {
        aplicarSessao(sessao.usuario, sessao.csrf);
        setAviso("Perfil salvo nesta conta.");
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível salvar o perfil.");
    } finally {
      setEnviando(false);
    }
  }

  async function aoSalvarNome() {
    if (!csrf) {
      return;
    }
    if (nome.includes("@") || nome.trim().length > 40) {
      setErro("O nome de exibição não pode ser um e-mail nem passar de 40 caracteres.");
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const sessao = await salvarPerfil(csrf, { nome, perfil_juridico: perfil, tema });
      if (sessao.usuario) {
        aplicarSessao(sessao.usuario, sessao.csrf);
        setAviso("Perfil salvo nesta conta.");
      }
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível salvar o perfil.");
    } finally {
      setEnviando(false);
    }
  }

  const rosto = usuario?.tipo_avatar === "imagem" && foto ? (
    <img src={foto} alt="" className="h-8 w-8 rounded-full object-cover" />
  ) : (
    <span className="grid h-8 w-8 place-items-center rounded-full bg-black text-white dark:bg-white dark:text-black">
      {usuario ? <AvatarJuridico codigo={usuario.avatar_codigo} className="h-5 w-5" /> : <UserRound size={16} />}
    </span>
  );

  return (
    <>
      <button
        type="button"
        onClick={() => abrirTela(usuario ? "menu" : "menu")}
        className="inline-flex min-h-11 items-center gap-2 rounded-full px-2 text-sm text-black hover:bg-black/5 dark:text-white dark:hover:bg-white/10"
        aria-label={usuario ? `Conta de ${usuario.nome_exibicao}` : "Entrar ou criar conta"}
      >
        {rosto}
        <span className="hidden sm:inline">{usuario ? usuario.nome_exibicao : "Entrar"}</span>
      </button>
      {aberto && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center sm:p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-conta"
            className="max-h-[100dvh] w-full overflow-y-auto rounded-t-2xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-black shadow-xl sm:max-h-[90dvh] sm:max-w-md sm:rounded-2xl sm:p-5 dark:bg-black dark:text-white"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                {tela === "entrar" || tela === "cadastrar" || (tela === "menu" && !usuario) ? (
                  <Marca />
                ) : (
                  <p className="text-xs font-medium tracking-wide text-[#9f1239]">Meu Direito</p>
                )}
                <h2 id="titulo-conta" className="mt-2 text-lg font-semibold">
                  {tituloDaTela(tela, usuario)}
                </h2>
              </div>
              <button type="button" onClick={fechar} className="grid h-11 w-11 place-items-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10" aria-label="Fechar conta">
                <X size={18} />
              </button>
            </div>
            {!contasDisponiveis && (
              <p className="mt-3 text-sm leading-6">
                O cadastro fica indisponível enquanto o banco de contas não está no ar. A pesquisa continua aberta sem login.
              </p>
            )}
            {tela === "menu" && !usuario && (
              <div className="mt-4 grid gap-2">
                <button type="button" className={botaoCheio} onClick={() => abrirTela("entrar")}>Entrar</button>
                <button type="button" className="min-h-11 rounded-full border border-black/15 text-sm dark:border-white/20" onClick={() => abrirTela("cadastrar")}>Criar conta</button>
                <button type="button" className="min-h-11 text-sm text-[#5c5c5c] underline dark:text-white/70" onClick={fechar}>Continuar sem entrar</button>
              </div>
            )}
            {tela === "menu" && usuario && (
              <div className="mt-4 grid gap-2">
                <button type="button" className="min-h-11 rounded-xl border border-black/10 px-3 text-left text-sm dark:border-white/15" onClick={() => { setNome(usuario.nome_exibicao); abrirTela("perfil"); }}>Meu perfil</button>
                <button type="button" className="min-h-11 rounded-xl border border-black/10 px-3 text-left text-sm dark:border-white/15" onClick={() => abrirTela("conta")}>Configurações da conta</button>
                <button type="button" className="min-h-11 rounded-xl px-3 text-left text-sm text-[#9f1239]" onClick={() => void aoSair()}>Sair</button>
              </div>
            )}
            {(tela === "entrar" || tela === "cadastrar") && (
              <form
                className="mt-4 grid gap-3"
                onSubmit={(evento) => {
                  evento.preventDefault();
                  void (tela === "entrar" ? aoEntrar() : aoCadastrar());
                }}
              >
                {tela === "cadastrar" && (
                  <label className="grid gap-1 text-sm">
                    Nome de exibição
                    <input className={campo} value={nome} onChange={(evento) => setNome(evento.target.value)} maxLength={40} placeholder="Opcional" autoComplete="nickname" />
                  </label>
                )}
                <label className="grid gap-1 text-sm">
                  E-mail
                  <input className={campo} type="email" required value={email} onChange={(evento) => setEmail(evento.target.value)} autoComplete="email" />
                </label>
                <label className="grid gap-1 text-sm">
                  Senha
                  <span className="flex gap-2">
                    <input className={campo} type={mostrarSenha ? "text" : "password"} required minLength={tela === "cadastrar" ? 8 : 1} value={senha} onChange={(evento) => setSenha(evento.target.value)} autoComplete={tela === "entrar" ? "current-password" : "new-password"} />
                    <button type="button" className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-black/15 dark:border-white/15" onClick={() => setMostrarSenha((atual) => !atual)} aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}>
                      {mostrarSenha ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </span>
                </label>
                {tela === "cadastrar" && (
                  <label className="grid gap-1 text-sm">
                    Confirmar senha
                    <input className={campo} type={mostrarSenha ? "text" : "password"} required minLength={8} value={confirmar} onChange={(evento) => setConfirmar(evento.target.value)} autoComplete="new-password" />
                  </label>
                )}
                <button type="submit" className={botaoCheio} disabled={enviando || !contasDisponiveis}>{tela === "entrar" ? "Entrar" : "Criar conta"}</button>
                {tela === "entrar" && (
                  <button type="button" className="text-sm underline" onClick={() => { setErro(null); setAviso(correioConfigurado ? null : "O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente."); setTela("recuperar"); }}>Esqueci minha senha</button>
                )}
                <button type="button" className="text-sm underline" onClick={() => abrirTela(tela === "entrar" ? "cadastrar" : "entrar")}>
                  {tela === "entrar" ? "Criar conta" : "Entrar"}
                </button>
                <button type="button" className="text-sm text-[#5c5c5c] underline dark:text-white/70" onClick={fechar}>Continuar sem entrar</button>
                <p className="text-xs leading-5 text-[#5c5c5c] dark:text-white/70">
                  Entrar não apaga as conversas deste navegador e não as envia para a conta.
                </p>
              </form>
            )}
            {tela === "recuperar" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                {correioConfigurado ? (
                  <>
                    <p>Informe o e-mail da conta. Se ele não tiver cadastro, a resposta é a mesma. Nenhuma senha é enviada.</p>
                    <label className="text-sm">E-mail<input className={campo} type="email" value={emailRecuperacao} onChange={(evento) => setEmailRecuperacao(evento.target.value)} autoComplete="email" /></label>
                    <button type="button" className={botaoCheio} disabled={enviando} onClick={() => void pedirRedefinicao(emailRecuperacao).then(setAviso).catch((falha: unknown) => setErro(falha instanceof Error ? falha.message : "Não foi possível enviar a redefinição."))}>Enviar link</button>
                  </>
                ) : (
                  <p>{aviso ?? "O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente."}</p>
                )}
                <button type="button" className="text-left underline" onClick={() => abrirTela("entrar")}>Voltar ao login</button>
                <button type="button" className="text-left text-[#5c5c5c] underline dark:text-white/70" onClick={fechar}>Continuar sem entrar</button>
              </div>
            )}
            {tela === "perfil" && usuario && (
              <div className="mt-4 grid gap-3">
                <div className="flex items-center gap-3">
                  {foto && usuario.tipo_avatar === "imagem" ? (
                    <img src={foto} alt="" className="h-14 w-14 rounded-full object-cover" />
                  ) : (
                    <span className="grid h-14 w-14 place-items-center rounded-full bg-black text-white dark:bg-white dark:text-black">
                      <AvatarJuridico codigo={usuario.avatar_codigo} className="h-8 w-8" />
                    </span>
                  )}
                  <p className="text-sm">{usuario.nome_exibicao}</p>
                </div>
                <label className="grid gap-1 text-sm">
                  Nome de exibição
                  <input className={campo} value={nome} onChange={(evento) => setNome(evento.target.value)} maxLength={40} />
                </label>
                <div className="grid gap-1 text-sm">
                  E-mail
                  <p className="rounded-xl border border-black/10 px-3 py-2 break-all dark:border-white/15">{usuario.email}</p>
                  <p className="text-xs leading-5 text-[#5c5c5c] dark:text-white/70">
                    O endereço completo aparece só para você. Ele não entra no cabeçalho.
                  </p>
                </div>
                <div className="grid grid-cols-3 gap-1.5" role="radiogroup" aria-label="Perfil jurídico">
                  {PERFIS_CONTA.map((opcao) => {
                    const ativo = perfil === opcao.id;
                    return (
                      <button
                        key={opcao.id}
                        type="button"
                        role="radio"
                        aria-checked={ativo}
                        disabled={enviando}
                        onClick={() => void escolherPerfilJuridico(opcao.id)}
                        className={`min-h-11 rounded-full px-1 text-[11px] font-medium sm:text-xs ${
                          ativo ? "bg-[#9f1239] text-white" : "border border-black/15 dark:border-white/20"
                        }`}
                      >
                        {opcao.rotulo}
                      </button>
                    );
                  })}
                </div>
                <div className="grid grid-cols-4 gap-2" role="list" aria-label="Avatares jurídicos">
                  {AVATARES_JURIDICOS.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      title={item.nome}
                      aria-label={item.nome}
                      disabled={enviando}
                      onClick={() => void escolherAvatar(item.id)}
                      className={`grid h-14 place-items-center rounded-xl border ${usuario.avatar_codigo === item.id && usuario.tipo_avatar === "biblioteca" ? "border-[#e10600] bg-[#e10600]/10" : "border-black/10 dark:border-white/15"}`}
                    >
                      <AvatarJuridico codigo={item.id} className="h-7 w-7" />
                    </button>
                  ))}
                </div>
                <label className="text-sm">
                  Enviar foto JPEG, PNG ou WebP
                  <input
                    className="mt-1 block w-full text-xs"
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(evento) => void aoEnviarFoto(evento.target.files?.[0])}
                  />
                </label>
                {usuario.tipo_avatar === "imagem" && (
                  <button type="button" className="min-h-11 text-left text-sm underline" onClick={() => void aoRemoverFoto()}>Remover imagem e voltar ao avatar</button>
                )}
                <button type="button" className={botaoCheio} disabled={enviando} onClick={() => void aoSalvarNome()}>Salvar perfil</button>
                <p className="text-xs leading-5 text-[#5c5c5c] dark:text-white/70">
                  A importação pede confirmação e não apaga as conversas deste navegador.
                </p>
              </div>
            )}
            {tela === "conta" && usuario && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>E-mail da conta: {usuario.email}</p>
                {usuario.confirmacao_motivo === "conta_anterior" && (
                  <p>Este endereço foi cadastrado antes da confirmação por e-mail. Nenhum e-mail de confirmação foi enviado por isso.</p>
                )}
                {usuario.confirmacao_motivo === "link" && <p>E-mail confirmado pelo link.</p>}
                {!usuario.email_confirmado && (
                  <>
                    <p>O e-mail ainda não foi confirmado. A pesquisa jurídica continua disponível sem esta confirmação.</p>
                    <button
                      type="button"
                      className="min-h-11 text-left underline"
                      disabled={enviando}
                      onClick={() => {
                        setErro(null);
                        void reenviarConfirmacao(usuario.email)
                          .then(setAviso)
                          .catch((falha: unknown) => setErro(falha instanceof Error ? falha.message : "Não foi possível reenviar a confirmação."));
                      }}
                    >
                      Reenviar confirmação
                    </button>
                  </>
                )}
                <p>A troca de e-mail continua pendente. O endereço não pode ser alterado por aqui.</p>
                <p>As conversas feitas na conta ficam salvas e aparecem nos aparelhos em que você entrar. As deste navegador só entram na conta se você confirmar a importação.</p>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("perfil")}>Editar perfil e avatar</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("senha")}>Alterar senha</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => void abrirSessoes()}>Gerenciar sessões</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => void abrirPrivacidade()}>Privacidade e dados</button>
              </div>
            )}
            {tela === "senha" && (
              <div className="mt-4 grid gap-3">
                <label className="text-sm">Senha atual<input className={campo} type={mostrarSenha ? "text" : "password"} value={senhaAtual} onChange={(evento) => setSenhaAtual(evento.target.value)} autoComplete="current-password" /></label>
                <label className="text-sm">Nova senha<input className={campo} type={mostrarSenha ? "text" : "password"} value={novaSenha} onChange={(evento) => setNovaSenha(evento.target.value)} autoComplete="new-password" minLength={8} /></label>
                <label className="text-sm">Confirmar nova senha<input className={campo} type={mostrarSenha ? "text" : "password"} value={confirmarNova} onChange={(evento) => setConfirmarNova(evento.target.value)} autoComplete="new-password" minLength={8} /></label>
                <button type="button" className="text-left text-sm underline" onClick={() => setMostrarSenha((atual) => !atual)}>{mostrarSenha ? "Ocultar senhas" : "Mostrar senhas"}</button>
                <button type="button" className={botaoCheio} disabled={enviando} onClick={() => void aoAlterarSenha()}>Salvar nova senha</button>
                <button type="button" className="min-h-11 text-sm underline" onClick={() => abrirTela("conta")}>Voltar</button>
              </div>
            )}
            {tela === "confirmar" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>{enviando ? "Confirmando o e-mail…" : aviso ?? "O link de confirmação vale 24 horas e só pode ser usado uma vez."}</p>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela(usuario ? "conta" : "entrar")}>Voltar</button>
              </div>
            )}
            {tela === "redefinir" && (
              <div className="mt-4 grid gap-3">
                <p className="text-sm leading-6">Escolha uma nova senha. O link vale por 30 minutos e só pode ser usado uma vez.</p>
                <label className="text-sm">Nova senha<input className={campo} type={mostrarSenha ? "text" : "password"} value={novaSenha} onChange={(evento) => setNovaSenha(evento.target.value)} autoComplete="new-password" minLength={8} /></label>
                <label className="text-sm">Confirmar nova senha<input className={campo} type={mostrarSenha ? "text" : "password"} value={confirmarNova} onChange={(evento) => setConfirmarNova(evento.target.value)} autoComplete="new-password" minLength={8} /></label>
                <button type="button" className={botaoCheio} disabled={enviando || !tokenRedefinicao} onClick={() => void aoRedefinir()}>Redefinir senha</button>
              </div>
            )}
            {tela === "sessoes" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                {sessoes.map((item) => (
                  <div key={item.id} className="flex items-center justify-between gap-3 rounded-xl border border-black/10 px-3 py-2 dark:border-white/15">
                    <p>
                      {item.atual ? "Este navegador" : "Outro aparelho"}
                      <span className="block text-xs text-[#5c5c5c] dark:text-white/70">Desde {dataDaSessao(item.criada_em)}</span>
                    </p>
                    <button type="button" className="min-h-11 shrink-0 underline" disabled={enviando} onClick={() => void aoEncerrarSessao(item.id, item.atual)}>Encerrar</button>
                  </div>
                ))}
                <button type="button" className="min-h-11 text-left underline" disabled={enviando} onClick={() => void aoEncerrarOutras()}>Encerrar outras sessões</button>
                <button type="button" className="min-h-11 text-left text-[#9f1239] underline" disabled={enviando} onClick={() => void aoEncerrarTodas()}>Encerrar todas as sessões</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("conta")}>Voltar</button>
              </div>
            )}
            {tela === "privacidade" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>Aqui você consulta, corrige o que a conta permite, baixa uma cópia e exclui os dados da conta. Isto não declara conformidade com a LGPD.</p>
                <p>
                  {panorama?.contato
                    ? `Canal de privacidade: ${panorama.contato}.`
                    : "O canal de contato desta instalação ainda não foi configurado."}
                </p>
                <p>
                  {panorama?.controlador
                    ? `Responsável informado: ${panorama.controlador}.`
                    : "O responsável pelo tratamento ainda não foi identificado."}
                </p>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("perfil")}>Corrigir nome, avatar e perfil</button>
                <button
                  type="button"
                  className="min-h-11 text-left underline"
                  onClick={() => {
                    fechar();
                    onAbrirDocumento?.("privacidade");
                  }}
                >
                  Ler a política de privacidade
                </button>
                <p className="font-medium">Será apagado com a conta</p>
                <ul className="list-disc space-y-1 pl-5">
                  {(privacidade?.apagados ?? []).map((item) => <li key={item}>{item}</li>)}
                </ul>
                <p className="font-medium">Não fica guardado na conta</p>
                <ul className="list-disc space-y-1 pl-5">
                  {(privacidade?.nao_armazenados ?? []).map((item) => <li key={item}>{item}</li>)}
                </ul>
                <p>{privacidade?.retencao}</p>
                <p>{privacidade?.treinamento}</p>
                <p>Ao pesquisar, a pergunta atual é enviada ao Google Gemini. As anteriores não vão junto.</p>
                {panorama?.direitos.map((item) => <p key={item}>{item}</p>)}
                <PainelArmazenamento />
                <button type="button" className={botaoCheio} disabled={enviando} onClick={() => void aoBaixarDados()}>Baixar meus dados</button>
                <button type="button" className="min-h-11 text-left text-[#9f1239] underline" onClick={() => abrirTela("excluir")}>Excluir conta</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("conta")}>Voltar</button>
              </div>
            )}
            {tela === "excluir" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>A exclusão apaga o perfil, a foto, as conversas da conta, as referências salvas e as sessões. Digite EXCLUIR e a senha atual para confirmar.</p>
                <p>{privacidade?.retencao}</p>
                <label className="text-sm">Senha atual<input className={campo} type="password" value={senhaAtual} onChange={(evento) => setSenhaAtual(evento.target.value)} autoComplete="current-password" /></label>
                <label className="text-sm">Confirmação<input className={campo} value={confirmacaoExclusao} onChange={(evento) => setConfirmacaoExclusao(evento.target.value)} autoComplete="off" aria-label="Digite EXCLUIR" /></label>
                <button type="button" className="min-h-11 rounded-full bg-[#9f1239] text-sm font-medium text-white disabled:opacity-60" disabled={enviando || confirmacaoExclusao !== "EXCLUIR"} onClick={() => void aoExcluirConta()}>Excluir minha conta</button>
                <button type="button" className="min-h-11 text-left underline" onClick={() => abrirTela("privacidade")}>Voltar</button>
              </div>
            )}
            {erro && <p role="alert" className="mt-3 text-sm text-[#9f1239]">{erro}</p>}
            {aviso && tela !== "recuperar" && <p className="mt-3 text-sm text-[#5c5c5c] dark:text-white/70">{aviso}</p>}
          </div>
        </div>
      )}
    </>
  );
}

function tituloDaTela(tela: Tela, usuario: UsuarioConta | null): string {
  if (tela === "entrar") return "Entrar";
  if (tela === "cadastrar") return "Criar conta";
  if (tela === "perfil") return "Meu perfil";
  if (tela === "conta") return "Configurações da conta";
  if (tela === "recuperar") return "Esqueci minha senha";
  if (tela === "senha") return "Alterar senha";
  if (tela === "redefinir") return "Nova senha";
  if (tela === "confirmar") return "Confirmar e-mail";
  if (tela === "sessoes") return "Sessões";
  if (tela === "privacidade") return "Privacidade e dados";
  if (tela === "excluir") return "Excluir conta";
  return usuario ? usuario.nome_exibicao : "Conta";
}
