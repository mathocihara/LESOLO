
from pprint import pprint

from app.services.ia.recuperacao import recuperar_informacoes


def testar_recuperacao():

    consulta_teste = {
        "latitude": -24.95,
        "longitude": -53.45,
        "altitude_m": 755.94,
        "declividade_percentual": 89.9847,
        "tipo_solo": "Área Urbana",
        "aptidao_agricola": "Área urbana"
    }

    print("\n===== TESTE DE RECUPERAÇÃO DO CATÁLOGO =====")

    try:
        resultado = recuperar_informacoes(consulta_teste)

        print("\nREFERÊNCIAS ENCONTRADAS:")
        pprint(resultado["referencias"], sort_dicts=False)

        print("\nAVISOS:")
        pprint(resultado["avisos"], sort_dicts=False)

        print("\nTOTAL DE REFERÊNCIAS:")
        print(len(resultado["referencias"]))

        print("\n===== TESTE FINALIZADO =====")

    except Exception as erro:
        print("\nERRO DURANTE O TESTE:")
        print(f"{type(erro).__name__}: {erro}")


if __name__ == "__main__":
    testar_recuperacao()
