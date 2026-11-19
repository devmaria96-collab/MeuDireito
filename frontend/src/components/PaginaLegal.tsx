import { useEffect, useState } from "react";
import { lerPanorama, type PanoramaLgpd } from "../services/lgpd.ts";
import { PainelArmazenamento } from "./PainelArmazenamento.tsx";

export function PaginaLegal({
  pagina,
  onFechar,
}: {
  pagina: "privacidade" | "termos";
  onFechar: () => void;
}) {
  const [panorama, setPanorama] = useState<PanoramaLgpd | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    void lerPanorama()
      .then((dados) => {
        if (ativo) {
          setPanorama(dados);
        }
      })
      .catch(() => {
        if (ativo) {
          setErro("Não foi possível carregar os dados desta instalação. Nada foi preenchido no lugar.");
        }
      });
    return () => {
      ativo = false;
    };
  }, []);

  return (
    <div className="fixed inset-0 z-[60] overflow-y-auto bg-white text-black dark:bg-black dark:text-white">
      <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-semibold text-[#9f1239]">Meu Direito</p>
          <button type="button" className="min-h-11 px-3 text-sm underline" onClick={onFechar}>
            Voltar
          </button>
        </div>
        {pagina === "privacidade" ? <Politica panorama={panorama} erro={erro} /> : <Termos panorama={panorama} erro={erro} />}
      </div>
    </div>
  );
}

function Politica({ panorama, erro }: { panorama: PanoramaLgpd | null; erro: string | null }) {
  return (
    <article className="mt-4 space-y-6 text-sm leading-6">
      <header>
        <h1 className="text-2xl font-semibold">Política de Privacidade</h1>
        {panorama?.identificacao && <p className="mt-2 text-sm">{panorama.identificacao}</p>}
        <p className="mt-2">{panorama?.aviso ?? "A descrição do tratamento é carregada do servidor desta instalação."}</p>
        {panorama?.aviso_demonstracao && <p className="mt-2">{panorama.aviso_demonstracao}</p>}
      </header>
      {erro && <p role="alert">{erro}</p>}
      {panorama && (
        <>
          <section>
            <h2 className="text-lg font-semibold">Quem trata os dados</h2>
            {panorama.marca_comercial && (
              <p className="mt-2">
                Nome comercial informado: {panorama.marca_comercial}. Isso não confirma a identificação legal do controlador.
              </p>
            )}
            <p className="mt-2">
              {panorama.controlador
                ? `Responsável informado nesta instalação: ${panorama.controlador}.`
                : "O responsável pelo tratamento ainda não foi identificado nesta instalação."}
            </p>
            <p className="mt-2">
              {panorama.contato
                ? `Canal para solicitações de privacidade: ${panorama.contato}.`
                : "O canal de contato ainda não foi configurado. Nenhuma solicitação é recebida por um endereço inventado."}
            </p>
            {panorama.pendencias_administrador.length > 0 && (
              <>
                <h3 className="mt-3 font-semibold">Pendências do administrador</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {panorama.pendencias_administrador.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </>
            )}
          </section>
          {panorama.gemini && (
            <section>
              <h2 className="text-lg font-semibold">Google Gemini</h2>
              <p className="mt-2">{panorama.gemini.provedor}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {panorama.gemini.enviado.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="mt-2">{panorama.gemini.contrato}</p>
              <p className="mt-2">{panorama.gemini.transferencia_internacional}</p>
            </section>
          )}
          <section>
            <h2 className="text-lg font-semibold">O que esta instalação faz</h2>
            <p className="mt-2">
              A pesquisa jurídica funciona sem conta. Cada pergunta enviada vai ao Google Gemini ({panorama.modelos_gemini}), com o perfil de linguagem.
              As mensagens anteriores não são enviadas. Se a resposta consultar lei federal, o servidor lê uma página pública do Planalto e pode pedir ao Gemini uma explicação desse trecho.
            </p>
            <p className="mt-2">{panorama.treinamento}</p>
            <p className="mt-2">{panorama.sensiveis_e_terceiros}</p>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Tratamentos</h2>
            <div className="mt-3 space-y-4">
              {panorama.inventario.map((item) => (
                <section key={item.categoria} className="rounded-2xl border border-black/10 p-3 dark:border-white/15">
                  <h3 className="font-semibold">{item.categoria}</h3>
                  <p className="mt-1">{item.dados}</p>
                  <p className="mt-1">Finalidade: {item.finalidade}</p>
                  <p className="mt-1">Base legal: {item.base_legal}</p>
                  <p className="mt-1">Retenção: {item.retencao}</p>
                  <p className="mt-1">Onde fica: {item.armazenamento}</p>
                </section>
              ))}
            </div>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Fornecedores e transferência</h2>
            <div className="mt-3 space-y-3">
              {panorama.fornecedores.map((item) => (
                <section key={item.nome}>
                  <h3 className="font-semibold">{item.nome}</h3>
                  <p>{item.papel}</p>
                  <p>{item.dados}</p>
                  <p>{item.observacao}</p>
                </section>
              ))}
            </div>
            <p className="mt-3">
              Não há compartilhamento com outros usuários. Quem opera esta máquina pode acessar o banco local. Não há venda de dados.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Cookies e armazenamento</h2>
            <ul className="mt-2 list-disc space-y-2 pl-5">
              {panorama.cookies.map((item) => (
                <li key={item.nome}>
                  <span className="font-medium">{item.nome}</span> {item.necessario ? "(necessário)" : "(opcional)"} — {item.descricao}
                </li>
              ))}
            </ul>
            <div className="mt-4">
              <PainelArmazenamento />
            </div>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Segurança</h2>
            <p className="mt-2">
              A senha fica só como hash Argon2id. A sessão usa cookie HttpOnly. As rotas da conta exigem essa sessão e, nas alterações, o token CSRF.
              Cada conta só acessa as próprias conversas. Esta resposta {panorama.requisicao_https ? "chegou por HTTPS." : "não chegou por HTTPS."} A marca Secure do cookie entra em HTTPS ou com COOKIE_SECURE.
              Publicar na internet sem HTTPS deixa a sessão exposta.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Crianças, adolescentes e dados sensíveis</h2>
            <p className="mt-2">{panorama.criancas}</p>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Direitos de quem usa</h2>
            <ul className="mt-2 list-disc space-y-2 pl-5">
              {panorama.direitos.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mt-2">
              Na conta, a área Privacidade e dados permite consultar, corrigir o que a tela oferece, baixar os dados e excluir a conta.
              A resposta da pesquisa é informação gerada por modelo, não uma decisão automatizada com efeito jurídico produzido por esta instalação.
            </p>
          </section>
          <section>
            <h2 className="text-lg font-semibold">Incidentes</h2>
            <p className="mt-2">{panorama.incidentes}</p>
          </section>
        </>
      )}
    </article>
  );
}

function Termos({ panorama, erro }: { panorama: PanoramaLgpd | null; erro: string | null }) {
  return (
    <article className="mt-4 space-y-4 text-sm leading-6">
      <header>
        <h1 className="text-2xl font-semibold">Termos de Uso</h1>
        {panorama?.identificacao && <p className="mt-2">{panorama.identificacao}</p>}
        <p className="mt-2">
          O Meu Direito é uma ferramenta de informação e pesquisa jurídica assistida por inteligência artificial. Não é advogado, não representa a pessoa e não substitui a orientação de um profissional habilitado.
        </p>
      </header>
      {erro && <p role="alert">{erro}</p>}
      {panorama?.aviso_demonstracao && <p>{panorama.aviso_demonstracao}</p>}
      <p>
        {panorama?.modo_demonstracao
          ? "Nesta demonstração a pesquisa funciona sem cadastro. Criar conta fica desligado porque não há persistência segura das contas."
          : "A pesquisa funciona sem cadastro. A conta é opcional e serve para guardar histórico, perfil e sessões."}
      </p>
      <p>
        As respostas podem errar, ficar desatualizadas ou não confirmar a vigência de uma norma. Lei, súmula e jurisprudência só podem ser tratadas como verificadas quando a própria resposta disser que a fonte foi lida. Tribunais não são consultados.
      </p>
      <p>
        Ao enviar uma pergunta, ela e o perfil de linguagem vão para o Google Gemini{panorama?.modelos_gemini ? ` (${panorama.modelos_gemini})` : ""}. As mensagens anteriores não vão junto. A consulta de legislação lê páginas públicas do Planalto e, se o texto for encontrado, pede uma explicação ao mesmo modelo.
      </p>
      <p>
        Não escreva CPF, endereço, dado de outra pessoa ou dado de criança se isso não for indispensável. O que for escrito pode ficar no histórico escolhido e ser enviado ao modelo.
      </p>
      <p>
        Minutas, quando a rota de geração é usada, são rascunhos para revisão humana. Esta instalação não as guarda no servidor e elas não estão prontas para protocolo.
      </p>
      <p>O uso não cria relação de cliente e advogado nem promessa de resultado judicial.</p>
      <p>
        {panorama?.marca_comercial
          ? `Nome comercial informado: ${panorama.marca_comercial}. Isso não confirma a identificação legal do controlador. `
          : ""}
        {panorama?.controlador
          ? `Responsável informado nesta instalação: ${panorama.controlador}.`
          : "O responsável por esta instalação ainda não foi identificado."}{" "}
        {panorama?.contato
          ? `Contato de privacidade: ${panorama.contato}.`
          : "Não há canal de contato configurado."}
      </p>
    </article>
  );
}
