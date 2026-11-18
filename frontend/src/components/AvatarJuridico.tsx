const COMUNS = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
};

export const AVATARES_JURIDICOS = [
  { id: "balanca", nome: "Balança da Justiça" },
  { id: "martelo", nome: "Martelo de juiz" },
  { id: "livro", nome: "Livro jurídico" },
  { id: "constituicao", nome: "Constituição" },
  { id: "coluna", nome: "Coluna da Justiça" },
  { id: "tribunal", nome: "Tribunal" },
  { id: "pergaminho", nome: "Pergaminho" },
  { id: "estudante", nome: "Estudante de Direito" },
  { id: "protecao", nome: "Símbolo de proteção jurídica" },
] as const;

export type CodigoAvatar = (typeof AVATARES_JURIDICOS)[number]["id"];

export function AvatarJuridico({ codigo, className = "h-8 w-8" }: { codigo: string; className?: string }) {
  return (
    <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
      {codigo === "martelo" && (
        <>
          <path {...COMUNS} d="M18 20l14-10 4 4-14 10" />
          <path {...COMUNS} d="M16 22l6 6" />
          <path {...COMUNS} d="M14 36h16" />
          <path {...COMUNS} d="M20 28l-6 8" />
        </>
      )}
      {codigo === "livro" && (
        <>
          <path {...COMUNS} d="M10 12h12a6 6 0 0 1 6 6v18H16a6 6 0 0 0-6 6z" />
          <path {...COMUNS} d="M38 12H26a6 6 0 0 0-6 6v18h12a6 6 0 0 1 6 6z" />
        </>
      )}
      {codigo === "constituicao" && (
        <>
          <path {...COMUNS} d="M14 8h16l6 6v26H14z" />
          <path {...COMUNS} d="M30 8v6h6" />
          <path {...COMUNS} d="M19 24h12M19 30h8" />
        </>
      )}
      {codigo === "coluna" && (
        <>
          <path {...COMUNS} d="M12 14h24M14 38h20" />
          <path {...COMUNS} d="M16 14v24M24 14v24M32 14v24" />
          <path {...COMUNS} d="M10 10h28v4H10z" />
        </>
      )}
      {codigo === "tribunal" && (
        <>
          <path {...COMUNS} d="M8 20 L24 8 L40 20" />
          <path {...COMUNS} d="M12 20v16h24V20" />
          <path {...COMUNS} d="M20 36v-8h8v8" />
        </>
      )}
      {codigo === "pergaminho" && (
        <>
          <path {...COMUNS} d="M16 10h16a4 4 0 0 1 4 4v22a4 4 0 0 1-4 4H16" />
          <path {...COMUNS} d="M16 10a4 4 0 0 0 0 8h0" />
          <path {...COMUNS} d="M16 40a4 4 0 0 1 0-8" />
          <path {...COMUNS} d="M22 22h10M22 28h8" />
        </>
      )}
      {codigo === "estudante" && (
        <>
          <circle {...COMUNS} cx="24" cy="16" r="5" />
          <path {...COMUNS} d="M12 36c2-7 8-10 12-10s10 3 12 10" />
          <path {...COMUNS} d="M30 28l6 2v8l-6-2" />
        </>
      )}
      {codigo === "protecao" && (
        <>
          <path {...COMUNS} d="M24 8l12 4v10c0 7-5 12-12 16-7-4-12-9-12-16V12z" />
          <path {...COMUNS} d="M18 24l4 4 8-8" />
        </>
      )}
      {codigo !== "martelo" &&
        codigo !== "livro" &&
        codigo !== "constituicao" &&
        codigo !== "coluna" &&
        codigo !== "tribunal" &&
        codigo !== "pergaminho" &&
        codigo !== "estudante" &&
        codigo !== "protecao" && (
          <>
            <path {...COMUNS} d="M24 8v6" />
            <path {...COMUNS} d="M10 22h28" />
            <path {...COMUNS} d="M14 22l-4 14h10l-4-14" />
            <path {...COMUNS} d="M34 22l-4 14h10l-4-14" />
            <path {...COMUNS} d="M24 14v22" />
          </>
        )}
    </svg>
  );
}
