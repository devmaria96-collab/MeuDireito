import { useEffect, useRef, type ReactNode } from "react";
import { SUGESTOES } from "../conteudo.ts";
import type { Mensagem } from "../types/chat.ts";
import { ChatMessage } from "./ChatMessage.tsx";

interface PropriedadesJanela {
  mensagens: Mensagem[];
  enviando: boolean;
  onSugestao: (pergunta: string) => void;
  children?: ReactNode;
}

export function ChatWindow({ mensagens, enviando, onSugestao, children }: PropriedadesJanela) {
  const painel = useRef<HTMLDivElement>(null);
  const fim = useRef<HTMLDivElement>(null);
  const seguir = useRef(true);

  function aoRolar() {
    const area = painel.current;
    if (!area) {
      return;
    }
    seguir.current = area.scrollHeight - area.scrollTop - area.clientHeight < 96;
  }

  useEffect(() => {
    if (enviando) {
      seguir.current = true;
    }
  }, [enviando]);

  useEffect(() => {
    if (!seguir.current) {
      return;
    }
    const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    fim.current?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "end" });
  }, [mensagens, enviando]);

  if (mensagens.length === 0 && !enviando) {
    return (
      <div className="flex flex-1 items-center justify-center overflow-y-auto px-4 py-8">
        <div className="w-full max-w-2xl surgir">
          <h2 className="text-center text-4xl font-medium tracking-tight text-black sm:text-5xl dark:text-white">
            Como posso ajudar?
          </h2>
          <p className="mt-3 text-center text-sm text-black/70 dark:text-white/75">
            O conhecimento jurídico ao seu alcance.
          </p>
          <div className="mt-8">{children}</div>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {SUGESTOES.map((sugestao) => (
              <button
                key={sugestao}
                type="button"
                onClick={() => onSugestao(sugestao)}
                className="min-h-11 max-w-full rounded-full border border-black/10 bg-white/80 px-4 py-2 text-left text-sm text-black hover:border-[#e10600] dark:border-white/15 dark:bg-black/55 dark:text-white"
              >
                {sugestao}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div ref={painel} onScroll={aoRolar} className="min-h-0 flex-1 overflow-y-auto px-3 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        {mensagens.map((mensagem) => (
          <ChatMessage key={mensagem.id} mensagem={mensagem} />
        ))}
        {enviando && (
          <div className="flex items-center gap-3 text-sm text-muted" role="status" aria-live="polite">
            <span className="flex h-8 items-center gap-1 rounded-full bg-black/70 px-3" aria-hidden="true">
              <span className="h-1.5 w-1.5 motion-safe:animate-pulse rounded-full bg-gold" />
              <span className="h-1.5 w-1.5 motion-safe:animate-pulse rounded-full bg-gold [animation-delay:150ms]" />
              <span className="h-1.5 w-1.5 motion-safe:animate-pulse rounded-full bg-gold [animation-delay:300ms]" />
            </span>
            Meu Direito está escrevendo...
          </div>
        )}
        <div ref={fim} />
      </div>
    </div>
  );
}
