import csv
from pathlib import Path


# Caminho do catálogo dentro da pasta do serviço de IA.
CAMINHO_CATALOGO = (
    Path(__file__).resolve().parent
    / "catalogo"
    / "aptidao_agricola.csv"
)

ORIGEM_CATALOGO = (
    "Catálogo técnico local (aptidao_agricola.csv). "
    "O arquivo não informa a fonte bibliográfica original."
)


def normalizar_texto(valor):
    """Normaliza espaços e caixa para comparar símbolos e nomes de colunas."""
    if valor is None:
        return ""
    return " ".join(str(valor).strip().casefold().split()).rstrip(".").strip()


def carregar_catalogo():
    """Lê o CSV do catálogo, identificando o separador e a codificação."""
    if not CAMINHO_CATALOGO.exists():
        raise FileNotFoundError(f"Catálogo não encontrado: {CAMINHO_CATALOGO}")

    try:
        arquivo = CAMINHO_CATALOGO.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        arquivo = CAMINHO_CATALOGO.read_text(encoding="latin-1")

    if not arquivo.strip():
        raise ValueError("O catálogo CSV está vazio.")

    try:
        delimitador = csv.Sniffer().sniff(
            arquivo[:5000], delimiters=";,\t|"
        ).delimiter
    except csv.Error:
        delimitador = ";"

    leitor = csv.DictReader(arquivo.splitlines(), delimiter=delimitador)
    if not leitor.fieldnames:
        raise ValueError("Não foi possível identificar as colunas do CSV.")
    return list(leitor)


def recuperar_informacoes(consulta):
    """Recupera a legenda por Simb_Apt e evita escolher entre descrições conflitantes."""
    if hasattr(consulta, "model_dump"):
        consulta = consulta.model_dump()

    registros = carregar_catalogo()
    if not registros:
        raise ValueError("O catálogo CSV não contém registros.")

    colunas = {
        str(coluna).upper(): coluna
        for coluna in registros[0]
        if coluna is not None
    }
    coluna_simbolo = colunas.get("SIMB_APT")
    coluna_legenda = colunas.get("LEGENDA_AP")
    simbolo_recebido = str(consulta.get("aptidao_agricola") or "").strip()
    referencias = []
    avisos = []
    descricao_aptidao = None
    registros_correspondentes = []

    if simbolo_recebido:
        if coluna_simbolo and coluna_legenda:
            registros_correspondentes = [
                registro
                for registro in registros
                if normalizar_texto(registro.get(coluna_simbolo))
                == normalizar_texto(simbolo_recebido)
            ]

            # Só há correspondência segura quando todos os registros do símbolo
            # apontam para exatamente o mesmo texto de legenda.
            legendas = {
                str(registro.get(coluna_legenda)).strip()
                for registro in registros_correspondentes
                if registro.get(coluna_legenda)
                and str(registro.get(coluna_legenda)).strip()
            }

            if len(legendas) == 1:
                descricao_aptidao = next(iter(legendas))
                referencias.append({
                    "titulo": f"Legenda de aptidão {simbolo_recebido}",
                    "origem": ORIGEM_CATALOGO,
                    "trecho_utilizado": (
                        "Correspondência de aptidão validada por Simb_Apt.\n"
                        f"Simb_Apt: {simbolo_recebido}\n"
                        f"Legenda_Ap: {descricao_aptidao}\n"
                        f"Registros verificados: {len(registros_correspondentes)}; "
                        "descrições distintas: 1."
                    ),
                })
            elif len(legendas) > 1:
                avisos.append(
                    "Foram encontradas descrições Legenda_Ap diferentes para "
                    f"Simb_Apt '{simbolo_recebido}'; nenhuma foi escolhida."
                )
            elif registros_correspondentes:
                avisos.append(
                    "O símbolo de aptidão foi encontrado, mas não possui "
                    "Legenda_Ap preenchida no catálogo."
                )
            else:
                avisos.append(
                    "Não foi encontrada correspondência exata em Simb_Apt para "
                    f"a classificação '{simbolo_recebido}'."
                )
        else:
            avisos.append(
                "O catálogo não contém as colunas Simb_Apt e Legenda_Ap "
                "necessárias para explicar a classificação."
            )

    # Solo continua como informação complementar. Quando há aptidão recebida,
    # não se enviam linhas de solo que possam expor legendas concorrentes.
    tipo_solo = normalizar_texto(consulta.get("tipo_solo"))
    if tipo_solo and not simbolo_recebido:
        colunas_solo = [
            colunas[nome]
            for nome in ("LEGENDA", "SOLO_COMP1", "SOLO_COMP2", "SOLO_COMP3", "SOLO_COMP4")
            if nome in colunas
        ]
        for numero_linha, registro in enumerate(registros, start=1):
            if not any(
                normalizar_texto(registro.get(coluna)) == tipo_solo
                for coluna in colunas_solo
            ):
                continue
            trecho = "\n".join(
                f"{coluna}: {valor}"
                for coluna, valor in registro.items()
                if valor is not None and str(valor).strip()
            )
            referencias.append({
                "titulo": f"Registro {numero_linha} do catálogo de solos",
                "origem": ORIGEM_CATALOGO,
                "trecho_utilizado": "Correspondência de solo\n\n" + trecho,
            })

    return {
        "referencias": referencias,
        "avisos": avisos,
        "descricao_aptidao": descricao_aptidao,
        "registros_aptidao_correspondentes": len(registros_correspondentes),
    }
