# Meu Direito

O conhecimento jurídico ao seu alcance.

Plataforma local de pesquisa, educação e apoio à redação sobre o Direito brasileiro. O backend usa Python, FastAPI, OpenAI Agents SDK, LiteLLM e Google Gemini. A interface usa React, TypeScript e Vite.

A chave `GEMINI_API_KEY` fica somente no `.env` da raiz. Ela não entra no frontend e não deve aparecer em logs.

O Meu Direito é uma ferramenta de pesquisa jurídica. Consulta o texto de artigos de lei federal no Portal da Legislação do Planalto quando a página oficial pode ser lida. A transcrição exibida é a que foi recuperada nessa consulta. A explicação do Gemini é interpretação e não substitui o texto da fonte. Súmulas, jurisprudência e tribunais não são consultados. As respostas são informação geral, não aconselhamento jurídico individualizado e não incluem redação de peças.

O histórico fica no navegador, pode conter dados sensíveis e pode ser apagado nas configurações. Esta instalação não tem autenticação e não deve ser publicada na internet sem isolamento de dados e controles compatíveis com a LGPD.

## Backend

Na pasta do projeto:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

A API fica em [http://127.0.0.1:8000](http://127.0.0.1:8000).

`POST /conversar` recebe `pergunta` e, se informados, `perfil` (`estudante`, `profissional` ou `cidadao`) e `tipo_documento`. A resposta continua `{"resposta": "..."}`. Cada pergunta é independente.

`GET /fontes-oficiais` lista portais oficiais sem consultar tribunais.

`POST /consultar-legislacao` recebe `consulta` e, se informado, `perfil`. A resposta separa `texto_oficial`, `url`, `consultado_em` e `explicacao`. Sem leitura confirmada, `verificada` fica falsa e nenhum artigo é apresentado como verificado.

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
