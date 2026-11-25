const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

function errorMessage(payload, status) {
  const detail = payload?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail.message === 'string') return detail.message
  if (Array.isArray(detail)) return detail.map((item) => item.msg || 'Dados inválidos.').join(' ')
  return `A API retornou um erro (HTTP ${status}).`
}

export async function apiRequest(path, { method = 'GET', body, signal } = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      credentials: 'include',
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Não foi possível conectar à API. Verifique se o backend está em execução.')
  }
  if (response.status === 204) return null
  let payload
  try { payload = await response.json() } catch { payload = null }
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('lesolo:session-expired'))
    const error = new Error(errorMessage(payload, response.status))
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload
}

export const login = (body) => apiRequest('/api/usuarios/login', { method: 'POST', body })
export const cadastrar = (body) => apiRequest('/api/usuarios/cadastro', { method: 'POST', body })
export const cadastrarUsuario = cadastrar
export const logout = () => apiRequest('/api/usuarios/logout', { method: 'POST' })
export const entrar = login
export const sair = logout
export const obterUsuarioAtual = () => apiRequest('/api/usuarios/me')
export const atualizarConta = (body) => apiRequest('/api/usuarios/me', { method: 'PATCH', body })
export const excluirConta = (body) => apiRequest('/api/usuarios/me', { method: 'DELETE', body })
export const listarHistorico = (status) => apiRequest(`/api/historico${status ? `?status=${encodeURIComponent(status)}` : ''}`)
export const criarRegistroTemporario = (body) => apiRequest('/api/historico/temporario', { method: 'POST', body })
export const obterRegistro = (id) => apiRequest(`/api/historico/${id}`)
export const salvarRegistro = (id, nome) => apiRequest(`/api/historico/${id}/salvar`, { method: 'POST', body: nome ? { nome } : {} })
export const excluirRegistro = (id) => apiRequest(`/api/historico/${id}`, { method: 'DELETE' })
export const excluirHistorico = () => apiRequest('/api/historico', { method: 'DELETE' })
export const obterPreferencias = () => apiRequest('/api/preferencias')
export const atualizarPreferencias = (body) => apiRequest('/api/preferencias', { method: 'PUT', body })
