import { useEffect, useState } from "react";
import { CHAVE_PERFIL, EVENTO_CONSENTIMENTO, lerEscolha, permitirPreferencias } from "../services/consentimento.ts";
import type { Perfil } from "../types/chat.ts";

function perfilInicial(): Perfil {
  if (lerEscolha()?.preferencias === false) {
    return "cidadao";
  }
  const salvo = localStorage.getItem(CHAVE_PERFIL);
  if (salvo === "estudante" || salvo === "profissional" || salvo === "cidadao") {
    return salvo;
  }
  return "cidadao";
}

export function usePerfil() {
  const [perfil, setPerfil] = useState<Perfil>(perfilInicial);
  const [gravacao, setGravacao] = useState(0);

  useEffect(() => {
    const atualizar = () => setGravacao((valor) => valor + 1);
    window.addEventListener(EVENTO_CONSENTIMENTO, atualizar);
    return () => window.removeEventListener(EVENTO_CONSENTIMENTO, atualizar);
  }, []);

  useEffect(() => {
    if (permitirPreferencias()) {
      localStorage.setItem(CHAVE_PERFIL, perfil);
    }
  }, [perfil, gravacao]);

  return { perfil, setPerfil };
}
