import { useEffect, useState } from "react";
import { EVENTO_CONSENTIMENTO, gravarEscolha, lerEscolha, type EscolhaArmazenamento } from "../services/consentimento.ts";

export function PainelArmazenamento() {
  const [escolha, setEscolha] = useState<EscolhaArmazenamento | null>(lerEscolha);
  useEffect(() => {
    const atualizar = () => setEscolha(lerEscolha());
    window.addEventListener(EVENTO_CONSENTIMENTO, atualizar);
    return () => window.removeEventListener(EVENTO_CONSENTIMENTO, atualizar);
  }, []);
  return (
    <div className="grid gap-3 text-sm leading-6">
      <p>
        O cookie de sessão só nasce quando você entra na conta. Ele é necessário para manter essa conta e não pode ser desligado sem sair.
      </p>
      <p>
        Tema, perfil de linguagem e histórico de visitante ficam neste navegador apenas se você permitir. Recusar apaga essas cópias locais.
        Não apaga a conta nem as conversas já salvas nela.
      </p>
      {escolha && (
        <p>
          Escolha atual: {escolha.preferencias ? "tema e perfil podem ser lembrados" : "tema e perfil não são lembrados"};{" "}
          {escolha.historicoVisitante ? "o histórico de visitante pode ser guardado" : "o histórico de visitante não é guardado"}.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="min-h-11 rounded-full bg-[#9f1239] px-4 text-sm font-medium text-white"
          onClick={() => gravarEscolha({ preferencias: true, historicoVisitante: true })}
        >
          Guardar tema, perfil e histórico
        </button>
        <button
          type="button"
          className="min-h-11 rounded-full border border-black/15 px-4 text-sm dark:border-white/20"
          onClick={() => gravarEscolha({ preferencias: false, historicoVisitante: false })}
        >
          Somente o necessário
        </button>
      </div>
    </div>
  );
}
