import { useEffect, useRef, useState } from "react";
import { conversar } from "../services/api.ts";
import { EVENTO_CONSENTIMENTO, permitirHistoricoVisitante, type EscolhaArmazenamento } from "../services/consentimento.ts";
import {
  apagarHistoricoLocal,
  criarMensagem,
  lerConversaAtiva,
  lerConversas,
  salvarConversaAtiva,
  salvarConversas,
  tituloDaPergunta,
} from "../services/conversas.ts";
import {
  ErroHistorico,
  apagarConversa,
  apagarHistoricoConta,
  importarConversas,
  listarConversas,
  obterConversa,
  perguntarConta,
  renomearConversa,
} from "../services/historico.ts";
import type { Conversa, Perfil, TipoDocumento } from "../types/chat.ts";

export interface OpcoesEnvio {
  titulo?: string;
  tipoDocumento?: TipoDocumento | null;
}

export interface ContaDoChat {
  autenticado: boolean;
  csrf: string | null;
  pronta: boolean;
}

const CHAVE_ADIAR = "meu-direito.importacao-adiada";

function ordenar(conversas: Conversa[]): Conversa[] {
  return [...conversas].sort((esquerda, direita) => {
    const a = Date.parse(direita.atualizadaEm || direita.criadaEm) || 0;
    const b = Date.parse(esquerda.atualizadaEm || esquerda.criadaEm) || 0;
    return a - b;
  });
}

function gravarLocais(conversas: Conversa[], ativa: string | null) {
  salvarConversas(conversas);
  salvarConversaAtiva(ativa);
}

export function useConversas(perfil: Perfil, conta: ContaDoChat) {
  const [conversas, setConversas] = useState<Conversa[]>([]);
  const [ativaId, setAtivaId] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [erroLista, setErroLista] = useState<string | null>(null);
  const [carregandoLista, setCarregandoLista] = useState(true);
  const [listaPronta, setListaPronta] = useState(false);
  const [origens, setOrigens] = useState<Set<string>>(new Set());
  const [importacaoAdiada, setImportacaoAdiada] = useState(() => sessionStorage.getItem(CHAVE_ADIAR) === "1");
  const [importando, setImportando] = useState(false);
  const bloqueio = useRef(false);
  const conversasRef = useRef(conversas);
  const ativaRef = useRef(ativaId);
  conversasRef.current = conversas;
  ativaRef.current = ativaId;
  const perfilAtual = useRef(perfil);
  const contaAtual = useRef(conta);
  const contaVista = useRef(conta);
  perfilAtual.current = perfil;
  contaAtual.current = conta;
  if (conta.pronta && (contaVista.current.autenticado !== conta.autenticado || contaVista.current.csrf !== conta.csrf || !contaVista.current.pronta)) {
    contaVista.current = conta;
    if (!conta.autenticado || !conta.csrf) {
      const locais = lerConversas().map((item) => ({ ...item, carregada: true }));
      setConversas(locais);
      const salva = lerConversaAtiva();
      setAtivaId(salva && locais.some((conversa) => conversa.id === salva) ? salva : null);
      setOrigens(new Set());
      setListaPronta(true);
      setCarregandoLista(false);
      setErroLista(null);
    } else {
      setConversas([]);
      setAtivaId(null);
      setListaPronta(false);
      setCarregandoLista(true);
      setErroLista(null);
    }
  }

  useEffect(() => {
    if (!conta.pronta) {
      return;
    }
    if (!conta.autenticado || !conta.csrf) {
      const locais = lerConversas().map((item) => ({ ...item, carregada: true }));
      setConversas(locais);
      const salva = lerConversaAtiva();
      setAtivaId(salva && locais.some((conversa) => conversa.id === salva) ? salva : null);
      setOrigens(new Set());
      setCarregandoLista(false);
      setListaPronta(true);
      setErroLista(null);
      return;
    }
    const csrf = conta.csrf;
    let cancelado = false;
    setConversas([]);
    setAtivaId(null);
    setCarregandoLista(true);
    setListaPronta(false);
    setErroLista(null);
    void listarConversas()
      .then((lista) => {
        if (cancelado) {
          return;
        }
        setConversas(ordenar(lista));
        setOrigens(new Set(lista.flatMap((item) => (item.origemLocal ? [item.origemLocal] : []))));
        setListaPronta(true);
      })
      .catch((falha: unknown) => {
        if (!cancelado) {
          setErroLista(falha instanceof Error ? falha.message : "Não foi possível carregar as conversas.");
        }
      })
      .finally(() => {
        if (!cancelado) {
          setCarregandoLista(false);
        }
      });
    return () => {
      cancelado = true;
      void csrf;
    };
  }, [conta.pronta, conta.autenticado, conta.csrf]);

  useEffect(() => {
    const aoMudar = (evento: Event) => {
      if (contaAtual.current.autenticado) {
        return;
      }
      const escolha = (evento as CustomEvent<EscolhaArmazenamento>).detail;
      if (escolha?.historicoVisitante && permitirHistoricoVisitante()) {
        gravarLocais(conversasRef.current, ativaRef.current);
        return;
      }
      if (escolha && !escolha.historicoVisitante) {
        setConversas([]);
        setAtivaId(null);
      }
    };
    window.addEventListener(EVENTO_CONSENTIMENTO, aoMudar);
    return () => window.removeEventListener(EVENTO_CONSENTIMENTO, aoMudar);
  }, []);

  const ativa = conversas.find((conversa) => conversa.id === ativaId) ?? null;
  const locaisPendentes = conta.autenticado
    ? lerConversas().filter((conversa) => conversa.mensagens.length > 0 && !origens.has(conversa.id))
    : [];

  function aplicar(proximas: Conversa[], proximaAtiva: string | null) {
    const ordenadas = contaAtual.current.autenticado ? ordenar(proximas) : proximas;
    setConversas(ordenadas);
    setAtivaId(proximaAtiva);
    if (!contaAtual.current.autenticado) {
      gravarLocais(ordenadas, proximaAtiva);
    }
  }

  function novaConversa() {
    setAtivaId(null);
    setErro(null);
    if (!contaAtual.current.autenticado) {
      salvarConversaAtiva(null);
    }
  }

  async function selecionarConversa(id: string) {
    setAtivaId(id);
    setErro(null);
    if (!contaAtual.current.autenticado) {
      salvarConversaAtiva(id);
      return;
    }
    const atual = conversas.find((conversa) => conversa.id === id);
    if (!atual || atual.carregada !== false) {
      return;
    }
    try {
      const completa = await obterConversa(id);
      setConversas((lista) => lista.map((conversa) => (conversa.id === id ? completa : conversa)));
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível abrir a conversa.");
    }
  }

  async function excluirConversa(id: string) {
    const csrf = contaAtual.current.csrf;
    if (contaAtual.current.autenticado && csrf) {
      try {
        await apagarConversa(csrf, id);
      } catch (falha) {
        setErro(falha instanceof Error ? falha.message : "Não foi possível excluir a conversa.");
        return;
      }
    }
    const proximas = conversas.filter((conversa) => conversa.id !== id);
    aplicar(proximas, ativaId === id ? null : ativaId);
    setErro(null);
  }

  async function excluirHistorico() {
    const csrf = contaAtual.current.csrf;
    if (contaAtual.current.autenticado && csrf) {
      try {
        await apagarHistoricoConta(csrf);
      } catch (falha) {
        setErro(falha instanceof Error ? falha.message : "Não foi possível apagar o histórico da conta.");
        return;
      }
      setConversas([]);
      setAtivaId(null);
      setErro(null);
      return;
    }
    apagarHistoricoLocal();
    setConversas([]);
    setAtivaId(null);
    setErro(null);
  }

  async function renomear(id: string, titulo: string) {
    const limpo = titulo.replace(/\s+/g, " ").trim();
    if (!limpo) {
      return;
    }
    const csrf = contaAtual.current.csrf;
    if (contaAtual.current.autenticado && csrf) {
      const atualizada = await renomearConversa(csrf, id, limpo);
      setConversas((lista) =>
        ordenar(
          lista.map((conversa) =>
            conversa.id === id ? { ...conversa, titulo: atualizada.titulo, atualizadaEm: atualizada.atualizadaEm } : conversa,
          ),
        ),
      );
      return;
    }
    const proximas = conversas.map((conversa) =>
      conversa.id === id ? { ...conversa, titulo: limpo, atualizadaEm: new Date().toISOString() } : conversa,
    );
    aplicar(proximas, ativaId);
  }

  function adotar(conversa: Conversa, temporaria: string) {
    setConversas((lista) => ordenar([conversa, ...lista.filter((item) => item.id !== temporaria && item.id !== conversa.id)]));
    setAtivaId(conversa.id);
  }

  async function enviar(pergunta: string, opcoes?: OpcoesEnvio) {
    const texto = pergunta.trim();
    if (!texto || bloqueio.current) {
      return;
    }
    if (ativa && ativa.carregada === false) {
      setErro("A conversa ainda está carregando.");
      return;
    }
    bloqueio.current = true;
    setEnviando(true);
    setErro(null);

    const usuario = criarMensagem("usuario", texto);
    const idExistente = ativaId && conversas.some((conversa) => conversa.id === ativaId) ? ativaId : null;
    const id = idExistente ?? crypto.randomUUID();
    const conversaAtual = conversas.find((conversa) => conversa.id === idExistente);
    const tipoDocumento = opcoes?.tipoDocumento ?? conversaAtual?.tipoDocumento ?? null;
    const agora = new Date().toISOString();

    const proximas = !idExistente
      ? [
          {
            id,
            titulo: opcoes?.titulo ?? tituloDaPergunta(texto),
            criadaEm: agora,
            atualizadaEm: agora,
            carregada: true,
            mensagens: [usuario],
            tipoDocumento,
          },
          ...conversas,
        ]
      : conversas.map((conversa) =>
          conversa.id === id
            ? { ...conversa, tipoDocumento, atualizadaEm: agora, mensagens: [...conversa.mensagens, usuario] }
            : conversa,
        );
    aplicar(proximas, id);

    try {
      if (contaAtual.current.autenticado && contaAtual.current.csrf) {
        const salva = await perguntarConta({
          pergunta: texto,
          csrf: contaAtual.current.csrf,
          conversaId: conversaAtual?.naConta ? idExistente : null,
          titulo: opcoes?.titulo ?? tituloDaPergunta(texto),
          perfil: perfilAtual.current,
          tipoDocumento,
        });
        adotar(salva, id);
      } else {
        const resposta = await conversar({
          pergunta: texto,
          perfil: perfilAtual.current,
          tipoDocumento,
        });
        const agente = criarMensagem("agente", resposta.resposta, resposta.referencias);
        const comResposta = proximas.map((conversa) =>
          conversa.id === id ? { ...conversa, mensagens: [...conversa.mensagens, agente] } : conversa,
        );
        aplicar(comResposta, id);
      }
    } catch (falha) {
      if (falha instanceof ErroHistorico && falha.conversa) {
        adotar(falha.conversa, id);
      }
      setErro(falha instanceof Error ? falha.message : "Ocorreu um erro inesperado.");
    } finally {
      bloqueio.current = false;
      setEnviando(false);
    }
  }

  function dispensarImportacao() {
    sessionStorage.setItem(CHAVE_ADIAR, "1");
    setImportacaoAdiada(true);
  }

  async function importarLocais() {
    const csrf = contaAtual.current.csrf;
    if (!csrf || importando) {
      return;
    }
    setImportando(true);
    setErro(null);
    try {
      const resultado = await importarConversas(csrf, locaisPendentes);
      const lista = await listarConversas();
      setOrigens(new Set([...origens, ...resultado.origens, ...lista.flatMap((item) => (item.origemLocal ? [item.origemLocal] : []))]));
      setConversas(ordenar(lista));
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível importar as conversas.");
      throw falha;
    } finally {
      setImportando(false);
    }
  }

  return {
    conversas,
    ativa,
    enviando,
    erro,
    erroLista,
    carregandoLista,
    importacaoDisponivel: conta.autenticado && listaPronta && !importacaoAdiada && locaisPendentes.length > 0,
    importando,
    novaConversa,
    selecionarConversa,
    excluirConversa,
    excluirHistorico,
    renomear,
    dispensarImportacao,
    importarLocais,
    enviar,
  };
}
