import json
import logging

from pydantic import ValidationError

from app.config.settings import settings
from app.schemas.explicacao import ExplicacaoRequest, ExplicacaoResponse
from app.services.ia.prompts import construir_prompts
from app.services.ia.recuperacao import recuperar_informacoes
from app.services.inteligencia_artificial import gerar_resposta_ollama


logger = logging.getLogger(__name__)


def preparar_contexto_ia(dados: ExplicacaoRequest) -> dict:
    """Recupera material e prepara os prompts sem alterar os dados recebidos."""
    consulta = dados.consulta.model_dump()
    recuperacao = recuperar_informacoes(consulta)
    referencias_encontradas = recuperacao["referencias"]

    # A aptidão é o foco da explicação; coloque primeiro o registro que a
    # corresponde. Registros de solo permanecem como complemento.
    referencias_aptidao = [
        referencia
        for referencia in referencias_encontradas
        if "Correspondência de aptidão" in referencia["trecho_utilizado"]
    ]
    referencias_complementares = (
        [
            referencia
            for referencia in referencias_encontradas
            if referencia not in referencias_aptidao
        ]
        if not consulta.get("aptidao_agricola")
        else []
    )
    referencias_priorizadas = referencias_aptidao + referencias_complementares
    limite_referencias = settings.IA_MAX_REFERENCIAS_CONTEXTO
    referencias = referencias_priorizadas[:limite_referencias]
    avisos = list(recuperacao["avisos"])
    if consulta.get("status_consulta") in {"PARCIAL", "SEM_RESULTADOS"}:
        ausentes = ", ".join(consulta.get("dados_ausentes", [])) or "não identificados"
        avisos.append(
            f"A consulta geográfica está {consulta['status_consulta'].casefold()}; "
            f"dados ausentes: {ausentes}. Não trate os campos ausentes como zero."
        )
    desatualizados = consulta.get("dados_desatualizados", [])
    if desatualizados:
        avisos.append(
            "Estes valores foram preservados de uma consulta anterior e não foram "
            "confirmados nesta consulta: " + ", ".join(desatualizados) + "."
        )
    prompts = construir_prompts(consulta, referencias, avisos)

    return {
        "consulta": consulta,
        "referencias": referencias,
        "avisos": avisos,
        "descricao_aptidao": recuperacao["descricao_aptidao"],
        "prompt_sistema": prompts["prompt_sistema"],
        "prompt_usuario": prompts["prompt_usuario"],
    }


def _validar_conteudo_modelo(resposta_modelo: str) -> ExplicacaoResponse:
    """Converte JSON e exige todos os campos obrigatórios do contrato."""
    try:
        resposta_json = json.loads(resposta_modelo)
    except json.JSONDecodeError as erro:
        # Aceita somente um objeto JSON completo, caso o modelo tenha incluído
        # cercas Markdown ou texto externo apesar do formato estruturado.
        inicio = resposta_modelo.find("{")
        profundidade = 0
        dentro_de_string = False
        escape = False
        fim = None
        if inicio >= 0:
            for indice in range(inicio, len(resposta_modelo)):
                caractere = resposta_modelo[indice]
                if dentro_de_string:
                    if escape:
                        escape = False
                    elif caractere == "\\":
                        escape = True
                    elif caractere == '"':
                        dentro_de_string = False
                    continue
                if caractere == '"':
                    dentro_de_string = True
                elif caractere == "{":
                    profundidade += 1
                elif caractere == "}":
                    profundidade -= 1
                    if profundidade == 0:
                        fim = indice + 1
                        break
        if fim is None:
            raise ValueError("O modelo não retornou um objeto JSON completo.") from erro
        try:
            resposta_json = json.loads(resposta_modelo[inicio:fim])
        except json.JSONDecodeError as erro_extracao:
            raise ValueError("O modelo não retornou um objeto JSON válido.") from erro_extracao

    if not isinstance(resposta_json, dict):
        raise ValueError("A resposta JSON do modelo precisa ser um objeto.")

    try:
        return ExplicacaoResponse.model_validate(resposta_json)
    except ValidationError as erro:
        detalhes = "; ".join(
            f"{'.'.join(str(parte) for parte in item['loc'])}: {item['msg']}"
            for item in erro.errors(include_input=False)
        )
        raise ValueError(f"Resposta incompleta ou inválida: {detalhes}") from erro


def _reconciliar_resposta(
    resposta: ExplicacaoResponse,
    referencias_recuperadas: list[dict],
    avisos_recuperacao: list[str],
    consulta: dict,
    descricao_aptidao: str | None,
) -> ExplicacaoResponse:
    """Mantém somente citações canônicas que vieram do catálogo local."""
    por_titulo = {referencia["titulo"]: referencia for referencia in referencias_recuperadas}
    referencias_validas = []
    titulos_incluidos = set()
    citacao_rejeitada = False

    for referencia in resposta.referencias:
        referencia_canonica = por_titulo.get(referencia.titulo)
        if referencia_canonica is None:
            citacao_rejeitada = True
            continue
        if referencia.titulo not in titulos_incluidos:
            referencias_validas.append(referencia_canonica)
            titulos_incluidos.add(referencia.titulo)

    referencia_aptidao_canonica = next(
        (
            referencia
            for referencia in referencias_recuperadas
            if "Correspondência de aptidão" in referencia["trecho_utilizado"]
        ),
        None,
    )
    if (
        descricao_aptidao
        and referencia_aptidao_canonica
        and referencia_aptidao_canonica["titulo"] not in titulos_incluidos
    ):
        referencias_validas.insert(0, referencia_aptidao_canonica)
        titulos_incluidos.add(referencia_aptidao_canonica["titulo"])

    if referencias_recuperadas and not referencias_validas:
        raise ValueError(
            "O modelo não vinculou a explicação a nenhuma referência recuperada."
        )

    avisos = list(dict.fromkeys(
        aviso.strip()
        for aviso in [*resposta.avisos, *avisos_recuperacao]
        if aviso and aviso.strip()
    ))

    if citacao_rejeitada:
        avisos.append(
            "Uma referência indicada pelo modelo não foi confirmada no catálogo e foi descartada."
        )
    if not referencias_validas:
        avisos.append(
            "A explicação não ficou vinculada a uma referência técnica recuperada."
        )

    dados = resposta.model_dump()
    dados["referencias"] = referencias_validas
    dados["avisos"] = list(dict.fromkeys(avisos))

    aptidao = consulta.get("aptidao_agricola")
    aptidao_recebida = isinstance(aptidao, str) and bool(aptidao.strip())
    referencia_aptidao = any(
        "Correspondência de aptidão" in referencia["trecho_utilizado"]
        for referencia in referencias_validas
    )
    # Conserva-se o resumo do modelo apenas quando não há inferência detectada.
    # As demais seções usam a descrição efetivamente presente na legenda local.
    if not aptidao_recebida:
        dados["explicacao"]["dados_recebidos"] = _resumir_dados(consulta)
        dados["explicacao"]["interpretacao_aptidao"] = (
            "A consulta não retornou uma classificação de aptidão agrícola. "
            "Ela não pode ser deduzida dos outros dados."
        )
        dados["avisos"].append(
            "O campo de aptidão agrícola estava ausente ou vazio."
        )
    else:
        aptitude_value = aptidao.strip()
        resumo_modelo = dados["explicacao"]["dados_recebidos"]
        resumo_contem_inferencia = _resumo_contem_inferencia_nao_fundamentada(
            resumo_modelo,
            consulta,
            referencias_validas,
        )
        if aptitude_value.casefold() not in resumo_modelo.casefold() or resumo_contem_inferencia:
            if resumo_contem_inferencia:
                logger.warning(
                    "Resumo do modelo substituído por texto factual: possível inferência sem respaldo."
                )
            dados["explicacao"]["dados_recebidos"] = _resumir_dados(consulta)

        if referencia_aptidao and descricao_aptidao:
            interpretacao = dados["explicacao"]["interpretacao_aptidao"].strip()
            if _interpretacao_contem_inferencia_nao_fundamentada(
                interpretacao,
                descricao_aptidao,
            ):
                logger.warning(
                    "Interpretação do modelo substituída pela legenda: possível inferência sem respaldo."
                )
                interpretacao = (
                    f'A legenda correspondente informa: "{descricao_aptidao}".'
                )
                dados["explicacao"]["interpretacao_aptidao"] = interpretacao
            if descricao_aptidao.casefold() not in interpretacao.casefold():
                dados["explicacao"]["interpretacao_aptidao"] = (
                    interpretacao
                    + f' Legenda de referência: "{descricao_aptidao}".'
                )
        else:
            dados["explicacao"]["interpretacao_aptidao"] = (
                f'Não foi possível recuperar uma descrição única para o símbolo '
                f'"{aptitude_value}". Seu significado não será inferido.'
            )
            dados["avisos"].append(
                f'Não foi recuperada uma Legenda_Ap única para Simb_Apt '
                f'"{aptitude_value}".'
            )

    # Não expor interpretações livres do modelo para dados que o catálogo não
    # explica. Isso também cobre casos sem correspondência direta de aptidão.
    dados["explicacao"]["relacao_variaveis_geoespaciais"] = (
        _texto_variaveis_complementares(consulta, aptidao_recebida)
    )
    if aptidao_recebida and referencia_aptidao and descricao_aptidao:
        dados["explicacao"]["implicacoes_praticas"] = (
            "A legenda informa os níveis de manejo, mas não indica culturas ou produtividade."
        )
        dados["explicacao"]["limitacoes"] = (
            "A explicação se limita à legenda recuperada; ela não informa culturas "
            "ou produtividade."
        )
    elif aptidao_recebida:
        dados["explicacao"]["implicacoes_praticas"] = (
            "Sem uma legenda correspondente única, não é possível indicar uso ou cultivo."
        )
        dados["explicacao"]["limitacoes"] = (
            "O símbolo não será interpretado sem uma correspondência única entre "
            "Simb_Apt e Legenda_Ap."
        )
    else:
        dados["explicacao"]["implicacoes_praticas"] = (
            "Sem a classificação de aptidão, não é possível explicar esse resultado "
            "nem deduzi-lo a partir dos outros campos."
        )
        dados["explicacao"]["limitacoes"] = (
            "O tipo de solo, a altitude e a declividade são apresentados apenas "
            "como dados complementares; não permitem deduzir a aptidão ausente."
        )

    dados["status"] = (
        "concluida"
        if aptidao_recebida and referencia_aptidao and descricao_aptidao
        else "parcial"
    )

    dados["avisos"] = list(dict.fromkeys(dados["avisos"]))

    return ExplicacaoResponse.model_validate(dados)


def _resumir_dados(consulta: dict) -> str:
    """Gera uma frase factual preservando os valores presentes na consulta."""
    partes = []
    aptidao = consulta.get("aptidao_agricola")
    tipo_solo = consulta.get("tipo_solo")
    altitude = consulta.get("altitude_m")
    declividade = consulta.get("declividade_percentual")

    if isinstance(aptidao, str) and aptidao.strip():
        partes.append(f'Aptidão agrícola retornada: "{aptidao.strip()}".')
    else:
        partes.append("A consulta não retornou aptidão agrícola.")
    if isinstance(tipo_solo, str) and tipo_solo.strip():
        partes.append(f'Tipo de solo retornado: "{tipo_solo.strip()}".')
    if altitude is not None:
        partes.append(f"Altitude registrada: {altitude} m.")
    if declividade is not None:
        partes.append(f"Declividade registrada: {declividade}%.")

    return " ".join(partes)


def _resumo_contem_inferencia_nao_fundamentada(
    texto: str,
    consulta: dict,
    referencias: list[dict],
) -> bool:
    """Detecta afirmações de risco simples no resumo gerado pelo modelo."""
    texto_normalizado = texto.casefold()
    material = " ".join(
        [str(valor) for valor in consulta.values() if valor is not None]
        + [referencia["trecho_utilizado"] for referencia in referencias]
    ).casefold()
    termos_de_inferencia = (
        "devido",
        "por causa",
        "em razão",
        "em razao",
        "determina",
        "influencia",
        "influência",
        "resulta",
        "leva a",
        "adequad",
        "apropriad",
        "cultiv",
        "recomend",
        "produtiv",
        "plantio",
        "safra",
        "parque",
        "jardim",
        "lazer",
    )
    return any(
        termo in texto_normalizado and termo not in material
        for termo in termos_de_inferencia
    )


def _interpretacao_contem_inferencia_nao_fundamentada(
    texto: str,
    legenda: str,
) -> bool:
    """Detecta previsões agronômicas não sustentadas pela legenda."""
    texto_normalizado = texto.casefold()
    legenda_normalizada = legenda.casefold()
    termos_de_risco = (
        "com sucesso",
        "podem ser cultiv",
        "pode ser cultiv",
        "podem cultivar",
        "pode cultivar",
        "recomend",
        "produtiv",
        "garant",
        "pode haver",
        "resultará",
        "resultara",
        "será produt",
        "sera produt",
        "adequado para",
        "adequada para",
        "é possível cultivar",
        "e possivel cultivar",
    )
    return any(
        termo in texto_normalizado and termo not in legenda_normalizada
        for termo in termos_de_risco
    )


def _texto_variaveis_complementares(
    consulta: dict,
    aptidao_recebida: bool,
) -> str:
    valores = []
    altitude = consulta.get("altitude_m")
    declividade = consulta.get("declividade_percentual")
    tipo_solo = consulta.get("tipo_solo")

    if isinstance(tipo_solo, str) and tipo_solo.strip():
        valores.append(f'Tipo de solo: "{tipo_solo.strip()}"')
    if altitude is not None:
        valores.append(f"altitude {altitude} m")
    if declividade is not None:
        valores.append(f"declividade {declividade}%")

    if not valores:
        return "Não foram recebidos dados complementares para esta consulta."

    regra = (
        "Esses valores complementam a consulta e não alteram a aptidão recebida."
        if aptidao_recebida
        else "Esses valores não permitem deduzir uma classificação de aptidão."
    )
    return (
        "; ".join(valores)
        + ". "
        + regra
    )


def gerar_explicacao(dados: ExplicacaoRequest) -> ExplicacaoResponse:
    """Coordena recuperação, prompt, geração estruturada e validação."""
    contexto = preparar_contexto_ia(dados)
    schema = ExplicacaoResponse.model_json_schema()
    prompt_usuario = contexto["prompt_usuario"]
    ultimo_erro = None

    for tentativa in range(1, settings.IA_MAX_VALIDATION_ATTEMPTS + 1):
        resposta_modelo = gerar_resposta_ollama(
            prompt_sistema=contexto["prompt_sistema"],
            prompt_usuario=prompt_usuario,
            response_schema=schema,
            num_predict=min(
                settings.OLLAMA_NUM_PREDICT * tentativa,
                4096,
            ),
        )

        try:
            resposta_validada = _validar_conteudo_modelo(resposta_modelo)
            resposta_final = _reconciliar_resposta(
                resposta_validada,
                contexto["referencias"],
                contexto["avisos"],
                contexto["consulta"],
                contexto["descricao_aptidao"],
            )
        except ValueError as erro:
            ultimo_erro = erro
            logger.warning(
                "Resposta do modelo não passou pela validação na tentativa %s/%s: %s",
                tentativa,
                settings.IA_MAX_VALIDATION_ATTEMPTS,
                erro,
            )
            if tentativa < settings.IA_MAX_VALIDATION_ATTEMPTS:
                prompt_usuario += (
                    "\n\nA resposta anterior foi rejeitada pelo validador: "
                    f"{erro}. Gere novamente o objeto completo, preenchendo todos os campos "
                    "obrigatórios e respeitando o schema JSON."
                )
                continue
            break

        return resposta_final

    raise ValueError(
        f"O modelo não produziu uma explicação válida após "
        f"{settings.IA_MAX_VALIDATION_ATTEMPTS} tentativa(s): {ultimo_erro}"
    ) from ultimo_erro
