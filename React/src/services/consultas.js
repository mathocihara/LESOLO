import { apiRequest } from './api.js'

export function consultarCoordenada({ latitude, longitude }, { signal, acaoRepeticao, registroId } = {}) {
  return apiRequest('/api/consultas/consultar', {
    method: 'POST', body: {
      latitude: Number(latitude),
      longitude: Number(longitude),
      ...(acaoRepeticao ? { acao_repeticao: acaoRepeticao } : {}),
      ...(registroId ? { registro_id: registroId } : {}),
    }, signal,
  })
}

export function solicitarExplicacao(consulta, { signal } = {}) {
  return apiRequest('/api/explicacao', { method: 'POST', body: { consulta }, signal })
}
