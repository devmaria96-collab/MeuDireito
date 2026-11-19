export const EVENTO_CONSENTIMENTO = "md-consentimento";
export const CHAVE_TEMA = "meu-ia.tema";
export const CHAVE_PERFIL = "meu-direito.perfil";

const CHAVE = "meu-direito.consentimento";
const ADIAR = "meu-direito.consentimento-adiado";

export interface EscolhaArmazenamento {
  preferencias: boolean;
  historicoVisitante: boolean;
}

function escolhaValida(valor: unknown): valor is EscolhaArmazenamento {
  if (!valor || typeof valor !== "object") {
    return false;
  }
  const escolha = valor as Partial<EscolhaArmazenamento>;
  return typeof escolha.preferencias === "boolean" && typeof escolha.historicoVisitante === "boolean";
}

export function lerEscolha(): EscolhaArmazenamento | null {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) {
      return null;
    }
    const dados: unknown = JSON.parse(bruto);
    return escolhaValida(dados) ? dados : null;
  } catch {
    return null;
  }
}

export function escolhaAdiada(): boolean {
  return sessionStorage.getItem(ADIAR) === "1";
}

export function adiarEscolha(): void {
  sessionStorage.setItem(ADIAR, "1");
  window.dispatchEvent(new Event(EVENTO_CONSENTIMENTO));
}

export function permitirPreferencias(): boolean {
  return lerEscolha()?.preferencias === true;
}

export function permitirHistoricoVisitante(): boolean {
  return lerEscolha()?.historicoVisitante === true;
}

export function gravarEscolha(escolha: EscolhaArmazenamento): void {
  localStorage.setItem(CHAVE, JSON.stringify(escolha));
  sessionStorage.removeItem(ADIAR);
  if (!escolha.preferencias) {
    localStorage.removeItem(CHAVE_TEMA);
    localStorage.removeItem(CHAVE_PERFIL);
  }
  if (!escolha.historicoVisitante) {
    for (const chave of ["meu-direito.conversas", "meu-direito.conversa-ativa", "meu-ia.conversas", "meu-ia.conversa-ativa"]) {
      localStorage.removeItem(chave);
    }
  }
  window.dispatchEvent(new CustomEvent<EscolhaArmazenamento>(EVENTO_CONSENTIMENTO, { detail: escolha }));
}
