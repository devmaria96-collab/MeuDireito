import { useEffect, useState } from "react";
import { adiarEscolha, escolhaAdiada, EVENTO_CONSENTIMENTO, lerEscolha } from "../services/consentimento.ts";
import { PainelArmazenamento } from "./PainelArmazenamento.tsx";

export function AvisoArmazenamento() {
  const [visivel, setVisivel] = useState(() => lerEscolha() === null && !escolhaAdiada());
  const [detalhes, setDetalhes] = useState(false);

  useEffect(() => {
    const atualizar = () => setVisivel(lerEscolha() === null && !escolhaAdiada());
    window.addEventListener(EVENTO_CONSENTIMENTO, atualizar);
    return () => window.removeEventListener(EVENTO_CONSENTIMENTO, atualizar);
  }, []);

  if (!visivel) {
    return null;
  }

  return (
    <section className="mx-3 mt-2 rounded-2xl border border-black/10 bg-white p-3 text-sm leading-6 text-black shadow-sm sm:mx-6 dark:border-white/15 dark:bg-black dark:text-white">
      <h2 className="font-semibold">Armazenamento neste navegador</h2>
      <p className="mt-1 text-[#5c5c5c] dark:text-white/70">
        A pesquisa não exige conta. Enquanto você não escolher, o que já está salvo continua aqui, e as conversas novas de visitante não são gravadas.
      </p>
      {detalhes ? (
        <div className="mt-3">
          <PainelArmazenamento />
        </div>
      ) : (
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" className="min-h-11 rounded-full bg-[#9f1239] px-4 text-sm font-medium text-white" onClick={() => setDetalhes(true)}>
            Escolher
          </button>
          <button type="button" className="min-h-11 px-3 text-sm underline" onClick={adiarEscolha}>
            Decidir depois
          </button>
        </div>
      )}
    </section>
  );
}
