import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

interface PropriedadesEntrada {
  enviando: boolean;
  solto?: boolean;
  experimental?: boolean;
  onEnviar: (pergunta: string) => void;
}

export function ChatInput({ enviando, solto = false, experimental = false, onEnviar }: PropriedadesEntrada) {
  const [texto, setTexto] = useState("");
  const [celular, setCelular] = useState(false);
  const campo = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const consulta = window.matchMedia("(max-width: 767px)");
    const atualizar = () => setCelular(consulta.matches);
    atualizar();
    consulta.addEventListener("change", atualizar);
    return () => consulta.removeEventListener("change", atualizar);
  }, []);

  useEffect(() => {
    const elemento = campo.current;
    if (!elemento) {
      return;
    }
    elemento.style.height = "0px";
    elemento.style.height = `${Math.min(elemento.scrollHeight, 160)}px`;
  }, [texto]);

  function enviar() {
    const pergunta = texto.trim();
    if (!pergunta || enviando) {
      return;
    }
    onEnviar(pergunta);
    setTexto("");
  }

  function aoTeclar(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (celular || evento.key !== "Enter" || evento.shiftKey || evento.nativeEvent.isComposing) {
      return;
    }
    evento.preventDefault();
    enviar();
  }

  return (
    <form
      className={
        solto
          ? "w-full"
          : "border-t border-black/10 bg-white/95 px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur sm:px-6 dark:border-white/10 dark:bg-black/80"
      }
      onSubmit={(evento) => {
        evento.preventDefault();
        enviar();
      }}
    >
      <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-[28px] border border-black/10 bg-white/95 p-2 shadow-lg dark:border-white/15 dark:bg-black/75">
        <label htmlFor="pergunta" className="sr-only">
          Pergunta para o Meu Direito
        </label>
        <textarea
          id="pergunta"
          ref={campo}
          rows={1}
          value={texto}
          disabled={enviando}
          enterKeyHint={celular ? "enter" : "send"}
          onChange={(evento) => setTexto(evento.target.value)}
          onKeyDown={aoTeclar}
          placeholder="Pesquise um direito, uma lei ou um tema jurídico..."
          className="max-h-40 min-h-11 w-0 flex-1 resize-none bg-transparent px-3 py-2 text-base text-black outline-none placeholder:text-muted disabled:opacity-60 sm:text-[15px] dark:text-white"
        />
        <button
          type="submit"
          disabled={enviando || texto.trim().length === 0}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#9f1239] text-white transition hover:bg-[#7f0e2d] disabled:cursor-not-allowed disabled:bg-black/10 disabled:text-black/35 dark:disabled:bg-white/15 dark:disabled:text-white/40"
          aria-label={enviando ? "Enviando pergunta" : "Enviar pergunta"}
        >
          <ArrowUp size={18} />
        </button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs leading-5 text-muted">
        {celular ? "Use o botão para enviar. " : "Enter envia. Shift + Enter quebra a linha. "}
        Ao enviar, esta pergunta e o perfil de linguagem vão para o Google Gemini. As mensagens anteriores não vão junto.
        {experimental && " A resposta usa inteligência artificial e pode errar. Não escreva dado pessoal, informação sigilosa ou documento jurídico real."}
      </p>
    </form>
  );
}
