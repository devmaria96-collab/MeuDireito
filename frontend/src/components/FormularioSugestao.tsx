import { useState } from "react";
import { enviarSugestao } from "../services/sugestao.ts";

export function FormularioSugestao({ onFechar }: { onFechar: () => void }) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviada, setEnviada] = useState(false);
  const [enviando, setEnviando] = useState(false);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4" role="presentation">
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-sugestao"
        className="w-full max-w-md rounded-2xl bg-white p-5 text-black dark:bg-black dark:text-white"
        onSubmit={(evento) => {
          evento.preventDefault();
          setEnviando(true);
          setErro(null);
          void enviarSugestao(texto)
            .then(() => setEnviada(true))
            .catch((falha: unknown) => setErro(falha instanceof Error ? falha.message : "Não foi possível enviar a sugestão."))
            .finally(() => setEnviando(false));
        }}
      >
        <h2 id="titulo-sugestao" className="text-lg font-semibold">
          Enviar sugestão
        </h2>
        <p className="mt-2 text-sm leading-6">
          Escreva só a ideia de melhoria. Não inclua nome, e-mail, telefone, dado pessoal ou documento. A resposta da pesquisa não vai junto.
        </p>
        {enviada ? (
          <p className="mt-4 text-sm" role="status">
            Sugestão recebida. Ela não identifica quem escreveu.
          </p>
        ) : (
          <>
            <label className="mt-4 block text-sm" htmlFor="texto-sugestao">
              Sugestão
            </label>
            <textarea
              id="texto-sugestao"
              required
              minLength={5}
              maxLength={500}
              value={texto}
              onChange={(evento) => setTexto(evento.target.value)}
              className="mt-2 min-h-28 w-full rounded-2xl border border-black/15 bg-white px-3 py-2 text-sm text-black outline-none focus:border-[#e10600] dark:border-white/15 dark:bg-black dark:text-white"
            />
            {erro && (
              <p className="mt-2 text-sm" role="alert">
                {erro}
              </p>
            )}
            <button type="submit" disabled={enviando} className="mt-4 min-h-11 w-full rounded-full bg-[#9f1239] text-sm font-medium text-white disabled:opacity-60">
              Enviar sugestão
            </button>
          </>
        )}
        <button type="button" className="mt-3 min-h-11 text-sm underline" onClick={onFechar}>
          Fechar
        </button>
      </form>
    </div>
  );
}
