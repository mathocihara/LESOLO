const API_URL = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
).replace(/\/+$/, '')

function mensagemDaResposta(payload, status) {
  const detail = payload?.detail

  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || 'Dados inválidos.').join(' ')
  }
  if (detail && typeof detail === 'object') return JSON.stringify(detail)

  return `A API retornou um erro (HTTP ${status}).`
}

export async function consultarCoordenada({ latitude, longitude }, { signal } = {}) {
  let response

  try {
    response = await fetch(`${API_URL}/api/consultas/consultar`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude: Number(latitude),
        longitude: Number(longitude),
      }),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error

    throw new Error(
      'Não foi possível conectar à API. Verifique se o backend está em execução em http://127.0.0.1:8000.',
    )
  }

  let payload
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    throw new Error(mensagemDaResposta(payload, response.status))
  }

  return payload
}
