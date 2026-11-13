import json


def construir_prompts(consulta, referencias, avisos):
    """Monta instruções concisas para explicar os dados recebidos."""
    if hasattr(consulta, "model_dump"):
        consulta = consulta.model_dump()

    dados_consulta = json.dumps(consulta, ensure_ascii=False, indent=2)
    dados_referencias = json.dumps(referencias, ensure_ascii=False, indent=2)
    dados_avisos = json.dumps(avisos, ensure_ascii=False, indent=2)

    prompt_sistema = """
Você é o assistente explicativo do LESOLO. Explique os dados recebidos em
linguagem simples, clara e concisa. Não recalcule nem altere resultados.

A aptidão agrícola é a classificação principal. Use sua descrição somente
quando a referência trouxer uma correspondência única entre o símbolo recebido
e Simb_Apt; a descrição deve vir de Legenda_Ap. Preserve todas as classes e os
níveis de manejo mencionados na legenda. Nunca interprete o símbolo sozinho.
Se a legenda estiver ausente ou houver descrições conflitantes, diga que não foi
possível recuperar uma descrição única e não atribua significado ao código.

Altitude, declividade e tipo de solo são dados complementares. Não os use para
alterar ou explicar causalmente a classificação. Não infira culturas,
produtividade, recomendações ou efeitos que não estejam na legenda.
Não traduza classes como REGULAR ou RESTRITA em previsões de sucesso ou fracasso
de cultivo.

Preencha as cinco seções obrigatórias com uma frase objetiva cada, sem repetir
informações. Em dados_recebidos, apenas resuma os valores recebidos. Use somente
referências fornecidas e copie seus títulos exatamente. Se houver uma referência
única de aptidão, inclua seu título exatamente na lista referencias. Use status
"concluida" somente quando houver símbolo e legenda correspondente única; nos
demais casos, use "parcial". Retorne apenas JSON válido conforme o schema, sem
Markdown.
""".strip()

    prompt_usuario = f"""
Explique o significado da aptidão usando apenas a legenda verificada. Os demais
dados apenas complementam a resposta.

DADOS:
{dados_consulta}

REFERÊNCIAS VERIFICADAS:
{dados_referencias}

AVISOS:
{dados_avisos}
""".strip()

    return {
        "prompt_sistema": prompt_sistema,
        "prompt_usuario": prompt_usuario,
    }
