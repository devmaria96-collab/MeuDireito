import { useEffect, useRef, useState } from "react";
import { conversar } from "../services/api.ts";
import {
  apagarHistoricoLocal,
  criarMensagem,
  lerConversaAtiva,
  lerConversas,
  salvarConversaAtiva,
  salvarConversas,
  tituloDaPergunta,
} from "../services/conversas.ts";
import type { Conversa, Perfil, TipoDocumento } from "../types/chat.ts";

export interface OpcoesEnvio {
  titulo?: string;
  tipoDocumento?: TipoDocumento | null;
}

export function useConversas(perfil: Perfil) {
  const [conversas, setConversas] = useState<Conversa[]>(lerConversas);
  const [ativaId, setAtivaId] = useState<string | null>(() => {
    const salva = lerConversaAtiva();
    return salva && lerConversas().some((conversa) => conversa.id === salva) ? salva : null;
  });
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const bloqueio = useRef(false);
  const perfilAtual = useRef(perfil);
  perfilAtual.current = perfil;

  useEffect(() => {
    salvarConversas(conversas);
  }, [conversas]);

  useEffect(() => {
    salvarConversaAtiva(ativaId);
  }, [ativaId]);

  const ativa = conversas.find((conversa) => conversa.id === ativaId) ?? null;

  function novaConversa() {
    setAtivaId(null);
    setErro(null);
  }

  function selecionarConversa(id: string) {
    setAtivaId(id);
    setErro(null);
  }

  function excluirConversa(id: string) {
    setConversas((atual) => atual.filter((conversa) => conversa.id !== id));
    setAtivaId((atual) => (atual === id ? null : atual));
    setErro(null);
  }

  function excluirHistorico() {
    apagarHistoricoLocal();
    setConversas([]);
    setAtivaId(null);
    setErro(null);
  }

  async function enviar(pergunta: string, opcoes?: OpcoesEnvio) {
    const texto = pergunta.trim();
    if (!texto || bloqueio.current) {
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

    setAtivaId(id);
    setConversas((atual) => {
      if (!idExistente) {
        const criada: Conversa = {
          id,
          titulo: opcoes?.titulo ?? tituloDaPergunta(texto),
          criadaEm: new Date().toISOString(),
          mensagens: [usuario],
          tipoDocumento,
        };
        return [criada, ...atual];
      }
      return atual.map((conversa) =>
        conversa.id === id
          ? { ...conversa, tipoDocumento, mensagens: [...conversa.mensagens, usuario] }
          : conversa,
      );
    });

    try {
      const resposta = await conversar({
        pergunta: texto,
        perfil: perfilAtual.current,
        tipoDocumento,
      });
      const agente = criarMensagem("agente", resposta.resposta, resposta.referencias);
      setConversas((atual) =>
        atual.map((conversa) =>
          conversa.id === id
            ? { ...conversa, mensagens: [...conversa.mensagens, agente] }
            : conversa,
        ),
      );
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Ocorreu um erro inesperado.");
    } finally {
      bloqueio.current = false;
      setEnviando(false);
    }
  }

  return {
    conversas,
    ativa,
    enviando,
    erro,
    novaConversa,
    selecionarConversa,
    excluirConversa,
    excluirHistorico,
    enviar,
  };
}
