# LGPD — checklist desta instalação

Este arquivo registra o que o Meu Direito faz hoje. Não é parecer jurídico e não declara conformidade com a Lei nº 13.709/2018.

A política pública sai de `GET /lgpd`. Ela não recebe nome, e-mail ou chave usados no desenvolvimento. Responsável e canal só aparecem se `CONTROLADOR_PRIVACIDADE` e `CONTATO_PRIVACIDADE` estiverem definidos.

## Implementado

- Pesquisa sem conta. A pergunta atual e o perfil de linguagem vão ao Google Gemini. As mensagens anteriores não vão. O rastreamento do SDK para a OpenAI está desligado.
- Consulta de lei federal baixa página pública de planalto.gov.br. A explicação desse trecho, quando há texto, também vai ao Gemini.
- A rota de minuta envia os campos do formulário ao Gemini e não grava o arquivo.
- Conta opcional, exportação JSON, exclusão com a palavra EXCLUIR, sessões, Argon2id e isolamento entre usuários.
- Política de Privacidade, Termos de Uso e área Privacidade e dados.
- Cookie `md_sessao` HttpOnly. SameSite Lax por padrão; Strict se configurado; None só com Secure. A marca Secure entra em HTTPS ou com `COOKIE_SECURE=1`.
- CORS local, mais as origens de `ORIGENS_PERMITIDAS`. Curinga e caminho são recusados. `PROXY_CONFIAVEL` limita o uso do protocolo informado pelo proxy.
- Recuperação de senha e confirmação de e-mail por SMTP real, com token temporário, de uso único e guardado só como hash. Sem SMTP, a resposta diz que está pendente e não cria token nem simula envio.
- Contas anteriores à confirmação permanecem utilizáveis com o motivo `conta_anterior`. Isso não registra um e-mail enviado.
- A pesquisa pública não depende da confirmação do e-mail.
- Preferência de tema, perfil e histórico de visitante só é gravada depois da escolha. Recusar apaga essas cópias locais e não apaga a conta.
- A política lista o que é enviado ao Gemini e o que os termos públicos de 19/11/2026 dizem sobre serviço pago e não pago, sem afirmar qual regime vale para esta chave.
- Pendências de configuração aparecem na política e no log de subida, sem dados pessoais.
- `NOME_COMERCIAL` pode mostrar um nome comercial. Ele não preenche `CONTROLADOR_PRIVACIDADE`.
- Com `AMBIENTE=homologacao`, a interface e a API exigem uma senha de acesso guardada só no ambiente. Sem o cookie da API, a pesquisa não chama o Gemini. Em desenvolvimento e em produção essa trava fica desligada.

## Testado

Em 19 de novembro de 2026, 72 testes de backend terminaram OK. `npm run build` no frontend também terminou sem erro. Os testes incluem, com contas de teste:

- Exportação JSON e exclusão da conta, sem atingir outra conta.
- Exclusão de conversas e isolamento entre usuários.
- Recuperação de senha sem simular e-mail e, com SMTP substituído no teste, token que expira e não se repete.
- Confirmação de e-mail nas mesmas condições, com limite de reenvio. A pesquisa sem conta continuou disponível.
- Cookie HttpOnly, Secure e SameSite, inclusive None só quando o cookie é Secure.
- A política sem responsável e sem contato configurados, e sem a chave da API.
- A escolha de armazenamento local: gravar, ler de novo e, ao recusar, apagar histórico e tema deste navegador.
- A homologação: sem o cookie, a pesquisa, a legislação e a minuta não chamam o Gemini; com o cookie, a conta de teste confirma o estado pendente do e-mail, a recuperação não simula envio, uma conta não lê a conversa da outra e a exclusão não derruba a outra sessão. O banco local de desenvolvimento é recusado como destino de migração. O nome comercial Tavares Web não vira controlador nem contato.

`alembic heads` mostrou `20261119_0006` e não aplicou migração no banco de desenvolvimento. `python -m app.migrar_homologacao` recusou esse mesmo banco. Nenhuma conta real foi excluída. Não houve deploy nem envio ao GitHub.

## Pendente de configuração

- `CONTROLADOR_PRIVACIDADE` está vazio. A política não nomeia o responsável.
- `CONTATO_PRIVACIDADE` está vazio. Não há canal publicado para os titulares.
- SMTP e `URL_PUBLICA` não estão definidos. Nenhum e-mail de recuperação ou confirmação sai desta máquina.
- `ORIGENS_PERMITIDAS` não tem domínio de produção. O CORS aceita só o ambiente local.
- Esta execução responde em HTTP. O cookie não leva a marca Secure aqui.
- Não está registrado se a chave do Gemini é de serviço pago, se há aditivo de tratamento aceito ou se o registro de logs do AI Studio está ligado.
- A senha `ACESSO_HOMOLOGACAO`, as URLs da Vercel e da Render e o PostgreSQL exclusivo de homologação ainda não foram criados. Nenhum e-mail real foi autorizado.

## Pendente de validação jurídica

- Bases legais de cada tratamento, inclusive o envio ao Gemini.
- Qual regime do Gemini API se aplica e qual mecanismo cobre uma transferência internacional. A região de tratamento não foi afirmada.
- Uso por crianças e adolescentes. Não há verificação de idade.
- Prazo de guarda de conversas, logs e de um backup, se ele passar a existir. O aplicativo não gera backup.
- Quando um incidente deve ser comunicado à ANPD e aos titulares.
- Texto final da política e dos termos antes de qualquer publicação.
- A troca do endereço de e-mail ainda não existe.
- O nome comercial Tavares Web não foi confirmado como identificação legal do controlador. O canal de Gmail ou Outlook ainda não tem endereço.

## Procedimento de incidente

1. Conter o acesso: encerrar sessões, tirar a instalação da rede se o risco continuar e preservar o volume do banco sem apagá-lo às cegas.
2. Anotar data, o que vazou ou se perdeu, quantos titulares são afetados e o que já foi feito. Não copiar senha, chave de API nem conteúdo de conversa para o registro.
3. A comunicação à ANPD e aos titulares, quando o incidente puder acarretar risco ou dano relevante, é decisão jurídica, no art. 48 da LGPD. O aplicativo não envia essa comunicação sozinho.
4. O endereço mostrado aos titulares é só `CONTATO_PRIVACIDADE`. Sem essa variável, não há canal publicado.
