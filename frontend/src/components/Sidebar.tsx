import { BookOpen, Landmark, Menu, PanelLeftClose, PanelLeftOpen, Plus, Scale, Settings, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Conversa } from "../types/chat.ts";

interface PropriedadesBarra {
  conversas: Conversa[];
  ativaId: string | null;
  abertaNoCelular: boolean;
  recolhida: boolean;
  onNova: () => void;
  onSelecionar: (id: string) => void;
  onPedirExclusao: (id: string) => void;
  onConsultar: () => void;
  onFontes: () => void;
  onConfiguracoes: () => void;
  onAlternarRecolhimento: () => void;
  onFecharCelular: () => void;
}

function dataCurta(iso: string): string {
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) {
    return "";
  }
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" }).format(data);
}

export function BotaoMenu({ aberto, onAbrir }: { aberto: boolean; onAbrir: () => void }) {
  return (
    <button
      id="botao-menu"
      type="button"
      onClick={onAbrir}
      className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-black hover:bg-black/5 md:hidden dark:text-white dark:hover:bg-white/10"
      aria-label="Abrir menu"
      aria-controls="menu-lateral"
      aria-expanded={aberto}
    >
      <Menu size={20} />
    </button>
  );
}

function ItemMenu({
  ativo,
  recolhida,
  rotulo,
  icone,
  onClick,
}: {
  ativo?: boolean;
  recolhida: boolean;
  rotulo: string;
  icone: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={ativo ? "page" : undefined}
      title={rotulo}
      className={`flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-sm transition hover:bg-white/10 ${
        ativo ? "bg-white/10 font-medium text-white shadow-[inset_3px_0_0_#e10600]" : "text-slate-100"
      } ${recolhida ? "md:justify-center md:px-0" : ""}`}
    >
      <span className={ativo ? "text-gold" : ""} aria-hidden="true">
        {icone}
      </span>
      <span className={recolhida ? "md:sr-only" : ""}>{rotulo}</span>
    </button>
  );
}

export function Sidebar({
  conversas,
  ativaId,
  abertaNoCelular,
  recolhida,
  onNova,
  onSelecionar,
  onPedirExclusao,
  onConsultar,
  onFontes,
  onConfiguracoes,
  onAlternarRecolhimento,
  onFecharCelular,
}: PropriedadesBarra) {
  const painel = useRef<HTMLElement>(null);
  const fechar = useRef<HTMLButtonElement>(null);
  const [celular, setCelular] = useState(false);
  const oculto = celular && !abertaNoCelular;

  useEffect(() => {
    const consulta = window.matchMedia("(max-width: 767px)");
    const atualizar = () => setCelular(consulta.matches);
    atualizar();
    consulta.addEventListener("change", atualizar);
    return () => consulta.removeEventListener("change", atualizar);
  }, []);

  useEffect(() => {
    if (!abertaNoCelular) {
      return;
    }
    const corpo = document.body;
    const estouro = corpo.style.overflow;
    corpo.style.overflow = "hidden";
    fechar.current?.focus();

    function conter(evento: KeyboardEvent) {
      if (evento.key !== "Tab" || !painel.current) {
        return;
      }
      const itens = [...painel.current.querySelectorAll<HTMLElement>("button:not([disabled]), a[href]")].filter(
        (item) => item.getClientRects().length > 0,
      );
      if (itens.length === 0) {
        return;
      }
      const primeiro = itens[0];
      const ultimo = itens[itens.length - 1];
      if (evento.shiftKey && document.activeElement === primeiro) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primeiro.focus();
      }
    }

    document.addEventListener("keydown", conter);
    return () => {
      corpo.style.overflow = estouro;
      document.removeEventListener("keydown", conter);
      document.getElementById("botao-menu")?.focus();
    };
  }, [abertaNoCelular]);

  return (
    <>
      {abertaNoCelular && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-deep/60 md:hidden"
          aria-label="Fechar menu"
          onClick={onFecharCelular}
        />
      )}
      <aside
        ref={painel}
        id="menu-lateral"
        role={abertaNoCelular ? "dialog" : "navigation"}
        aria-modal={abertaNoCelular || undefined}
        aria-hidden={oculto || undefined}
        inert={oculto || undefined}
        aria-label="Menu do Meu Direito"
        className={`fixed inset-y-0 left-0 z-40 flex w-[min(18rem,calc(100%-2.75rem))] flex-col border-r border-white/10 bg-black text-white motion-safe:transition-transform motion-safe:duration-200 md:static md:translate-x-0 ${
          abertaNoCelular ? "translate-x-0" : "-translate-x-full"
        } ${recolhida ? "md:w-[4.75rem]" : "md:w-72"}`}
      >
        <div className={`flex items-center gap-3 px-4 py-4 ${recolhida ? "md:flex-col md:px-2" : ""}`}>
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#9f1239] text-white">
            <Scale size={20} />
          </span>
          <div className={recolhida ? "md:sr-only" : ""}>
            <p className="text-sm font-semibold tracking-wide">Meu Direito</p>
          </div>
          <button
            ref={fechar}
            type="button"
            onClick={onFecharCelular}
            className="ml-auto grid h-11 w-11 place-items-center rounded-lg hover:bg-white/10 md:hidden"
            aria-label="Fechar menu"
          >
            <X size={18} />
          </button>
          <button
            type="button"
            onClick={onAlternarRecolhimento}
            className={`hidden h-11 w-11 place-items-center rounded-lg hover:bg-white/10 md:grid ${
              recolhida ? "" : "ml-auto"
            }`}
            aria-label={recolhida ? "Expandir barra lateral" : "Recolher barra lateral"}
          >
            {recolhida ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <div className="px-3">
          <button
            type="button"
            onClick={onNova}
            className={`flex min-h-11 w-full items-center gap-2 rounded-full px-3 text-sm font-medium hover:bg-white/10 ${
              recolhida ? "md:px-0" : ""
            }`}
          >
            <Plus size={18} />
            <span className={recolhida ? "md:sr-only" : ""}>Nova conversa</span>
          </button>
        </div>

        <div className={`mt-5 flex min-h-0 flex-1 flex-col px-3 ${recolhida ? "md:hidden" : ""}`}>
          <p className="px-2 pb-2 text-xs font-medium tracking-wide text-slate-400 uppercase">Conversas</p>
          <div className="min-h-0 flex-1 space-y-1 overflow-y-auto overscroll-contain pb-3">
            {conversas.length === 0 && <p className="px-2 py-3 text-sm text-slate-400">Nenhuma conversa ainda.</p>}
            {conversas.map((conversa) => {
              const selecionada = conversa.id === ativaId;
              return (
                <div
                  key={conversa.id}
                  className={`group flex items-center gap-1 rounded-xl ${
                    selecionada ? "bg-white/10 shadow-[inset_3px_0_0_#e10600]" : "hover:bg-white/10"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelecionar(conversa.id)}
                    aria-current={selecionada ? "true" : undefined}
                    className="min-h-11 min-w-0 flex-1 px-3 py-2 text-left"
                  >
                    <span className="block truncate text-sm">{conversa.titulo}</span>
                    <span className="block text-xs text-slate-400">{dataCurta(conversa.criadaEm)}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onPedirExclusao(conversa.id)}
                    className="mr-1 grid h-11 w-11 shrink-0 place-items-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100 [@media(hover:hover)]:focus-visible:opacity-100"
                    aria-label={`Excluir conversa ${conversa.titulo}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        <div className="mt-auto space-y-1 border-t border-white/10 p-3">
          <p className={`px-2 pb-1 text-xs font-medium tracking-wide text-slate-400 uppercase ${recolhida ? "md:sr-only" : ""}`}>
            Navegação
          </p>
          <ItemMenu recolhida={recolhida} rotulo="Consultar legislação" icone={<BookOpen size={18} />} onClick={onConsultar} />
          <ItemMenu recolhida={recolhida} rotulo="Fontes oficiais" icone={<Landmark size={18} />} onClick={onFontes} />
          <ItemMenu recolhida={recolhida} rotulo="Configurações" icone={<Settings size={18} />} onClick={onConfiguracoes} />
        </div>
      </aside>
    </>
  );
}
