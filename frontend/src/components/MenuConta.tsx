import { Eye, EyeOff, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Tema } from "../hooks/useTema.ts";
import {
  avisoRecuperacao,
  cadastrarConta,
  carregarFoto,
  entrarConta,
  enviarFoto,
  lerSessao,
  removerFoto,
  sairConta,
  salvarPerfil,
  type UsuarioConta,
} from "../services/conta.ts";
import type { Perfil } from "../types/chat.ts";
import { AVATARES_JURIDICOS, AvatarJuridico } from "./AvatarJuridico.tsx";

type Tela = "menu" | "entrar" | "cadastrar" | "perfil" | "conta" | "recuperar";

interface PropriedadesMenu {
  perfil: Perfil;
  tema: Tema;
  onPerfil: (perfil: Perfil) => void;
  onTema: (tema: Tema) => void;
  onSessao: (usuario: UsuarioConta | null, csrf: string | null) => void;
}

const campo =
  "min-h-11 w-full rounded-xl border border-black/15 bg-white px-3 text-base text-black outline-none focus:border-[#e10600] sm:text-sm dark:border-white/15 dark:bg-black dark:text-white";
const botaoCheio = "min-h-11 w-full rounded-full bg-[#9f1239] text-sm font-medium text-white disabled:opacity-60";

export function MenuConta({ perfil, tema, onPerfil, onTema, onSessao }: PropriedadesMenu) {
  const [aberto, setAberto] = useState(false);
  const [tela, setTela] = useState<Tela>("menu");
  const [usuario, setUsuario] = useState<UsuarioConta | null>(null);
  const [csrf, setCsrf] = useState<string | null>(null);
  const [foto, setFoto] = useState<string | null>(null);
  const [contasDisponiveis, setContasDisponiveis] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mostrarSenha, setMostrarSenha] = useState(false);
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
    let ativo = true;
    void lerSessao().then(async (sessao) => {
      if (!ativo) {
        return;
      }
      setContasDisponiveis(sessao.contas_disponiveis);
      if (sessao.usuario && sessao.csrf) {
        guardarVisitante();
        aplicarPreferencias(sessao.usuario);
        aplicarSessao(sessao.usuario, sessao.csrf);
        if (sessao.usuario.tipo_avatar === "imagem") {
          trocarFoto(await carregarFoto());
        }
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
        setNome(sessao.usuario.nome_exibicao);
        setTela("perfil");
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

  async function aoSalvarNome() {
    if (!csrf) {
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
              <div>
                <p className="text-xs font-medium tracking-wide text-[#9f1239]">Meu Direito</p>
                <h2 id="titulo-conta" className="text-lg font-semibold">
                  {tituloDaTela(tela, usuario)}
                </h2>
              </div>
              <button type="button" onClick={fechar} className="grid h-11 w-11 place-items-center rounded-lg hover:bg-black/5 dark:hover:bg-white/10" aria-label="Fechar conta">
                <X size={18} />
              </button>
            </div>
            {tela === "entrar" || tela === "cadastrar" ? (
              <p className="mt-1 text-sm text-[#5c5c5c] dark:text-white/70">O conhecimento jurídico ao seu alcance.</p>
            ) : null}
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
                  <button type="button" className="text-sm underline" onClick={() => void avisoRecuperacao().then(setAviso).then(() => setTela("recuperar"))}>Esqueci minha senha</button>
                )}
                <button type="button" className="text-sm underline" onClick={() => abrirTela(tela === "entrar" ? "cadastrar" : "entrar")}>
                  {tela === "entrar" ? "Criar conta" : "Entrar"}
                </button>
                <button type="button" className="text-sm text-[#5c5c5c] underline dark:text-white/70" onClick={fechar}>Continuar sem entrar</button>
              </form>
            )}
            {tela === "recuperar" && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>{aviso ?? "O envio de e-mail ainda não está configurado. A recuperação de senha permanece pendente."}</p>
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
                  A importação do histórico deste navegador para a conta ainda não está disponível. Nada é importado automaticamente.
                </p>
              </div>
            )}
            {tela === "conta" && usuario && (
              <div className="mt-4 grid gap-3 text-sm leading-6">
                <p>E-mail da conta: {usuario.email}</p>
                <p>A troca de e-mail fica pendente até existir um fluxo de confirmação. O endereço não pode ser alterado por aqui.</p>
                <p>O histórico de pesquisa continua neste navegador e não é sincronizado entre aparelhos.</p>
                <button type="button" className="text-left underline" onClick={() => abrirTela("perfil")}>Editar perfil e avatar</button>
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
  return usuario ? usuario.nome_exibicao : "Conta";
}
