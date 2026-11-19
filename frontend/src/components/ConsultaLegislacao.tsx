import { Search, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { consultarLegislacao, type ResultadoLegislacao } from "../services/api.ts";
import type { Perfil } from "../types/chat.ts";

const EXEMPLOS = [
  "O que diz o artigo 5º da Constituição Federal?",
  "Explique o artigo 6º do Código de Defesa do Consumidor.",
  "Quais são os direitos previstos na CLT sobre férias?",
] as const;

interface PropriedadesConsulta {
  perfil: Perfil;
  experimental?: boolean;
  onFechar: () => void;
}

export function ConsultaLegislacao({ perfil, experimental = false, onFechar }: PropriedadesConsulta) {
  const [consulta, setConsulta] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoLegislacao | null>(null);

  async function pesquisar(texto: string) {
    const pedido = texto.trim();
    if (!pedido || enviando) {
      return;
    }
    setConsulta(pedido);
    setEnviando(true);
    setErro(null);
    try {
      setResultado(await consultarLegislacao(pedido, perfil));
    } catch (falha) {
      setResultado(null);
      setErro(falha instanceof Error ? falha.message : "Não foi possível consultar a legislação.");
    } finally {
      setEnviando(false);
    }
  }

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    void pesquisar(consulta);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy/50 sm:items-center sm:p-4" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="titulo-legislacao"
        className="max-h-[100dvh] w-full overflow-y-auto rounded-t-2xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] text-navy shadow-xl sm:max-h-[85vh] sm:max-w-2xl sm:rounded-2xl sm:p-5 dark:bg-navy dark:text-white"
      >
        <div className="flex items-start justify-between gap-3">
          <h2 id="titulo-legislacao" className="text-lg font-semibold">
            Consultar legislação
          </h2>
          <button
            type="button"
            onClick={onFechar}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-lg hover:bg-slate-100 dark:hover:bg-white/10"
            aria-label="Fechar consulta de legislação"
          >
            <X size={18} />
          </button>
        </div>
        <p className="mt-2 text-sm leading-6 text-ink dark:text-slate-200">
          A leitura é feita no Portal da Legislação do Planalto. A pergunta não é enviada como formulário a esse site. Se o texto for encontrado, a explicação vai ao Google Gemini e fica separada do texto oficial.
          {experimental && " A explicação pode errar. Não escreva dado pessoal, informação sigilosa ou documento jurídico real."}
        </p>
        <form onSubmit={aoEnviar} className="mt-4 flex gap-2">
          <label htmlFor="consulta-legislacao" className="sr-only">
            Lei ou artigo
          </label>
          <input
            id="consulta-legislacao"
            value={consulta}
            onChange={(evento) => setConsulta(evento.target.value)}
            placeholder="Informe a lei e o artigo"
            className="min-h-11 min-w-0 flex-1 rounded-xl border border-slate-200 bg-surface px-3 py-2 text-base outline-none focus:border-gold sm:text-sm dark:border-white/10 dark:bg-deep"
          />
          <button
            type="submit"
            disabled={enviando || consulta.trim().length === 0}
            className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#9f1239] text-white disabled:cursor-not-allowed disabled:bg-black/15 disabled:text-black/40"
            aria-label="Consultar legislação"
          >
            <Search size={18} />
          </button>
        </form>
        <div className="mt-3 flex flex-col gap-2">
          {EXEMPLOS.map((exemplo) => (
            <button
              key={exemplo}
              type="button"
              disabled={enviando}
              onClick={() => void pesquisar(exemplo)}
              className="min-h-11 rounded-xl border border-slate-200 px-3 py-2 text-left text-sm leading-5 break-words hover:border-gold disabled:opacity-60 dark:border-white/10"
            >
              {exemplo}
            </button>
          ))}
        </div>
        {enviando && (
          <p className="mt-4 text-sm text-muted" role="status">
            Consultando o Planalto...
          </p>
        )}
        {erro && (
          <p role="alert" className="mt-4 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200">
            {erro}
          </p>
        )}
        {resultado && (
          <div className="mt-4 space-y-3 text-sm leading-6">
            <p className="rounded-xl bg-surface px-3 py-2 break-words dark:bg-deep">{resultado.aviso}</p>
            {resultado.verificada && resultado.texto_oficial && resultado.url && (
              <section className="rounded-2xl border border-gold/40 bg-gold/10 p-3">
                <h3 className="font-semibold break-words">
                  {resultado.norma}
                  {resultado.artigo ? `, artigo ${resultado.artigo}` : ""}
                  {resultado.numero
                    ? ` · nº ${resultado.numero}${resultado.ano ? `/${resultado.ano}` : ""}`
                    : resultado.ano
                      ? ` · ${resultado.ano}`
                      : ""}
                </h3>
                <p className="mt-1 text-xs text-muted">
                  Consulta em {resultado.consultado_em}. A vigência não foi confirmada só porque a página foi lida.
                  {resultado.tipo_texto === "compilado"
                    ? " Página compilada ou consolidada."
                    : " Não foi confirmado se a página é o texto original ou uma consolidação."}
                  {resultado.situacao === "norma_revogada" ? " A página indica revogação da norma." : ""}
                  {resultado.situacao === "dispositivo_revogado" || resultado.situacao === "indicio_revogacao"
                    ? " O artigo consultado está indicado como revogado."
                    : ""}
                  {resultado.situacao === "dispositivo_alterado" || resultado.situacao === "indicio_alteracao"
                    ? " O caput tem nota de alteração."
                    : ""}
                  {resultado.situacao === "dispositivo_incluido" ? " O caput tem nota de inclusão." : ""}
                  {resultado.notas_fonte && resultado.notas_fonte.length > 0
                    ? " Cada nota vale só para o trecho nomeado."
                    : ""}
                </p>
                {resultado.notas_fonte && resultado.notas_fonte.length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-xs">
                    {resultado.notas_fonte.map((nota) => (
                      <li key={nota}>{nota}</li>
                    ))}
                  </ul>
                )}
                <a
                  href={resultado.url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-sm font-medium break-all text-[#9f1239] underline dark:text-[#ff8a8a]"
                >
                  Abrir a página oficial no Planalto
                </a>
                <h4 className="mt-3 font-semibold">Texto recuperado da fonte</h4>
                <blockquote className="mt-1 max-h-64 overflow-y-auto whitespace-pre-wrap break-words border-l-2 border-gold pl-3 text-ink dark:text-slate-100">
                  {resultado.texto_oficial}
                </blockquote>
              </section>
            )}
            {resultado.explicacao && (
              <section className="rounded-2xl border border-slate-200 p-3 dark:border-white/10">
                <h3 className="font-semibold">Explicação do Meu Direito</h3>
                <p className="mt-1 whitespace-pre-wrap break-words text-ink dark:text-slate-100">{resultado.explicacao}</p>
              </section>
            )}
            {resultado.aviso_explicacao && <p className="break-words">{resultado.aviso_explicacao}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
