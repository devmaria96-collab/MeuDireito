export function RodapeLegal({
  onAbrir,
  experimental = false,
  onSugestao,
}: {
  onAbrir: (pagina: "privacidade" | "termos") => void;
  experimental?: boolean;
  onSugestao?: () => void;
}) {
  return (
    <div className="mx-auto mt-2 max-w-3xl">
      {experimental && (
        <p className="text-center text-xs text-muted">Versão experimental — Projeto de portfólio</p>
      )}
      <p className="flex flex-wrap justify-center gap-x-3 gap-y-1 text-center text-xs text-muted">
        <button type="button" className="min-h-11 underline" onClick={() => onAbrir("privacidade")}>
          Política de Privacidade
        </button>
        <button type="button" className="min-h-11 underline" onClick={() => onAbrir("termos")}>
          Termos de Uso
        </button>
        {experimental && onSugestao && (
          <button type="button" className="min-h-11 underline" onClick={onSugestao}>
            Enviar sugestão
          </button>
        )}
      </p>
    </div>
  );
}
