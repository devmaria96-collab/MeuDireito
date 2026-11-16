import type { Perfil } from "../types/chat.ts";

const OPCOES: { id: Perfil; titulo: string; curto: string; descricao: string }[] = [
  {
    id: "estudante",
    titulo: "Estudante",
    curto: "Estudante",
    descricao: "Explicações claras. Material de estudo só quando você pedir para revisar ou praticar.",
  },
  {
    id: "profissional",
    titulo: "Profissional jurídico",
    curto: "Profissional",
    descricao: "Pesquisa de legislação, argumentos e fontes oficiais, com linguagem técnica.",
  },
  {
    id: "cidadao",
    titulo: "Cidadão",
    curto: "Cidadão",
    descricao: "Leis em linguagem simples, direitos, deveres, termos e caminhos em serviços públicos.",
  },
];

interface PropriedadesPerfil {
  perfil: Perfil;
  onMudar: (perfil: Perfil) => void;
  solto?: boolean;
}

export function SeletorPerfil({ perfil, onMudar, solto = false }: PropriedadesPerfil) {
  const selecionado = OPCOES.find((opcao) => opcao.id === perfil) ?? OPCOES[2];

  return (
    <section className={solto ? "mb-3" : "border-b border-black/10 bg-white/80 px-3 py-3 sm:px-5 dark:bg-black/50"}>
      <div className="mx-auto flex max-w-3xl flex-col gap-2">
        <div className="grid grid-cols-3 gap-1.5 sm:gap-2" role="radiogroup" aria-label="Perfil de utilização">
          {OPCOES.map((opcao) => {
            const ativo = opcao.id === perfil;
            return (
              <button
                key={opcao.id}
                type="button"
                role="radio"
                aria-checked={ativo}
                aria-label={opcao.titulo}
                onClick={() => onMudar(opcao.id)}
                className={`min-h-11 rounded-full px-1.5 py-2 text-center text-[11px] leading-tight font-medium sm:px-3 sm:text-sm ${
                  ativo
                    ? "bg-[#9f1239] font-semibold text-white shadow-[inset_0_-2px_0_#ffffff]"
                    : "bg-white/80 text-black hover:bg-white dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
                }`}
              >
                <span className="sm:hidden">{opcao.curto}</span>
                <span className="hidden sm:inline">{opcao.titulo}</span>
              </button>
            );
          })}
        </div>
        <p className={`text-center text-xs leading-5 text-black/70 dark:text-white/70 ${solto ? "" : "text-left"}`}>
          {selecionado.descricao}
        </p>
      </div>
    </section>
  );
}
