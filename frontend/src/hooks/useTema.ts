import { useEffect, useState } from "react";

const CHAVE_TEMA = "meu-ia.tema";

export type Tema = "claro" | "escuro";

function temaInicial(): Tema {
  const salvo = localStorage.getItem(CHAVE_TEMA);
  return salvo === "escuro" ? "escuro" : "claro";
}

export function useTema() {
  const [tema, setTema] = useState<Tema>(temaInicial);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", tema === "escuro");
    localStorage.setItem(CHAVE_TEMA, tema);
  }, [tema]);

  function alternarTema() {
    setTema((atual) => (atual === "escuro" ? "claro" : "escuro"));
  }

  function definirTema(proximo: Tema) {
    setTema(proximo);
  }

  return { tema, alternarTema, definirTema };
}
