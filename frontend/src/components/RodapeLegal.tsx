export function RodapeLegal({ onAbrir }: { onAbrir: (pagina: "privacidade" | "termos") => void }) {
  return (
    <p className="mx-auto mt-2 flex max-w-3xl flex-wrap justify-center gap-x-3 gap-y-1 text-center text-xs text-muted">
      <button type="button" className="min-h-11 underline" onClick={() => onAbrir("privacidade")}>
        Política de Privacidade
      </button>
      <button type="button" className="min-h-11 underline" onClick={() => onAbrir("termos")}>
        Termos de Uso
      </button>
    </p>
  );
}
