import { Check, Copy, Landmark, Scale, ThumbsDown, ThumbsUp, User } from "lucide-react";
import { isValidElement, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import { enviarAvaliacao, type MotivoAvaliacao } from "../services/api.ts";
import type { Mensagem, Referencia } from "../types/chat.ts";

const MOTIVOS: { id: MotivoAvaliacao; rotulo: string }[] = [
  { id: "incorreta", rotulo: "Informação incorreta" },
  { id: "desatualizada", rotulo: "Informação desatualizada" },
  { id: "incompleta", rotulo: "Resposta incompleta" },
  { id: "confusa", rotulo: "Explicação confusa" },
  { id: "outro", rotulo: "Outro motivo" },
];

function hrefSeguro(href: string | undefined): string | null {
  if (!href) {
    return null;
  }
  try {
    const endereco = new URL(href, window.location.origin);
    if (endereco.protocol === "http:" || endereco.protocol === "https:") {
      return endereco.href;
    }
  } catch {
    return null;
  }
  return null;
}

interface PropriedadesMensagem {
  mensagem: Mensagem;
}

function textoDosFilhos(no: ReactNode): string {
  if (typeof no === "string" || typeof no === "number") {
    return String(no);
  }
  if (Array.isArray(no)) {
    return no.map(textoDosFilhos).join("");
  }
  if (isValidElement<{ children?: ReactNode }>(no)) {
    return textoDosFilhos(no.props.children);
  }
  return "";
}

async function copiarTexto(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch {
    return false;
  }
}

function BlocoCodigo({ children }: { children?: ReactNode }) {
  const [copiado, setCopiado] = useState(false);
  const codigo = textoDosFilhos(children).replace(/\n$/, "");

  async function copiar() {
    const ok = await copiarTexto(codigo);
    if (!ok) {
      return;
    }
    setCopiado(true);
    window.setTimeout(() => setCopiado(false), 1600);
  }

  return (
    <div className="relative my-3 overflow-hidden rounded-xl bg-navy">
      <button
        type="button"
        onClick={() => void copiar()}
        className="absolute top-2 right-2 inline-flex items-center gap-1 rounded-lg bg-white/10 px-2 py-1 text-xs text-white hover:bg-white/20"
        aria-label="Copiar código"
      >
        {copiado ? <Check size={14} /> : <Copy size={14} />}
        {copiado ? "Copiado" : "Copiar"}
      </button>
      <pre className="overflow-x-auto p-4 pt-10 text-sm leading-6 text-slate-100">
        {children}
      </pre>
    </div>
  );
}

function rotuloSituacao(referencia: Referencia): string {
  if (!referencia.verificada) {
    return "Não verificado";
  }
  if (referencia.situacao === "norma_revogada") {
    return "Norma indicada como revogada";
  }
  if (referencia.situacao === "dispositivo_revogado") {
    return "Artigo indicado como revogado";
  }
  if (referencia.situacao === "indicio_revogacao") {
    return "Indício de revogação na página";
  }
  if (referencia.situacao === "dispositivo_alterado") {
    return "Caput com nota de alteração";
  }
  if (referencia.situacao === "indicio_alteracao") {
    return "A página menciona alteração";
  }
  if (referencia.situacao === "dispositivo_incluido") {
    return "Caput com nota de inclusão";
  }
  return "Texto recuperado";
}

function ReferenciaCard({ referencia }: { referencia: Referencia }) {
  const tipo =
    referencia.tipo_texto === "compilado" ? "Texto compilado ou consolidado" : "Página oficial";
  return (
    <aside className="rounded-xl border border-[#e10600]/40 bg-white/90 px-3 py-2 text-xs leading-5 text-black dark:bg-black/70 dark:text-white">
      <p className="font-medium">
        {referencia.verificada ? "Fonte consultada" : "Fonte não confirmada"} · {rotuloSituacao(referencia)}
      </p>
      {referencia.verificada && (
        <p className="mt-1 break-words">
          {referencia.norma}
          {referencia.artigo ? `, artigo ${referencia.artigo}` : ""}
          {referencia.numero
            ? ` · nº ${referencia.numero}${referencia.ano ? `/${referencia.ano}` : ""}`
            : referencia.ano
              ? ` · ${referencia.ano}`
              : ""}
          {` · ${tipo}`}
        </p>
      )}
      {referencia.notas_fonte.length > 0 && (
        <ul className="mt-1 list-disc pl-4">
          {referencia.notas_fonte.map((nota) => (
            <li key={nota}>{nota}</li>
          ))}
        </ul>
      )}
      <p className="mt-1 text-muted">
        Consulta em {referencia.consultado_em || "data não informada"}. A vigência não foi confirmada.
      </p>
      {referencia.url && (
        <a
          href={referencia.url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-1 inline-block break-all font-medium text-[#9f1239] underline dark:text-[#ff8a8a]"
        >
          Abrir a página oficial no Planalto
        </a>
      )}
      {!referencia.verificada && <p className="mt-1">{referencia.aviso}</p>}
    </aside>
  );
}

function Avaliacao({ copiado, onCopiar }: { copiado: boolean; onCopiar: () => void }) {
  const [voto, setVoto] = useState<"positiva" | "negativa" | null>(null);
  const [motivoAberto, setMotivoAberto] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function registrar(avaliacao: "positiva" | "negativa", motivo?: MotivoAvaliacao) {
    if (enviando || voto) {
      return;
    }
    setEnviando(true);
    setAviso(null);
    try {
      await enviarAvaliacao(avaliacao, motivo);
      setVoto(avaliacao);
      setMotivoAberto(false);
      setAviso("Avaliação registrada. O modelo não é reentrenado com ela.");
    } catch {
      setAviso("Não foi possível registrar a avaliação.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mt-1 w-full">
      <div className="flex flex-wrap items-center">
        <button
          type="button"
          onClick={onCopiar}
          className="inline-flex min-h-11 items-center gap-1 rounded-lg px-3 text-xs text-muted hover:bg-slate-200/70 dark:hover:bg-white/10"
          aria-label="Copiar resposta"
        >
          {copiado ? <Check size={14} /> : <Copy size={14} />}
          {copiado ? "Copiado" : "Copiar"}
        </button>
        <button
          type="button"
          disabled={enviando || voto !== null}
          onClick={() => void registrar("positiva")}
          className={`inline-flex min-h-11 items-center gap-1 rounded-lg px-3 text-xs hover:bg-slate-200/70 disabled:opacity-60 dark:hover:bg-white/10 ${
            voto === "positiva" ? "text-[#9f1239]" : "text-muted"
          }`}
          aria-label="Gostei"
          aria-pressed={voto === "positiva"}
        >
          <ThumbsUp size={14} />
          Gostei
        </button>
        <button
          type="button"
          disabled={enviando || voto !== null}
          onClick={() => {
            setMotivoAberto((aberto) => !aberto);
            setAviso(null);
          }}
          className={`inline-flex min-h-11 items-center gap-1 rounded-lg px-3 text-xs hover:bg-slate-200/70 disabled:opacity-60 dark:hover:bg-white/10 ${
            voto === "negativa" ? "text-[#9f1239]" : "text-muted"
          }`}
          aria-label="Não gostei"
          aria-pressed={voto === "negativa"}
        >
          <ThumbsDown size={14} />
          Não gostei
        </button>
      </div>
      {motivoAberto && !voto && (
        <div className="mt-1 flex flex-wrap gap-2 px-1" role="group" aria-label="Motivo da avaliação">
          {MOTIVOS.map((motivo) => (
            <button
              key={motivo.id}
              type="button"
              disabled={enviando}
              onClick={() => void registrar("negativa", motivo.id)}
              className="min-h-11 rounded-full border border-black/15 px-3 text-xs text-black hover:border-[#e10600] dark:border-white/20 dark:text-white"
            >
              {motivo.rotulo}
            </button>
          ))}
          <button
            type="button"
            disabled={enviando}
            onClick={() => void registrar("negativa")}
            className="min-h-11 rounded-full px-3 text-xs text-muted underline"
          >
            Registrar sem motivo
          </button>
        </div>
      )}
      {aviso && <p className="px-3 text-xs text-muted">{aviso}</p>}
    </div>
  );
}

export function ChatMessage({ mensagem }: PropriedadesMensagem) {
  const [copiado, setCopiado] = useState(false);
  const doUsuario = mensagem.papel === "usuario";

  async function copiarResposta() {
    const ok = await copiarTexto(mensagem.conteudo);
    if (!ok) {
      return;
    }
    setCopiado(true);
    window.setTimeout(() => setCopiado(false), 1600);
  }

  return (
    <article className={`surgir flex min-w-0 gap-2 sm:gap-3 ${doUsuario ? "flex-row-reverse" : "flex-row"}`}>
      <span
        className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full ${
          doUsuario ? "bg-black text-white" : "bg-[#9f1239] text-white"
        }`}
        aria-hidden="true"
      >
        {doUsuario ? <User size={16} /> : <Scale size={16} />}
      </span>
      <div className={`flex min-w-0 max-w-[min(100%,40rem)] flex-col ${doUsuario ? "items-end" : "items-start"}`}>
        <p className="mb-1 px-1 text-xs font-medium text-muted">{doUsuario ? "Você" : "Meu Direito"}</p>
        <div
          className={`w-fit max-w-full min-w-0 rounded-2xl px-4 py-3 text-[15px] leading-7 ${
            doUsuario
              ? "rounded-br-md bg-white text-black"
              : "rounded-bl-md border border-black/10 bg-white/90 text-black dark:border-white/10 dark:bg-black/75 dark:text-white"
          }`}
        >
          {doUsuario ? (
            <p className="whitespace-pre-wrap break-words">{mensagem.conteudo}</p>
          ) : (
            <div className="markdown min-w-0">
              <ReactMarkdown
                components={{
                  a: ({ href, children }) => {
                    const seguro = hrefSeguro(typeof href === "string" ? href : undefined);
                    if (!seguro) {
                      return <span>{children}</span>;
                    }
                    const oficial = seguro.startsWith("https://www.planalto.gov.br/");
                    if (oficial) {
                      return (
                        <a
                          href={seguro}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="my-2 flex items-start gap-2 rounded-xl border border-[#e10600]/50 bg-[#e10600]/10 px-3 py-2 text-sm text-black no-underline dark:text-white"
                        >
                          <Landmark size={16} className="mt-0.5 shrink-0 text-[#9f1239] dark:text-[#ff6b6b]" aria-hidden="true" />
                          <span className="min-w-0">
                            <span className="block font-medium">Fonte oficial consultada</span>
                            <span className="block break-all text-xs text-muted">{children}</span>
                          </span>
                        </a>
                      );
                    }
                    return (
                      <a href={seguro} target="_blank" rel="noreferrer noopener">
                        {children}
                      </a>
                    );
                  },
                  img: ({ alt }) => <span>{alt}</span>,
                  pre: ({ children }) => <BlocoCodigo>{children}</BlocoCodigo>,
                  code: ({ className, children }) =>
                    className ? (
                      <code className={className}>{children}</code>
                    ) : (
                      <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[0.92em] dark:bg-white/10">
                        {children}
                      </code>
                    ),
                }}
              >
                {mensagem.conteudo}
              </ReactMarkdown>
            </div>
          )}
        </div>
        {!doUsuario && mensagem.referencias && mensagem.referencias.length > 0 && (
          <div className="mt-2 w-full space-y-2">
            {mensagem.referencias.map((referencia) => (
              <ReferenciaCard key={referencia.id} referencia={referencia} />
            ))}
          </div>
        )}
        {!doUsuario && (
          <Avaliacao copiado={copiado} onCopiar={() => void copiarResposta()} />
        )}
      </div>
    </article>
  );
}
