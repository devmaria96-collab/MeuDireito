"""Inventário do tratamento realmente feito por esta instalação.

Os textos descrevem o código e as variáveis de ambiente. Não declaram
conformidade com a LGPD e não preenchem responsável, contato ou fornecedor
que não esteja configurado.
"""

from __future__ import annotations

import os

from app.agente import MODELO_GEMINI, _MODELOS_RESERVA
from app.contas import dias_retencao
from app.correio import correio_configurado


def _limpo(nome: str) -> str | None:
    valor = os.getenv(nome, "").strip()
    return valor or None


def _modelos() -> str:
    nomes = [MODELO_GEMINI.removeprefix("gemini/")]
    nomes.extend(nome.removeprefix("gemini/") for nome in _MODELOS_RESERVA)
    return ", ".join(nomes)


def pendencias_administrador() -> list[str]:
    """Lista o que falta configurar, sem inventar responsável, contato ou servidor."""
    pendencias = []
    if not _limpo("CONTROLADOR_PRIVACIDADE"):
        pendencias.append("CONTROLADOR_PRIVACIDADE não está definida. A política não nomeia o responsável.")
    if not _limpo("CONTATO_PRIVACIDADE"):
        pendencias.append("CONTATO_PRIVACIDADE não está definida. Não há canal publicado para os titulares.")
    if not correio_configurado():
        pendencias.append(
            "O SMTP não está configurado. A recuperação de senha e a confirmação de e-mail permanecem pendentes, sem envio simulado."
        )
    if not os.getenv("ORIGENS_PERMITIDAS", "").strip():
        pendencias.append("ORIGENS_PERMITIDAS não tem domínio de produção. O CORS aceita só o ambiente local.")
    if _limpo("NOME_COMERCIAL") and not _limpo("CONTROLADOR_PRIVACIDADE"):
        pendencias.append("NOME_COMERCIAL está definido e não substitui a identificação legal do controlador.")
    return pendencias


def _cookies_de_homologacao() -> list[dict[str, object]]:
    from app.homologacao import ambiente

    if ambiente() != "homologacao":
        return []
    return [
        {
            "nome": "md_acesso",
            "necessario": True,
            "descricao": "Libera a API de homologação. É HttpOnly, dura 12 horas e guarda só um HMAC da senha de acesso. Sem ele a pesquisa não chama o Gemini.",
        },
        {
            "nome": "md_acesso_interface",
            "necessario": True,
            "descricao": "Libera a interface publicada durante a homologação. É HttpOnly no domínio da interface e não substitui o cookie da API.",
        },
    ]


def panorama(requisicao_https: bool) -> dict[str, object]:
    """Devolve o tratamento observado, sem base legal formalizada."""
    dias = dias_retencao()
    if dias == 0:
        retencao_exclusao = "Nenhum dado pessoal da conta é mantido depois da exclusão."
    else:
        retencao_exclusao = (
            f"Por {dias} dias permanece só o resumo criptográfico do e-mail e a data da exclusão. "
            "Nome, foto e conversas não entram nesse registro."
        )
    contato = _limpo("CONTATO_PRIVACIDADE")
    controlador = _limpo("CONTROLADOR_PRIVACIDADE")
    smtp = _limpo("SMTP_HOST") if correio_configurado() else None
    return {
        "conformidade_declarada": False,
        "aviso": "Este texto descreve o tratamento desta instalação. Ele não declara conformidade com a LGPD.",
        "controlador": controlador,
        "marca_comercial": _limpo("NOME_COMERCIAL"),
        "contato": contato,
        "requisicao_https": requisicao_https,
        "recuperacao_de_senha_configurada": correio_configurado(),
        "dias_retencao_exclusao": dias,
        "modelos_gemini": _modelos(),
        "pendencias_administrador": pendencias_administrador(),
        "gemini": {
            "provedor": "Google Gemini, acessado no servidor pela biblioteca LiteLLM. A chave fica só no backend.",
            "enviado": [
                "Na pesquisa, a pergunta atual e a instrução do perfil de linguagem. As mensagens anteriores não são enviadas.",
                "Na explicação de legislação, o trecho oficial já lido no Planalto e o perfil.",
                "Na rota de minuta, os campos do formulário.",
            ],
            "nao_enviado_por_esta_instalacao": [
                "A chave da API não vai ao navegador.",
                "O rastreamento do SDK para a OpenAI está desligado.",
                "Esta instalação não envia o histórico anterior da conversa.",
            ],
            "contrato": (
                "Os termos públicos do Gemini API, consultados em 19/11/2026, separam serviço pago e não pago. "
                "No serviço não pago, o texto público diz que o conteúdo pode ser usado para melhorar produtos e que revisores podem lê-lo. "
                "No serviço pago, o texto público diz que os prompts não são usados para melhorar produtos, que ficam registrados por tempo limitado "
                "para abuso e que podem ser armazenados de forma transitória em qualquer país em que o Google ou seus agentes tenham instalações. "
                "Esta instalação não registra se a chave é de serviço pago, se há aditivo de tratamento aceito nem se o registro de logs do AI Studio está ligado."
            ),
            "transferencia_internacional": (
                "Pendente. Não há evidência neste projeto sobre a região em que o conteúdo desta chave é tratado "
                "nem sobre um mecanismo de transferência adotado pelo responsável."
            ),
        },
        "fornecedores": [
            {
                "nome": "Google Gemini",
                "papel": "Gera a resposta da pesquisa, a explicação de um trecho lido no Planalto e, na rota de minuta, o texto do formulário.",
                "dados": "A pergunta atual, o perfil de linguagem e, quando houver, o trecho oficial já recuperado ou os campos do formulário.",
                "observacao": (
                    "O projeto não registra o país do tratamento, os subprocessadores nem um mecanismo de transferência internacional. "
                    f"Modelos usados: {_modelos()}. O rastreamento do SDK para a OpenAI fica desligado."
                ),
            },
            {
                "nome": "Portal da Legislação do Planalto",
                "papel": "Fonte pública do texto de lei federal.",
                "dados": "O servidor baixa páginas públicas de planalto.gov.br. A pergunta não é enviada como formulário a esse site.",
                "observacao": "A página pode ficar em cache na memória do processo por até uma hora.",
            },
            {
                "nome": "Servidor de e-mail",
                "papel": "Envia o link de redefinição de senha e o de confirmação de e-mail, se estiver configurado.",
                "dados": "Endereço de e-mail da conta e o link com o token. A senha não é enviada.",
                "observacao": f"Servidor configurado: {smtp}." if smtp else "Nenhum servidor de e-mail está configurado. O envio não é simulado.",
            },
        ],
        "inventario": [
            {
                "categoria": "Conta",
                "dados": "E-mail, senha somente como hash Argon2id, nome de exibição e datas de criação e atualização.",
                "finalidade": "Criar a conta opcional, autenticar e permitir acesso, correção e exclusão.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "Enquanto a conta existir. Na exclusão, segue a regra do registro de exclusão.",
                "armazenamento": "PostgreSQL desta instalação.",
            },
            {
                "categoria": "Perfil e foto",
                "dados": "Perfil de linguagem, tema, avatar e, se enviada, a foto convertida para WebP sem metadados.",
                "finalidade": "Mostrar a preferência da própria conta.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "Enquanto a conta existir. A foto é apagada do disco na exclusão da conta.",
                "armazenamento": "PostgreSQL e arquivo em dados/avatares, nomeado pelo identificador da conta.",
            },
            {
                "categoria": "Sessão",
                "dados": "Hash do cookie de sessão, token CSRF e datas. O cookie em si não fica no banco.",
                "finalidade": "Reconhecer a conta e autorizar alterações.",
                "base_legal": "Não formalizada. O cookie é estritamente necessário para a conta que a pessoa pediu.",
                "retencao": "A sessão ativa dura 14 dias ou até ser encerrada. Sessões revogadas permanecem até a exclusão da conta.",
                "armazenamento": "PostgreSQL e cookie HttpOnly md_sessao no navegador.",
            },
            {
                "categoria": "Redefinição de senha",
                "dados": "Hash do token, validade de 30 minutos e data de uso.",
                "finalidade": "Permitir uma nova senha sem revelar se o e-mail tem cadastro e sem enviar a senha.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "O token deixa de valer após o uso ou 30 minutos. O registro permanece até a exclusão da conta.",
                "armazenamento": "PostgreSQL. O e-mail só sai se o SMTP estiver configurado.",
            },
            {
                "categoria": "Conversas da conta",
                "dados": "Título, perguntas, respostas e referências jurídicas recuperadas.",
                "finalidade": "Mostrar o histórico nos aparelhos em que a mesma conta entrar.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "Até a pessoa apagar a conversa, apagar o histórico ou excluir a conta. Não há prazo automático.",
                "armazenamento": "PostgreSQL, isolado por conta. A pergunta atual é enviada ao Google Gemini; as anteriores não.",
            },
            {
                "categoria": "Histórico do visitante",
                "dados": "Conversas guardadas no navegador, sem conta.",
                "finalidade": "Continuar a pesquisa neste navegador.",
                "base_legal": "Não formalizada. O armazenamento no navegador é opcional e depende da escolha da pessoa.",
                "retencao": "Até a pessoa apagar o histórico, recusar o armazenamento opcional ou limpar os dados do site. Não há cópia no servidor.",
                "armazenamento": "localStorage do navegador.",
            },
            {
                "categoria": "Documentos",
                "dados": "Campos enviados à rota de minuta, quando ela é usada.",
                "finalidade": "Gerar um arquivo para baixar.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "O aplicativo não grava a minuta. Não há prazo de retenção no servidor porque não há arquivo armazenado.",
                "armazenamento": "Nenhum no servidor. A geração envia os campos ao Google Gemini.",
            },
            {
                "categoria": "Avaliação da resposta",
                "dados": "Somente positiva ou negativa e, se negativa, um motivo de uma lista fixa.",
                "finalidade": "Registrar a qualidade percebida, sem o texto da conversa e sem identificar a conta.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "O arquivo permanece até alguém apagá-lo. Não há prazo automático e a exclusão da conta não o altera.",
                "armazenamento": "Arquivo local dados/feedback.jsonl.",
            },
            {
                "categoria": "Registro de exclusão",
                "dados": "Resumo criptográfico do e-mail e a data, apenas se o prazo configurado for maior que zero.",
                "finalidade": "Atender um prazo de retenção definido por quem opera a instalação.",
                "base_legal": "Não formalizada. O padrão atual não retém dado pessoal.",
                "retencao": retencao_exclusao,
                "armazenamento": "PostgreSQL, tabela registros_exclusao.",
            },
            {
                "categoria": "Registros técnicos",
                "dados": "Eventos do processo, como falha de envio ou tipo de erro. A pergunta, a senha e a chave não devem entrar no log.",
                "finalidade": "Operar e diagnosticar o serviço.",
                "base_legal": "Não formalizada. Depende de o responsável validar a hipótese aplicável.",
                "retencao": "Não há prazo configurado. O destino é a saída do processo, sem rotina de arquivo.",
                "armazenamento": "Saída do processo da API.",
            },
            {
                "categoria": "Cópias de segurança",
                "dados": "Nenhuma rotina de backup faz parte do aplicativo.",
                "finalidade": "Não há finalidade de backup implementada.",
                "base_legal": "Não se aplica enquanto não existir cópia.",
                "retencao": "Não há prazo porque o aplicativo não gera backup. O volume do PostgreSQL permanece na máquina até quem opera removê-lo.",
                "armazenamento": "Volume local do Docker, quando o banco está em execução. Sem cópia externa configurada.",
            },
        ],
        "cookies": [
            {
                "nome": "md_sessao",
                "necessario": True,
                "descricao": "Mantém a conta autenticada. É HttpOnly. SameSite fica Lax, ou Strict se configurado. None só é usado junto com Secure. A marca Secure entra em HTTPS ou quando COOKIE_SECURE está ativo. Dura 14 dias.",
            },
            {
                "nome": "sessionStorage da aba",
                "necessario": True,
                "descricao": "Lembra a escolha de não importar conversas nesta aba e restaura tema e perfil ao entrar ou sair. Some quando a aba fecha.",
            },
            {
                "nome": "meu-direito.consentimento",
                "necessario": True,
                "descricao": "Guarda somente a escolha sobre o armazenamento opcional, para não perguntar de novo nem gravar o que foi recusado.",
            },
            {
                "nome": "meu-ia.tema e meu-direito.perfil",
                "necessario": False,
                "descricao": "Lembram tema e perfil de linguagem neste navegador. Não são necessários para pesquisar.",
            },
            {
                "nome": "meu-direito.conversas",
                "necessario": False,
                "descricao": "Guarda o histórico de quem pesquisa sem conta. Pode conter dado pessoal escrito na pergunta.",
            },
            *_cookies_de_homologacao(),
        ],
        "direitos": [
            "Consultar esta descrição e baixar os dados da conta em JSON.",
            "Corrigir nome, avatar, foto, perfil de linguagem e tema. A troca de e-mail ainda não existe.",
            "Apagar uma conversa, todo o histórico da conta ou a conta, com confirmação.",
            "Encerrar sessões e recusar o armazenamento opcional do navegador.",
            "Oposição, revisão humana e reclamação não têm fluxo dentro do aplicativo. Dependem do canal de contato, que só aparece se estiver configurado.",
        ],
        "criancas": (
            "O Meu Direito não pede idade e não é dirigido a crianças ou adolescentes. "
            "Não há verificação de idade nem regra específica do art. 14 da LGPD registrada. "
            "Uma pergunta ainda pode mencionar uma criança. Isso exige decisão jurídica antes da publicação."
        ),
        "sensiveis_e_terceiros": (
            "Não há campo próprio para dado pessoal sensível. A pergunta, a foto e os campos de minuta podem conter "
            "dado sensível ou informação de outra pessoa. O sistema não separa esse conteúdo e, na pesquisa, envia a pergunta atual ao Google Gemini."
        ),
        "treinamento": (
            "Esta instalação não usa o conteúdo das conversas para treinamento nem para análise adicional. "
            "Isso não descreve o tratamento feito pelo Google: o regime da chave não está registrado aqui."
        ),
        "incidentes": (
            "Não há comunicação automática à ANPD nem aos titulares. "
            "Um incidente com risco ou dano relevante exige avaliação jurídica sobre a comunicação, nos termos do art. 48 da LGPD. "
            "O registro deve ter data, natureza dos dados, titulares afetados e medidas adotadas, sem copiar senha, chave ou conteúdo das conversas. "
            "O canal publicado para os titulares é somente o configurado em CONTATO_PRIVACIDADE."
        ),
    }
