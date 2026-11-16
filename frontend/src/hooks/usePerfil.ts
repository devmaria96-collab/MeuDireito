import { useEffect, useState } from "react";
import type { Perfil } from "../types/chat.ts";

const CHAVE_PERFIL = "meu-direito.perfil";

function perfilInicial(): Perfil {
  const salvo = localStorage.getItem(CHAVE_PERFIL);
  if (salvo === "estudante" || salvo === "profissional" || salvo === "cidadao") {
    return salvo;
  }
  return "cidadao";
}

export function usePerfil() {
  const [perfil, setPerfil] = useState<Perfil>(perfilInicial);

  useEffect(() => {
    localStorage.setItem(CHAVE_PERFIL, perfil);
  }, [perfil]);

  return { perfil, setPerfil };
}
