import { useEffect, useState, type ReactNode } from "react";
import { consultarAcesso, entrarHomologacao } from "../services/homologacao.ts";

type Situacao = "verificando" | "liberado" | "bloqueado" | "incompleto";

export function PortaoHomologacao({ children }: { children: ReactNode }) {
  const [situacao, setSituacao] = useState<Situacao>("verificando");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let ativo = true;
    consultarAcesso()
      .then((estado) => {
        if (!ativo) {
          return;
        }
        if (!estado.exigido || estado.liberado) {
          setSituacao("liberado");
        } else if (!estado.configurado) {
          setSituacao("incompleto");
        } else {
          setSituacao("bloqueado");
        }
      })
      .catch(() => {
        if (ativo) {
          setSituacao("liberado");
        }
      });
    return () => {
      ativo = false;
    };
  }, []);

  if (situacao === "liberado") {
    return children;
  }

  return (
    <main className="grid min-h-screen place-items-center bg-black px-4 text-white">
      <form
        className="w-full max-w-sm"
        onSubmit={(evento) => {
          evento.preventDefault();
          setEnviando(true);
          setErro(null);
          void entrarHomologacao(senha)
            .then((mensagem) => {
              if (mensagem) {
                setErro(mensagem);
                return;
              }
              setSenha("");
              setSituacao("liberado");
            })
            .catch(() => setErro("Não foi possível falar com a API."))
            .finally(() => setEnviando(false));
        }}
      >
        <h1 className="text-2xl font-semibold">Acesso de homologação</h1>
        {situacao === "verificando" ? (
          <p className="mt-3 text-sm leading-6">Verificando o acesso desta instalação.</p>
        ) : situacao === "incompleto" ? (
          <p className="mt-3 text-sm leading-6" role="alert">
            O acesso da homologação não está configurado. A pesquisa permanece fechada até o administrador definir a senha no servidor.
          </p>
        ) : (
          <>
            <p className="mt-3 text-sm leading-6">
              Esta instalação de teste não fica aberta. A senha abaixo não é a senha de uma conta e não libera o Gemini para quem não a recebeu.
            </p>
            <label className="mt-4 block text-sm" htmlFor="senha-homologacao">
              Senha de acesso
            </label>
            <input
              id="senha-homologacao"
              type="password"
              autoComplete="current-password"
              minLength={16}
              maxLength={128}
              required
              value={senha}
              onChange={(evento) => setSenha(evento.target.value)}
              className="mt-2 min-h-11 w-full rounded-full border border-white/20 bg-black px-4 text-white outline-none focus:border-[#e10600]"
            />
            {erro && (
              <p className="mt-3 text-sm" role="alert">
                {erro}
              </p>
            )}
            <button type="submit" disabled={enviando} className="mt-4 min-h-11 w-full rounded-full bg-[#9f1239] text-sm font-medium text-white disabled:opacity-60">
              Entrar na homologação
            </button>
          </>
        )}
      </form>
    </main>
  );
}
