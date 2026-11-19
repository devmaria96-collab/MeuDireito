# Publicação e homologação do Meu Direito

Este guia prepara a instalação. Ele não faz deploy, não cria serviço na Vercel, no Render ou no Google e não declara conformidade com a LGPD.

O repositório previsto é `devmaria96-collab/MeuDireito`. Nada neste arquivo autoriza enviar o código ou colocar o sistema na internet.

## Demonstração de portfólio

A demonstração é o modo `AMBIENTE=demonstracao`. Ela não substitui o desenvolvimento local. Com esse valor:

- A pesquisa jurídica, a consulta ao Planalto e as referências verificáveis continuam sem login.
- O cadastro, o login e o PostgreSQL de contas ficam desligados. Nenhuma migração roda, mesmo que `DATABASE_URL` exista.
- Cada acesso pode fazer 15 pesquisas ao Gemini em 24 horas, com no máximo 8 a cada 10 minutos. O conjunto dos acessos para em 300 pesquisas em 24 horas. Os nomes são `COTA_GEMINI_POR_IP`, `COTA_GEMINI_RAJADA` e `COTA_GEMINI_GLOBAL`.
- O contador fica na memória do processo. No plano gratuito da Render ele zera quando o serviço dorme ou reinicia.
- A interface mostra “Versão experimental — Projeto de portfólio”, avisa que a resposta pode errar e pede para não escrever dado pessoal, informação sigilosa ou documento real.
- “Enviar sugestão” grava só o texto, sem nome e sem e-mail. Um texto com `@` ou com 10 dígitos seguidos é recusado.

O plano gratuito da Vercel serve o frontend. O plano gratuito da Render serve a API, com estas limitações conferidas na documentação em 19/11/2026: o serviço pode dormir após 15 minutos sem tráfego, tem 512 MB e não envia e-mail pelas portas 25, 465 ou 587. O disco é temporário, então a sugestão e a avaliação podem sumir no reinício. O PostgreSQL gratuito expira em 30 dias e não tem backup, por isso a demonstração não o usa.

Arquivos prontos, sem segredo: `.env.demonstracao.example`, `frontend/.env.demonstracao.example` e `render.yaml`. Aplicar o `render.yaml` na Render cria o serviço. Isso não foi feito.

Na Vercel, a raiz do projeto é `frontend`, o build é `npm run build` e a saída é `dist`. `VITE_API_URL` aponta para a origem HTTPS da API, sem caminho e sem credencial. Não defina `AMBIENTE=homologacao` nessa interface, senão o proxy pede a senha de homologação. Na API, `ORIGENS_PERMITIDAS` recebe a origem HTTPS da Vercel. `GEMINI_API_KEY` fica só no painel da Render.

Nenhum plano pago foi contratado e nada foi publicado.

## O que já existe no código

- A API sobe por `uvicorn app.main:app`. No desenvolvimento local o README usa `uvicorn app.main:app --reload`. Na Render o processo precisa escutar `0.0.0.0` e a porta `$PORT`.
- O frontend está em `frontend`. `npm run dev` sobe o Vite na porta 5173. `npm run build` executa `tsc && vite build` e gera `frontend/dist`.
- O Alembic fica em `alembic`, com `alembic.ini` na raiz. A revisão atual da cadeia é `20261119_0006`. `alembic/env.py` usa `DATABASE_URL` quando ela existe no processo. Sem essa variável, o arquivo de configuração aponta para `127.0.0.1:5434/meudireito`, que é o banco de desenvolvimento.
- Ao subir a API, `app/banco.py` aplica as migrações pendentes, exceto na homologação. Nesse ambiente a migração só ocorre com destino conferido e `CONFIRMAR_MIGRACAO_HOMOLOGACAO=1`.
- A pesquisa jurídica funciona sem conta em desenvolvimento e em produção. A conta é opcional. A senha da conta fica só como hash Argon2id.
- O cookie `md_sessao` é HttpOnly. SameSite é Lax, ou Strict se `COOKIE_SAMESITE=strict`. `none` só é aceito quando o cookie também é Secure.
- Sem `SMTP_HOST`, `SMTP_DE` e `URL_PUBLICA`, a recuperação de senha e a confirmação de e-mail respondem que o envio está pendente. Nenhum e-mail é simulado e nenhum token é criado.

## Três ambientes

| Ambiente | Arquivo de exemplo | Pesquisa pública | Banco |
| --- | --- | --- | --- |
| Desenvolvimento | `.env.example` e `frontend/.env.example` | Aberta | PostgreSQL local da porta 5434, banco `meudireito` |
| Homologação | `.env.homologacao.example` e `frontend/.env.homologacao.example` | Fechada pelo acesso privado | PostgreSQL exclusivo, sem cópia dos dados locais |
| Produção | `.env.producao.example` e `frontend/.env.producao.example` | Aberta de novo | Outro PostgreSQL, separado da homologação |

Os exemplos não trazem chave, senha, token nem URL com usuário e senha. Os valores reais ficam só nos painéis da Vercel e da Render, ou no `.env` local, que não entra no Git.

`NOME_COMERCIAL=Tavares Web` pode aparecer na política como nome comercial. `CONTROLADOR_PRIVACIDADE` e `CONTATO_PRIVACIDADE` continuam vazios. A identificação legal do controlador e o endereço de Gmail ou Outlook ainda não existem. A política diz isso em vez de inventar os dois.

## Acesso privado da homologação

Um endereço difícil de adivinhar não é proteção. O login da conta também não basta: em desenvolvimento e em produção a pesquisa continua acessível sem cadastro e chama o Gemini.

Na homologação há duas travas, com a mesma senha definida fora do repositório:

1. A interface na Vercel usa `frontend/proxy.ts`, apontado por `frontend/vercel.json`. Com `AMBIENTE=homologacao`, o arquivo não é servido enquanto o cookie HttpOnly `md_acesso_interface` não existir. A senha é lida de `ACESSO_HOMOLOGACAO` no servidor. Ela não pode ter o prefixo `VITE_`, porque esse prefixo entra no JavaScript público.
2. A API recusa `/conversar`, `/consultar-legislacao`, `/documentos/gerar`, as rotas de conta e o restante antes de chamar o Gemini. O cookie HttpOnly `md_acesso` é emitido por `POST /acesso/homologacao`, dura 12 horas e guarda só um HMAC. Sem o cookie a resposta é 403. Se a senha tiver menos de 16 caracteres, ou não existir, a API responde 503 e continua fechada.

`GET /saude` fica de fora dessa trava para a Render saber que o processo subiu. Essa rota não consulta o Gemini nem o banco.

A autenticação da Vercel, incluída nos planos, pode ser ligada além dessas travas. A proteção por senha da própria Vercel não está no plano Hobby; no Pro, a documentação consultada em 19/11/2026 cobra US$ 20 por projeto ao mês. Links compartilháveis da Vercel podem contornar a autenticação da plataforma. Por isso a trava da API continua obrigatória: ela impede que um terceiro use a chave do Gemini direto no endereço da Render.

No navegador, a interface e a API estão em domínios diferentes. O cookie da API precisa de `COOKIE_SECURE=1` e `COOKIE_SAMESITE=none`. `ORIGENS_PERMITIDAS` recebe a origem HTTPS da Vercel, sem caminho e sem curinga. `PROXY_CONFIAVEL=1` e `PROXY_HOSTS=*` servem para a Render, porque o processo não é exposto direto e o proxy da plataforma informa o HTTPS. Não use `PROXY_HOSTS=*` se o uvicorn estiver acessível sem esse proxy.

`URL_API_HOMOLOGACAO` na Vercel e `VITE_API_URL` no build devem ser a mesma origem HTTPS da API, sem caminho e sem credencial. A primeira faz o formulário inicial também liberar a API. A segunda é a única variável de API que o JavaScript precisa.

Em desenvolvimento local a trava não entra, porque `AMBIENTE` fica `desenvolvimento` ou vazio. A pesquisa da máquina atual continua aberta.

## Banco de homologação

Não copie o volume `meudireito_pg` nem use a URL `127.0.0.1:5434/meudireito`. Esse banco é o de desenvolvimento.

O arquivo `docker-compose.homologacao.yml` sobe um PostgreSQL 16 vazio, na porta 5435, com o banco `meudireito_homologacao` e outro volume. Ele não foi iniciado. A senha vem do terminal, não do arquivo:

```powershell
$env:POSTGRES_PASSWORD = "defina-uma-senha-so-neste-terminal"
docker compose -f docker-compose.homologacao.yml up -d
```

Na Render, crie um PostgreSQL separado quando for a hora. Não foi criado aqui. O plano gratuito documentado em 19/11/2026 expira em 30 dias, tem 1 GB, não faz backup e só permite um banco gratuito por workspace. O plano pago de banco começa em US$ 6 por mês.

Se a Render entregar `postgres://` ou `postgresql://`, troque o esquema para `postgresql+psycopg://` e mantenha o restante. Não cole a URL com senha neste repositório.

Antes de migrar, confira o destino. O comando imprime só esquema, host, porta e nome do banco:

```powershell
$env:AMBIENTE = "homologacao"
$env:DATABASE_URL = "postgresql+psycopg://USUARIO:SENHA@HOST:5432/meudireito_homologacao"
.\.venv\Scripts\python.exe -m app.migrar_homologacao
```

Sem `AMBIENTE=homologacao`, ou se o destino for o banco local `meudireito`, ele recusa e não migra. Com o destino certo, repita acrescentando `$env:CONFIRMAR_MIGRACAO_HOMOLOGACAO = "1"`. Não rode `alembic upgrade head` sem `DATABASE_URL`: o `alembic.ini` aponta para o banco de desenvolvimento.

A subida da API na homologação também só migra quando essas duas condições já estão válidas. Nos outros ambientes, a subida continua aplicando o que estiver pendente.

## SMTP

O código já envia por SMTP de verdade quando `SMTP_HOST`, `SMTP_DE` e `URL_PUBLICA` existem. Não houve envio nesta preparação.

Escolha um provedor depois e preencha os mesmos nomes:

- Gmail: `SMTP_HOST=smtp.gmail.com`, porta 587, `SMTP_TLS=1`. `SMTP_USUARIO` e `SMTP_DE` são o endereço da caixa. `SMTP_SENHA` é uma senha de aplicativo, não a senha da conta.
- Outlook.com: `SMTP_HOST=smtp-mail.outlook.com`, porta 587, `SMTP_TLS=1`.
- Microsoft 365: `SMTP_HOST=smtp.office365.com`, porta 587, `SMTP_TLS=1`.

`URL_PUBLICA` precisa ser a origem HTTPS da interface, porque ela entra no link. O canal `CONTATO_PRIVACIDADE` só deve ser preenchido quando esse endereço existir. Pode ser Gmail ou Outlook. Não foi escolhido ainda.

A documentação da Render consultada em 19/11/2026 diz que o plano gratuito de web service não abre conexão de saída nas portas 25, 465 e 587, e que a porta 25 fica bloqueada em todos os planos. A confirmação e a recuperação de senha, saindo de um web service gratuito, não funcionam. Um web service pago, a partir de US$ 7 por mês no plano de 512 MB, é o caminho documentado para usar a porta 587. Nenhum plano foi contratado.

## Variáveis obrigatórias na homologação

Na API:

```text
AMBIENTE=homologacao
ACESSO_HOMOLOGACAO=
NOME_COMERCIAL=Tavares Web
CONTROLADOR_PRIVACIDADE=
CONTATO_PRIVACIDADE=
GEMINI_API_KEY=
DATABASE_URL=
CONFIRMAR_MIGRACAO_HOMOLOGACAO=
SMTP_HOST=
SMTP_PORT=587
SMTP_USUARIO=
SMTP_SENHA=
SMTP_DE=
SMTP_TLS=1
URL_PUBLICA=
COOKIE_SECURE=1
COOKIE_SAMESITE=none
ORIGENS_PERMITIDAS=
PROXY_CONFIAVEL=1
PROXY_HOSTS=*
RETENCAO_REGISTRO_EXCLUSAO_DIAS=0
```

Na Vercel, além de `VITE_API_URL`:

```text
AMBIENTE=homologacao
ACESSO_HOMOLOGACAO=
URL_API_HOMOLOGACAO=
```

`ACESSO_HOMOLOGACAO` deve ser a mesma senha nos dois painéis e ter no mínimo 16 caracteres. Não a coloque num nome que comece com `VITE_`.

## Comandos conferidos

Desenvolvimento, em dois terminais, a partir da pasta do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

```powershell
cd frontend
npm install
npm run dev
```

Build do frontend:

```powershell
cd frontend
npm run build
```

Cadeia de migração, sem aplicá-la:

```powershell
$env:DATABASE_URL = "sqlite:///:memory:"
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
```

Testes de backend:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Na Render, quando o serviço for criado manualmente:

```text
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

O health check HTTP pode usar `/saude`. A raiz do serviço da API é a raiz do repositório. A raiz do projeto na Vercel é `frontend`, o build é `npm run build` e a saída é `dist`.

## Custos e serviços externos

Nada foi criado nem contratado. Os valores abaixo saem das páginas públicas consultadas em 19/11/2026 e podem mudar:

- Vercel Hobby: US$ 0. Vercel Pro: US$ 20 por mês. A senha de proteção da Vercel não existe no Hobby e, no Pro, custa US$ 20 por projeto ao mês. A autenticação da Vercel está incluída. O proxy deste repositório não depende da senha paga.
- Render, web service gratuito: US$ 0, 512 MB, pode dormir depois de 15 minutos sem tráfego e não envia SMTP na porta 587. O plano pago de 512 MB começa em US$ 7 por mês.
- Render Postgres gratuito: US$ 0, 1 GB, expira em 30 dias e não tem backup. O plano pago começa em US$ 6 por mês.
- Gemini: o preço depende do projeto Google da chave. Este repositório não registra se a chave é paga, se há aditivo de tratamento ou se o log do AI Studio está ligado.
- Gmail ou Outlook: nenhuma caixa foi criada. O SMTP usa a conta que for escolhida depois.

## Gemini

Cada pesquisa envia ao Google Gemini, pela LiteLLM no servidor, a pergunta atual e a instrução do perfil. As mensagens anteriores não vão. A explicação de um artigo envia o trecho já lido no Planalto. A rota de minuta envia os campos do formulário. A chave não vai ao navegador.

Os termos públicos do Gemini API, consultados em 19/11/2026, tratam de forma diferente o serviço pago e o não pago. Esta instalação não registra qual dos dois vale para a chave. A região e o mecanismo de transferência internacional continuam pendentes. A homologação não muda esse fato: ela só impede que terceiros disparem a chave enquanto o acesso privado estiver ligado.

## O que foi executado em 19/11/2026

- `unittest discover -s tests`: 72 testes OK. Incluem exportação, exclusão, histórico, isolamento, confirmação, recuperação, e a homologação com contas de teste. Sem o cookie, `/conversar` respondeu 403 e o Gemini substituído no teste não foi chamado. Nenhum e-mail real saiu.
- `npm run build` em `frontend`: concluiu sem erro.
- `alembic heads`: `20261119_0006`. Nenhuma migração foi aplicada no banco de desenvolvimento.
- `python -m app.migrar_homologacao`: recusou. O destino lido foi `127.0.0.1`, porta `5434`, banco `meudireito`, e `AMBIENTE` não era homologação.

Não houve deploy e o GitHub não recebeu estas alterações. Nenhuma conta real foi excluída.

## Pendências

- Senha de homologação, URLs da Vercel e da Render, `GEMINI_API_KEY` do ambiente novo e `DATABASE_URL` do banco exclusivo ainda não foram definidos nos painéis.
- O PostgreSQL de homologação não foi criado e não foi migrado.
- `CONTROLADOR_PRIVACIDADE` segue vazio. Tavares Web é só o nome comercial.
- `CONTATO_PRIVACIDADE` segue vazio. O endereço de Gmail ou Outlook não foi escolhido.
- SMTP não foi autorizado a enviar. No plano gratuito da Render a porta 587 nem abre.
- A identificação legal, as bases legais, crianças e adolescentes, a transferência internacional e o texto final da política continuam pendentes de validação jurídica. A troca de e-mail da conta também não existe.
- A produção não está autorizada. Com `AMBIENTE=producao` a pesquisa volta a ser pública; só passe para esse valor quando a publicação for decidida.
