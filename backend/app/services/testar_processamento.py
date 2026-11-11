
from app.services.processamento_geo import consultar_coordenada

resultado = consultar_coordenada(
    latitude=-24.95,
    longitude=-53.45
)

print("\n===== RESULTADO DA CONSULTA =====")

for chave, valor in resultado.items():
    print(f"{chave}: {valor}")
