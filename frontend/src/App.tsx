import { AlertCircle, Moon, Scale, Sun, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { AvisoArmazenamento } from "./components/AvisoArmazenamento.tsx";
import { MenuConta } from "./components/MenuConta.tsx";
import { PaginaLegal } from "./components/PaginaLegal.tsx";
import { RodapeLegal } from "./components/RodapeLegal.tsx";
import { FormularioSugestao } from "./components/FormularioSugestao.tsx";
import { BotaoMenu, Sidebar } from "./components/Sidebar.tsx";
import { ConsultaLegislacao } from "./components/ConsultaLegislacao.tsx";
import { ChatInput } from "./components/ChatInput.tsx";
import { ChatWindow } from "./components/ChatWindow.tsx";
import { SeletorPerfil } from "./components/SeletorPerfil.tsx";
import { useConversas } from "./hooks/useConversas.ts";
import { usePerfil } from "./hooks/usePerfil.ts";
import { useTema } from "./hooks/useTema.ts";
import { obterFontesOficiais, URL_API, verificarBackend, type CatalogoFontes } from "./services/api.ts";
import { salvarPerfil } from "./services/conta.ts";

type Conexao = "verificando" | "conectado" | "indisponivel";

function lerDocumento(): "privacidade" | "termos" | null {
  const valor = new URLSearchParams(window.location.search).get("documento");
  return valor === "privacidade" || valor === "termos" ? valor : null;
}

export default function App() {
  const { tema, definirTema } = useTema();
  const csrfConta = useRef<string | null>(null);
  const [tokenRedefinicao, setTokenRedefinicao] = useState<string | null>(null);
  const [tokenConfirmacao, setTokenConfirmacao] = useState<string | null>(null);
  const [conta, setConta] = useState<{ autenticado: boolean; csrf: string | null; pronta: boolean }>({
    autenticado: false,
    csrf: null,
    pronta: false,
  });
  const { perfil, setPerfil } = usePerfil();
  const {
    conversas,
    ativa,
    enviando,
    erro,
    erroLista,
    carregandoLista,
    importacaoDisponivel,
    importando,
    novaConversa,
    selecionarConversa,
    excluirConversa,
    excluirHistorico,
    renomear,
    dispensarImportacao,
    importarLocais,
    enviar,
  } = useConversas(perfil, conta);
  const [menuAberto, setMenuAberto] = useState(false);
  const [recolhida, setRecolhida] = useState(false);
  const [configAberta, setConfigAberta] = useState(false);
  const [consultaAberta, setConsultaAberta] = useState(false);
  const [fontesAbertas, setFontesAbertas] = useState(false);
  const [fontes, setFontes] = useState<CatalogoFontes | null>(null);
  const [erroFontes, setErroFontes] = useState<string | null>(null);
  const [exclusaoId, setExclusaoId] = useState<string | null>(null);
  const [renomearId, setRenomearId] = useState<string | null>(null);
  const [tituloEdicao, setTituloEdicao] = useState("");
  const [erroRenomear, setErroRenomear] = useState<string | null>(null);
  const [confirmarHistorico, setConfirmarHistorico] = useState(false);
  const [erroImportacao, setErroImportacao] = useState<string | null>(null);
  const [conexao, setConexao] = useState<Conexao>("verificando");
  const [documento, setDocumento] = useState<"privacidade" | "termos" | null>(lerDocumento);
  const [experimental, setExperimental] = useState(false);
  const [sugestaoAberta, setSugestaoAberta] = useState(false);

  function abrirDocumento(pagina: "privacidade" | "termos") {
    const parametros = new URLSearchParams(window.location.search);
    parametros.set("documento", pagina);
    const consulta = parametros.toString();
    window.history.pushState({}, "", `${window.location.pathname}?${consulta}`);
    setDocumento(pagina);
  }

  function fecharDocumento() {
    const parametros = new URLSearchParams(window.location.search);
    parametros.delete("documento");
    const consulta = parametros.toString();
    window.history.pushState({}, "", consulta ? `${window.location.pathname}?${consulta}` : window.location.pathname);
    setDocumento(null);
  }

  useEffect(() => {
    let ativo = true;
    void fetch(`${URL_API}/modo`, { credentials: "include" })
      .then(async (resposta) => (resposta.ok ? ((await resposta.json()) as { demonstracao?: unknown }) : null))
      .then((corpo) => {
        if (ativo) {
          setExperimental(corpo?.demonstracao === true);
        }
      })
      .catch(() => {
        if (ativo) {
          setExperimental(false);
        }
      });
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    const aoVoltar = () => setDocumento(lerDocumento());
    window.addEventListener("popstate", aoVoltar);
    return () => window.removeEventListener("popstate", aoVoltar);
  }, []);

  useEffect(() => {
    const parametros = new URLSearchParams(window.location.search);
    const token = parametros.get("redefinir");
    const confirmacao = parametros.get("confirmar");
    if (!token && !confirmacao) {
      return;
    }
    if (token) {
      setTokenRedefinicao(token);
      parametros.delete("redefinir");
    }
    if (confirmacao) {
      setTokenConfirmacao(confirmacao);
      parametros.delete("confirmar");
    }
    const restante = parametros.toString();
    window.history.replaceState({}, "", restante ? `${window.location.pathname}?${restante}` : window.location.pathname);
  }, []);

  useEffect(() => {
    let ativo = true;
    void verificarBackend().then((ok) => {
      if (ativo) {
        setConexao(ok ? "conectado" : "indisponivel");
      }
    });
    return () => {
      ativo = false;
    };
  }, []);

  useEffect(() => {
    if (!fontesAbertas || fontes) {
      return;
    }
    let ativo = true;
    void obterFontesOficiais()
      .then((catalogo) => {
        if (ativo) {
          setFontes(catalogo);
        }
      })
      .catch(() => {
        if (ativo) {
          setErroFontes("Não foi possível carregar as fontes oficiais agora.");
        }
      });
    return () => {
      ativo = false;
    };
  }, [fontesAbertas, fontes]);

  useEffect(() => {
    const janela = window.visualViewport;
    if (!janela) {
      return;
    }
    const ajustar = () => {
      document.documentElement.style.setProperty("--altura-app", `${janela.height}px`);
    };
    ajustar();
    janela.addEventListener("resize", ajustar);
    janela.addEventListener("scroll", ajustar);
    return () => {
      janela.removeEventListener("resize", ajustar);
      janela.removeEventListener("scroll", ajustar);
    };
  }, []);

  useEffect(() => {
    const consulta = window.matchMedia("(min-width: 768px)");
    const fechar = () => {
      if (consulta.matches) {
        setMenuAberto(false);
      }
    };
    consulta.addEventListener("change", fechar);
    return () => consulta.removeEventListener("change", fechar);
  }, []);

  useEffect(() => {
    function fecharComEsc(evento: KeyboardEvent) {
      if (evento.key !== "Escape") {
        return;
      }
      setMenuAberto(false);
      setConfigAberta(false);
      setConsultaAberta(false);
      setFontesAbertas(false);
      setExclusaoId(null);
      setConfirmarHistorico(false);
    }
    window.addEventListener("keydown", fecharComEsc);
    return () => window.removeEventListener("keydown", fecharComEsc);
  }, []);

  function mudarPerfil(proximo: typeof perfil) {
    setPerfil(proximo);
    if (csrfConta.current) {
      void salvarPerfil(csrfConta.current, { perfil_juridico: proximo }).catch(() => undefined);
    }
  }

  function mudarTema() {
    const proximo = tema === "escuro" ? "claro" : "escuro";
    definirTema(proximo);
    if (csrfConta.current) {
      void salvarPerfil(csrfConta.current, { tema: proximo }).catch(() => undefined);
    }
  }

  function escolherConversa(id: string) {
    selecionarConversa(id);
    setMenuAberto(false);
  }

  function comecarConversa() {
    novaConversa();
    setMenuAberto(false);
  }

  const conversaExclusao = conversas.find((conversa) => conversa.id === exclusaoId);

  return (
    <div className="flex h-[var(--altura-app,100dvh)] overflow-hidden bg-black text-black dark:text-white">
      <Sidebar
        conversas={conversas}
        ativaId={ativa?.id ?? null}
        abertaNoCelular={menuAberto}
        recolhida={recolhida}
        onNova={comecarConversa}
        onSelecionar={escolherConversa}
        onPedirExclusao={setExclusaoId}
        onPedirRenomear={(id) => {
          const conversa = conversas.find((item) => item.id === id);
          setTituloEdicao(conversa?.titulo ?? "");
          setErroRenomear(null);
          setRenomearId(id);
        }}
        carregando={carregandoLista}
        erroLista={erroLista}
        onConsultar={() => {
          setConsultaAberta(true);
          setMenuAberto(false);
        }}
        onFontes={() => {
          setFontesAbertas(true);
          setMenuAberto(false);
        }}
        onConfiguracoes={() => {
          setConfigAberta(true);
          setMenuAberto(false);
        }}
        onAlternarRecolhimento={() => setRecolhida((atual) => !atual)}
        onFecharCelular={() => setMenuAberto(false)}
      />

      <main className="palco flex min-w-0 flex-1 flex-col" {...(menuAberto ? { inert: true } : {})}>
        <header className="flex h-14 shrink-0 items-center gap-2 bg-transparent px-2 sm:px-4">
          <BotaoMenu aberto={menuAberto} onAbrir={() => setMenuAberto(true)} />
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#9f1239] text-white md:hidden" aria-hidden="true">
            <Scale size={16} />
          </span>
          <h1 className="min-w-0 truncate text-sm font-semibold tracking-tight md:sr-only">Meu Direito</h1>
          <div className="ml-auto flex shrink-0 items-center gap-1">
            <p
              className="flex items-center gap-2 text-xs text-muted"
              role="status"
              aria-label={
                conexao === "conectado"
                  ? "Backend conectado"
                  : conexao === "indisponivel"
                    ? "Backend indisponível"
                    : "Verificando backend"
              }
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  conexao === "conectado" ? "bg-white ring-1 ring-black/40 dark:ring-white" : conexao === "indisponivel" ? "bg-[#e10600]" : "bg-white/40"
                }`}
                aria-hidden="true"
              />
              <span className="hidden sm:inline">
                {conexao === "conectado" && "Conectado"}
                {conexao === "indisponivel" && "Sem conexão"}
                {conexao === "verificando" && "Verificando"}
              </span>
            </p>
            <MenuConta
              perfil={perfil}
              tema={tema}
              tokenRedefinicao={tokenRedefinicao}
              tokenConfirmacao={tokenConfirmacao}
              onAbrirDocumento={abrirDocumento}
              onTokenConsumido={() => {
                setTokenRedefinicao(null);
                setTokenConfirmacao(null);
              }}
              onPerfil={setPerfil}
              onTema={definirTema}
              onSessao={(usuario, csrf) => {
                csrfConta.current = csrf;
                setConta({ autenticado: Boolean(usuario && csrf), csrf, pronta: true });
              }}
            />
            <button
              type="button"
              onClick={mudarTema}
              className="grid h-11 w-11 place-items-center rounded-full text-black hover:bg-black/5 dark:text-white dark:hover:bg-white/10"
              aria-label={tema === "escuro" ? "Ativar tema claro" : "Ativar tema escuro"}
            >
              {tema === "escuro" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        <AvisoArmazenamento />

        {ativa?.carregada === false ? (
          <div className="flex min-h-0 flex-1 items-center justify-center px-6 text-center text-sm text-muted" role="status">
            {erro ?? "Carregando conversa…"}
          </div>
        ) : (ativa?.mensagens.length ?? 0) === 0 && !enviando ? (
          <ChatWindow
            mensagens={[]}
            enviando={false}
            onSugestao={(pergunta) => void enviar(pergunta, { titulo: pergunta })}
          >
            <SeletorPerfil perfil={perfil} onMudar={mudarPerfil} solto />
            <ChatInput enviando={enviando} solto experimental={experimental} onEnviar={(pergunta) => void enviar(pergunta)} />
            <RodapeLegal onAbrir={abrirDocumento} experimental={experimental} onSugestao={() => setSugestaoAberta(true)} />
          </ChatWindow>
        ) : (
          <>
            <ChatWindow
              mensagens={ativa?.mensagens ?? []}
              enviando={enviando}
              onSugestao={(pergunta) => void enviar(pergunta, { titulo: pergunta })}
            />

            {erro && (
              <div
                role="alert"
                className="mx-auto mb-2 flex w-[min(100%-1.5rem,48rem)] items-start gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-400/30 dark:bg-red-950/40 dark:text-red-100"
              >
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
                <p>{erro}</p>
              </div>
            )}

            <div className="px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-6">
              <div className="mx-auto w-full max-w-3xl">
                <SeletorPerfil perfil={perfil} onMudar={mudarPerfil} solto />
                <ChatInput enviando={enviando} solto experimental={experimental} onEnviar={(pergunta) => void enviar(pergunta)} />
                <RodapeLegal onAbrir={abrirDocumento} experimental={experimental} onSugestao={() => setSugestaoAberta(true)} />
              </div>
            </div>
          </>
        )}
      </main>

      {configAberta && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-config"
            className="max-h-[min(90dvh,40rem)] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 id="titulo-config" className="text-lg font-semibold">
                Privacidade
              </h2>
              <button
                type="button"
                onClick={() => setConfigAberta(false)}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/10"
                aria-label="Fechar configurações"
              >
                <X size={18} />
              </button>
            </div>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-ink dark:text-slate-200">
              <li>Sem conta, o histórico fica só neste navegador e pode conter dados sensíveis.</li>
              <li>Entrar não apaga esse histórico e não o envia para a conta. A importação só ocorre se você confirmar.</li>
              <li>Na conta, as conversas ficam salvas e aparecem nos aparelhos em que você entrar.</li>
              <li>Apagar o histórico da conta não remove a cópia que continua só neste navegador.</li>
              <li>Cada pergunta segue isolada. O agente recebe somente a pergunta atual da conversa selecionada.</li>
              <li>Não informe CPF, endereço ou documentos se isso não for indispensável.</li>
              <li>Ao enviar, a pergunta atual vai ao Google Gemini. As mensagens anteriores não vão junto.</li>
              <li>A chave do Gemini permanece somente no backend.</li>
              <li>O login é opcional. Esta instalação não declara conformidade com a LGPD.</li>
              <li>API local: {URL_API}</li>
            </ul>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <button type="button" className="min-h-11 underline" onClick={() => abrirDocumento("privacidade")}>
                Política de Privacidade
              </button>
              <button type="button" className="min-h-11 underline" onClick={() => abrirDocumento("termos")}>
                Termos de Uso
              </button>
            </div>
            <button
              type="button"
              onClick={() => setConfirmarHistorico(true)}
              className="mt-5 rounded-xl border border-red-300 px-4 py-2 text-sm text-red-700 hover:bg-red-50 dark:border-red-400/40 dark:text-red-200 dark:hover:bg-red-950/40"
            >
              Apagar todo o histórico
            </button>
          </div>
        </div>
      )}

      {consultaAberta && <ConsultaLegislacao perfil={perfil} experimental={experimental} onFechar={() => setConsultaAberta(false)} />}

      {sugestaoAberta && <FormularioSugestao onFechar={() => setSugestaoAberta(false)} />}

      {fontesAbertas && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-fontes"
            className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 id="titulo-fontes" className="text-lg font-semibold">
                Fontes oficiais
              </h2>
              <button
                type="button"
                onClick={() => setFontesAbertas(false)}
                className="grid h-11 w-11 shrink-0 place-items-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/10"
                aria-label="Fechar fontes oficiais"
              >
                <X size={18} />
              </button>
            </div>
            <p className="mt-3 text-sm leading-6 text-ink dark:text-slate-200">
              {fontes?.aviso ??
                "O Meu Direito ainda não consulta legislação ou tribunais em tempo real. Nenhum artigo ou decisão é confirmado automaticamente."}
            </p>
            {erroFontes && <p className="mt-3 text-sm text-red-700 dark:text-red-200">{erroFontes}</p>}
            <ul className="mt-4 space-y-3 text-sm">
              {fontes?.fontes.map((fonte) => (
                <li key={fonte.url}>
                  <a
                    href={fonte.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="font-medium break-words text-[#9f1239] underline dark:text-[#ff8a8a]"
                  >
                    {fonte.nome}
                  </a>
                  <p className="break-words text-ink/80 dark:text-slate-300">{fonte.descricao}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {conversaExclusao && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-exclusao"
            className="max-h-[min(90dvh,40rem)] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <h2 id="titulo-exclusao" className="text-lg font-semibold">
              Excluir conversa?
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink dark:text-slate-200">
              {conta.autenticado
                ? `“${conversaExclusao.titulo}” será removida da sua conta. Essa ação não pode ser desfeita.`
                : `“${conversaExclusao.titulo}” será removida deste navegador. Essa ação não pode ser desfeita.`}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setExclusaoId(null)}
                className="rounded-xl px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => {
                  excluirConversa(conversaExclusao.id);
                  setExclusaoId(null);
                }}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmarHistorico && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-historico"
            className="max-h-[min(90dvh,40rem)] w-full max-w-md overflow-y-auto rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <h2 id="titulo-historico" className="text-lg font-semibold">
              Apagar todo o histórico?
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink dark:text-slate-200">
              {conta.autenticado
                ? "As conversas da sua conta serão excluídas. A cópia que permanece só neste navegador não é apagada."
                : "Todas as conversas salvas neste navegador serão excluídas."}
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmarHistorico(false)}
                className="rounded-xl px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => {
                  excluirHistorico();
                  setConfirmarHistorico(false);
                  setConfigAberta(false);
                }}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
              >
                Apagar
              </button>
            </div>
          </div>
        </div>
      )}

      {renomearId && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-renomear"
            className="w-full max-w-md rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <h2 id="titulo-renomear" className="text-lg font-semibold">
              Renomear conversa
            </h2>
            <input
              value={tituloEdicao}
              onChange={(evento) => setTituloEdicao(evento.target.value)}
              maxLength={80}
              className="mt-4 w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm dark:border-white/15 dark:bg-black"
              aria-label="Novo título"
            />
            {erroRenomear && <p className="mt-2 text-sm text-[#9f1239]">{erroRenomear}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setRenomearId(null)} className="rounded-xl px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10">
                Cancelar
              </button>
              <button
                type="button"
                onClick={() => {
                  void renomear(renomearId, tituloEdicao)
                    .then(() => setRenomearId(null))
                    .catch((falha: unknown) => setErroRenomear(falha instanceof Error ? falha.message : "Não foi possível renomear."));
                }}
                className="rounded-xl bg-[#9f1239] px-4 py-2 text-sm font-medium text-white"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}

      {documento && <PaginaLegal pagina={documento} onFechar={fecharDocumento} />}

      {importacaoDisponivel && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-navy/50 p-4" role="presentation">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="titulo-importacao"
            className="w-full max-w-md rounded-2xl bg-white p-5 text-navy shadow-xl dark:bg-navy dark:text-white"
          >
            <h2 id="titulo-importacao" className="text-lg font-semibold">
              Conversas deste navegador
            </h2>
            <p className="mt-2 text-sm leading-6 text-ink dark:text-slate-200">
              Você possui conversas salvas neste navegador. Deseja adicioná-las à sua conta?
            </p>
            <p className="mt-2 text-sm leading-6 text-ink dark:text-slate-200">
              A cópia deste navegador só é removida se você apagá-la nas configurações, depois de a importação terminar.
            </p>
            {erroImportacao && <p className="mt-2 text-sm text-[#9f1239]">{erroImportacao}</p>}
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                onClick={dispensarImportacao}
                className="rounded-xl px-4 py-2 text-sm hover:bg-slate-100 dark:hover:bg-white/10"
              >
                Agora não
              </button>
              <button
                type="button"
                disabled={importando}
                onClick={() => {
                  setErroImportacao(null);
                  void importarLocais().catch((falha: unknown) => {
                    setErroImportacao(falha instanceof Error ? falha.message : "Não foi possível importar as conversas.");
                  });
                }}
                className="rounded-xl bg-[#9f1239] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
              >
                {importando ? "Importando…" : "Importar conversas"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
