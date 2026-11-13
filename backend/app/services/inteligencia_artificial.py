import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.settings import settings


logger = logging.getLogger(__name__)


def gerar_resposta_ollama(
    prompt_sistema: str,
    prompt_usuario: str,
    response_schema: dict | None = None,
    num_predict: int | None = None,
) -> str:
    """Envia prompts ao Ollama e devolve o conteúdo produzido pelo modelo."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario},
        ],
        # A API Ollama aceita tanto "json" quanto um JSON Schema no format.
        "format": response_schema or "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": settings.OLLAMA_CONTEXT_LENGTH,
            "num_predict": num_predict or settings.OLLAMA_NUM_PREDICT,
        },
    }
    requisicao = Request(
        settings.OLLAMA_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        logger.info("Solicitando resposta estruturada ao Ollama (%s)", settings.OLLAMA_MODEL)
        with urlopen(requisicao, timeout=settings.OLLAMA_TIMEOUT_SECONDS) as resposta:
            resultado = json.loads(resposta.read().decode("utf-8"))
    except HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        logger.warning("Ollama respondeu com HTTP %s", erro.code)
        raise RuntimeError(
            f"Erro HTTP do Ollama ({erro.code}): {detalhe[:1000]}"
        ) from erro
    except TimeoutError as erro:
        raise RuntimeError(
            f"O Ollama excedeu o tempo limite de {settings.OLLAMA_TIMEOUT_SECONDS:g} segundos."
        ) from erro
    except URLError as erro:
        raise RuntimeError(
            "Não foi possível conectar ao Ollama. Verifique se o serviço está em execução."
        ) from erro
    except json.JSONDecodeError as erro:
        raise RuntimeError("O Ollama retornou uma resposta de transporte inválida.") from erro

    conteudo = resultado.get("message", {}).get("content")
    if not isinstance(conteudo, str) or not conteudo.strip():
        raise RuntimeError("O Ollama não retornou conteúdo para a explicação.")

    if resultado.get("done_reason") == "length":
        logger.warning(
            "Ollama encerrou a geração pelo limite de tokens (eval_count=%s)",
            resultado.get("eval_count"),
        )

    return conteudo
