import { useEffect, useState } from "react";
import { CHAVE_TEMA, EVENTO_CONSENTIMENTO, lerEscolha, permitirPreferencias } from "../services/consentimento.ts";

export type Tema = "claro" | "escuro";

function temaInicial(): Tema {
  if (lerEscolha()?.preferencias === false) {
    return "claro";
  }
  const salvo = localStorage.getItem(CHAVE_TEMA);
  return salvo === "escuro" ? "escuro" : "claro";
}

export function useTema() {
  const [tema, setTema] = useState<Tema>(temaInicial);
  const [gravacao, setGravacao] = useState(0);

  useEffect(() => {
    const atualizar = () => setGravacao((valor) => valor + 1);
    window.addEventListener(EVENTO_CONSENTIMENTO, atualizar);
    return () => window.removeEventListener(EVENTO_CONSENTIMENTO, atualizar);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", tema === "escuro");
    if (permitirPreferencias()) {
      localStorage.setItem(CHAVE_TEMA, tema);
    }
  }, [tema, gravacao]);

  function alternarTema() {
    setTema((atual) => (atual === "escuro" ? "claro" : "escuro"));
  }

  function definirTema(proximo: Tema) {
    setTema(proximo);
  }

  return { tema, alternarTema, definirTema };
}
