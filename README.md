# Meu Direito

O conhecimento jurídico ao seu alcance.

Plataforma local de pesquisa, educação e apoio à redação sobre o Direito brasileiro. O backend usa Python, FastAPI, OpenAI Agents SDK, LiteLLM e Google Gemini. A interface usa React, TypeScript e Vite.

A chave `GEMINI_API_KEY` fica somente no `.env` da raiz. Ela não entra no frontend e não deve aparecer em logs.

O Meu Direito é uma ferramenta de pesquisa jurídica. Consulta o texto de artigos de lei federal no Portal da Legislação do Planalto quando a página oficial pode ser lida. A transcrição exibida é a que foi recuperada nessa consulta. A explicação do Gemini é interpretação e não substitui o texto da fonte. Súmulas, jurisprudência e tribunais não são consultados. As respostas são informação geral, não aconselhamento jurídico individualizado e não incluem redação de peças.

O visitante guarda o histórico só no navegador. Esse histórico pode conter dados sensíveis e pode ser apagado nas configurações. O login é opcional: a pesquisa funciona sem conta. Entrar em uma conta não apaga as conversas do navegador e não as envia sozinho. A importação pede confirmação. As conversas criadas na conta ficam no PostgreSQL e aparecem nos aparelhos em que a mesma conta entrar. Cada pergunta enviada ao Gemini continua isolada: o modelo recebe somente a pergunta atual da conversa selecionada. Esta instalação não deve ser publicada na internet sem HTTPS, confirmação de e-mail e controles compatíveis com a LGPD.

## Backend

Na pasta do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

A API fica em [http://127.0.0.1:8000](http://127.0.0.1:8000).

`POST /conversar` recebe `pergunta` e, se informados, `perfil` (`estudante`, `profissional` ou `cidadao`) e `tipo_documento`. A resposta é `{"resposta": "...", "referencias": [...]}`. Cada pergunta é independente e não exige conta.

Com uma sessão ativa, o histórico da conta usa `GET /conta/conversas`, `GET /conta/conversas/{id}`, `POST /conta/conversas/perguntar`, `PATCH /conta/conversas/{id}`, `DELETE /conta/conversas/{id}`, `DELETE /conta/conversas` e `POST /conta/conversas/importar`. Essas rotas só devolvem as conversas do usuário da sessão.

`GET /fontes-oficiais` lista portais oficiais sem consultar tribunais.

`POST /consultar-legislacao` recebe `consulta` e, se informado, `perfil`. A resposta separa `texto_oficial`, `url`, `consultado_em` e `explicacao`. Sem leitura confirmada, `verificada` fica falsa e nenhum artigo é apresentado como verificado.

## Contas e PostgreSQL

O cadastro fica disponível quando o PostgreSQL está no ar. Sem o banco, a pesquisa continua aberta.

```powershell
docker compose up -d
```

A URL já pode estar em `.env`:

```text
DATABASE_URL=postgresql+psycopg://meudireito:meudireito_local@127.0.0.1:5434/meudireito
```

O contêiner publica a porta 5434. A 5432 fica livre para outros PostgreSQL que já estejam nesta máquina.

Ao subir a API, o Alembic aplica as migrações pendentes. As senhas ficam somente como hash Argon2id. A sessão usa cookie HttpOnly. Em HTTP local o cookie não leva a marca Secure; em HTTPS, ou com `COOKIE_SECURE=1`, ela é ativada.

A recuperação de senha responde que o envio de e-mail ainda não está configurado. Ela não simula o envio.

## Frontend

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

A interface abre em [http://localhost:5173](http://localhost:5173).

A URL da API vem de `frontend/.env`:

```text
VITE_API_URL=http://127.0.0.1:8000
```

## Verificação

Na pasta `frontend`:

```powershell
npm run build
```
