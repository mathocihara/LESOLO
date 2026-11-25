import { useEffect, useState } from 'react'
import SideMenu from '../components/SideMenu.jsx'
import BottomMenu from '../components/BottomMenu.jsx'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import Acessibilidade from './Acessibilidade.jsx'
import Registros from './Registros.jsx'
import EditarConta from './EditarConta.jsx'
import FecharConta from './FecharConta.jsx'
import Perfil from './Perfil.jsx'
import { consultarCoordenada, solicitarExplicacao } from '../services/consultas.js'
import { listarHistorico, salvarRegistro, excluirRegistro, obterPreferencias, atualizarPreferencias, excluirHistorico } from '../services/api.js'

const metricFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

function formatMetric(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return metricFormatter.format(value)
}

function valueWithFreshness(result, field, value) {
  if (value === null || value === undefined || value === '') return value
  return (result.dados_desatualizados || []).includes(field)
    ? `Dado anterior: ${value} (não atualizado nesta consulta)`
    : value
}

const geographicLabels = {
  altitude_m: 'altitude',
  declividade_percentual: 'declividade',
  tipo_solo: 'tipo de solo',
  aptidao_agricola: 'aptidão agrícola',
}

function buildExplanationSummary(result, explanation) {
  const content = explanation?.explicacao || {}
  const parts = []
  const declividade = formatMetric(result?.declividade_percentual)
  const altitude = formatMetric(result?.altitude_m)
  const tipoSolo = typeof result?.tipo_solo === 'string' ? result.tipo_solo.trim() : ''
  const aptidao = typeof result?.aptidao_agricola === 'string'
    ? result.aptidao_agricola.trim()
    : ''

  if (declividade !== null) {
    parts.push((result?.dados_desatualizados || []).includes('declividade_percentual')
      ? `A declividade ${declividade}% é um valor anterior, não confirmado nesta consulta.`
      : `A declividade registrada é ${declividade}%.`)
  }
  if (tipoSolo) {
    parts.push((result?.dados_desatualizados || []).includes('tipo_solo')
      ? `O tipo de solo "${tipoSolo}" é um valor anterior, não confirmado nesta consulta.`
      : `O tipo de solo informado é "${tipoSolo}".`)
  }
  if (altitude !== null) {
    parts.push((result?.dados_desatualizados || []).includes('altitude_m')
      ? `A altitude ${altitude} m é um valor anterior, não confirmado nesta consulta.`
      : `A altitude registrada é ${altitude} m.`)
  }

  if (content.interpretacao_aptidao && !(result?.dados_desatualizados || []).includes('aptidao_agricola')) {
    parts.push(content.interpretacao_aptidao)
  } else if (aptidao) {
    parts.push((result?.dados_desatualizados || []).includes('aptidao_agricola')
      ? `A aptidão agrícola "${aptidao}" é um valor anterior, não confirmado nesta consulta.`
      : `A aptidão agrícola retornada pelo sistema é "${aptidao}".`)
  } else {
    parts.push('A consulta não retornou uma classificação de aptidão agrícola.')
  }

  if (tipoSolo || declividade !== null || altitude !== null) {
    parts.push(
      aptidao
        ? 'Esses dados complementam a consulta e não alteram a aptidão agrícola retornada.'
        : 'Esses dados complementam a consulta, mas não permitem deduzir a aptidão agrícola.',
    )
  }

  const fechamento = explanation?.status === 'parcial'
    ? content.implicacoes_praticas
    : content.limitacoes
  if (fechamento) {
    parts.push(fechamento)
  }

  return parts.join(' ')
}

function ResultIcon({ name }) {
  return (
    <svg
      className="result-card__svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {name === 'altitude' && (
        <>
          <path d="M3 20h18L14 7l-4 6-2-3-5 10Z" />
          <path d="M18 3v6m-2.5-3.5L18 3l2.5 2.5" />
        </>
      )}
      {name === 'slope' && (
        <>
          <path d="M4 19h16L4 5v14Z" />
          <path d="M8 19v-4h4" />
        </>
      )}
      {name === 'soil' && (
        <>
          <path d="M4 6c2 2 4-2 8 0s6 2 8 0" />
          <path d="M4 12c2 2 4-2 8 0s6 2 8 0" />
          <path d="M4 18c2 2 4-2 8 0s6 2 8 0" />
        </>
      )}
      {name === 'agriculture' && (
        <>
          <path d="M12 21v-9" />
          <path d="M12 13c0-5-3-7-8-7 0 5 2 8 8 8" />
          <path d="M12 11c0-4 2-6 7-6 0 4-2 7-7 8" />
          <path d="M5 21h14" />
        </>
      )}
    </svg>
  )
}

function ResultCard({ label, value, unit, icon }) {
  const hasValue = value !== null && value !== undefined && value !== ''

  return (
    <article className="result-card">
      <span className="result-card__icon">
        <ResultIcon name={icon} />
      </span>
      <div className="result-card__content">
        <h2 className="result-card__title">{label}</h2>
        <p className={`result-card__value${hasValue ? '' : ' result-card__value--empty'}`}>
          <span>{hasValue ? value : 'Sem dados'}</span>
          {hasValue && unit && <span className="result-card__unit">{unit}</span>}
        </p>
      </div>
    </article>
  )
}

function formatCoordinate(value) {
  const normalized = String(value ?? '').replace(',', '.')
  const negative = normalized.startsWith('-')
  const cleaned = normalized.replace(/-/g, '').replace(/[^\d.]/g, '')
  const decimalIndex = cleaned.indexOf('.')

  if (decimalIndex === -1) {
    return `${negative ? '-' : ''}${cleaned}`
  }

  const integerPart = cleaned.slice(0, decimalIndex)
  const decimalPart = cleaned.slice(decimalIndex + 1).replace(/\./g, '')

  return `${negative ? '-' : ''}${integerPart}.${decimalPart}`
}

function parseCoordinate(value) {
  if (!value || value === '-' || value === '.' || value === '-.') {
    return Number.NaN
  }

  return Number(value)
}

const A11Y_STORAGE_KEY = 'lesolo:acessibilidade'
function loadAccessibility() {
  try { return { ampliadores: false, leitores: false, teclado: false, ...JSON.parse(localStorage.getItem(A11Y_STORAGE_KEY) || '{}') } }
  catch { return { ampliadores: false, leitores: false, teclado: false } }
}

export default function Home({ user, onLogout, onUserUpdate }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [sideSelected, setSideSelected] = useState('')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [explanationLoading, setExplanationLoading] = useState(false)
  const [explanationError, setExplanationError] = useState('')
  const [explanation, setExplanation] = useState(null)
  const [history, setHistory] = useState([])
  const [preferences, setPreferences] = useState(null)
  const [panelError, setPanelError] = useState('')
  const [temporaryRecord, setTemporaryRecord] = useState(null)
  const [duplicatePrompt, setDuplicatePrompt] = useState(null)
  const [accessibility, setAccessibility] = useState(loadAccessibility)

  async function refreshHistory() {
    const [temporarios, permanentes] = await Promise.all([
      listarHistorico('TEMPORARIO'),
      listarHistorico('PERMANENTE'),
    ])
    const todos = [...temporarios, ...permanentes].sort(
      (a, b) => new Date(b.data_consulta) - new Date(a.data_consulta),
    )
    setHistory(todos)
    return todos
  }

  useEffect(() => {
    obterPreferencias().then(setPreferences).catch((e) => setPanelError(e.message))
  }, [])

  useEffect(() => {
    if (sideSelected === 'historico') refreshHistory().catch((e) => setPanelError(e.message))
  }, [sideSelected])

  useEffect(() => {
    if (!preferences) return
    document.documentElement.dataset.theme = preferences.tema
    document.documentElement.dataset.contrast = preferences.alto_contraste ? 'high' : 'normal'
  }, [preferences])

  useEffect(() => {
    document.documentElement.dataset.textSize = accessibility.ampliadores ? 'large' : 'normal'
    document.documentElement.dataset.screenReader = accessibility.leitores ? 'enhanced' : 'normal'
    document.documentElement.dataset.keyboardMode = accessibility.teclado ? 'quick' : 'normal'
    localStorage.setItem(A11Y_STORAGE_KEY, JSON.stringify(accessibility))
  }, [accessibility])

  useEffect(() => {
    if (!accessibility.teclado) return
    const handleShortcut = (event) => {
      if (!event.altKey || event.ctrlKey || event.metaKey) return
      const target = event.key.toLowerCase() === 'l' ? 'latitude' : event.key.toLowerCase() === 'o' ? 'longitude' : null
      if (target) { event.preventDefault(); document.getElementById(target)?.focus() }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [accessibility.teclado])

  function handleSideSelect(id) {
    if (id === 'sair') {
      setMenuOpen(false)
      onLogout?.()
      return
    }
    setSideSelected(id === 'painel' ? '' : id)
    setMenuOpen(false)
    setPanelError('')
  }

  function openAccountSettings() {
    setSideSelected('config-conta')
  }

  function onOpenAccessibility(){
    setSideSelected('acessibilidade')
  }

  function startNewConsultation() {
    setMenuOpen(false)
    setSideSelected('')
    setLatitude('')
    setLongitude('')
    setResult(null)
    setTemporaryRecord(null)
    setExplanation(null)
    setDuplicatePrompt(null)
  }

  function toggleAccessibility(key, value) {
    setAccessibility((current) => ({ ...current, [key]: value }))
  }

  function openRecord(record) {
    setLatitude(String(record.latitude)); setLongitude(String(record.longitude))
    setResult({ altitude_m: record.altitude_m == null ? null : Number(record.altitude_m), declividade_percentual: record.declividade_percentual == null ? null : Number(record.declividade_percentual), tipo_solo: record.tipo_solo, aptidao_agricola: record.aptidao_agricola, status_consulta: record.status_consulta, dados_ausentes: record.dados_ausentes || [], falhas_fontes: record.falhas_fontes || [], dados_desatualizados: record.dados_desatualizados || [] })
    setTemporaryRecord(null); setExplanation(null); setSideSelected('')
  }

  async function deleteRecord(record) {
    if (!window.confirm('Excluir este registro?')) return
    try { await excluirRegistro(record.id); await refreshHistory() }
    catch (requestError) { setPanelError(requestError.message) }
  }

  async function clearHistory() {
    if (!window.confirm('Limpar todo o histórico permanente?')) return
    try { await excluirHistorico(); await refreshHistory() }
    catch (requestError) { setPanelError(requestError.message) }
  }

  async function changePreference(patch) {
    try { setPreferences(await atualizarPreferencias(patch)) }
    catch (requestError) { setPanelError(requestError.message) }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setResult(null)
    setExplanationError('')
    setExplanation(null)
    setDuplicatePrompt(null)

    const parsedLatitude = parseCoordinate(latitude)
    const parsedLongitude = parseCoordinate(longitude)

    if (!Number.isFinite(parsedLatitude) || !Number.isFinite(parsedLongitude)) {
      setError('Informe uma latitude e uma longitude válidas.')
      return
    }

    if (parsedLatitude < -90 || parsedLatitude > 90) {
      setError('A latitude deve estar entre -90 e 90.')
      return
    }

    if (parsedLongitude < -180 || parsedLongitude > 180) {
      setError('A longitude deve estar entre -180 e 180.')
      return
    }

    await executarConsulta({ latitude: parsedLatitude, longitude: parsedLongitude })
  }

  async function executarConsulta(coordenadas, decisao = {}) {
    setLoading(true)
    try {
      const data = await consultarCoordenada(coordenadas, decisao)
      setResult(data)
      setTemporaryRecord(data.id && data.status === 'TEMPORARIO' ? { id: data.id } : null)
      setDuplicatePrompt(null)
    } catch (requestError) {
      const detail = requestError.payload?.detail
      if (requestError.status === 409 && detail?.code === 'CONSULTA_REPETIDA') {
        setDuplicatePrompt({ coordenadas, registros: detail.registros || [] })
      } else {
        setError(requestError.message || 'Não foi possível concluir a consulta.')
      }
    } finally {
      setLoading(false)
    }
  }

  function prosseguirConsulta(acaoRepeticao, registroId) {
    if (!duplicatePrompt) return
    const coordenadas = duplicatePrompt.coordenadas
    setDuplicatePrompt(null)
    executarConsulta(coordenadas, { acaoRepeticao, registroId })
  }

  async function handleExplain() {
    if (!result) return

    setExplanationError('')
    setExplanation(null)
    setExplanationLoading(true)

    try {
      const data = await solicitarExplicacao(result)
      setExplanation(data)
    } catch (requestError) {
      setExplanationError(
        requestError.message || 'Não foi possível gerar a explicação.',
      )
    } finally {
      setExplanationLoading(false)
    }
  }

  return (
    <div className="painel">
      <header className="painel-header">
        <SideMenu open={menuOpen} selected={sideSelected || 'painel'} onSelect={handleSideSelect} onToggle={setMenuOpen} />
      </header>

      <main className="painel-body" aria-live={accessibility.leitores ? 'polite' : undefined}>
        {panelError && <div role="alert"><ErrorMessage>{panelError}</ErrorMessage></div>}
        {sideSelected === 'historico' && <Registros records={history} onOpen={openRecord} onDelete={deleteRecord} onSave={async (record) => { try { await salvarRegistro(record.id); await refreshHistory() } catch (e) { setPanelError(e.message) } }} onClear={clearHistory} onBack={() => handleSideSelect('painel')} />}
        {sideSelected === 'perfil' && <Perfil user={user} preferences={preferences} onPreference={changePreference} onOpenAccountSettings={openAccountSettings} onOpenAccessibility={onOpenAccessibility} onBack={() => handleSideSelect('painel')} />}
        {sideSelected === 'config-conta' && <EditarConta user={user} onUpdated={onUserUpdate} onOpenCloseAccount={() => setSideSelected('fechar-conta')} onBack={() => setSideSelected('perfil')} />}
        {sideSelected === 'fechar-conta' && <FecharConta onBack={() => setSideSelected('config-conta')} />}
        {sideSelected === 'acessibilidade' && <Acessibilidade preferences={{ ...accessibility, tema: preferences?.tema || 'escuro', alto_contraste: Boolean(preferences?.alto_contraste) }} onToggle={toggleAccessibility} onTheme={(tema) => changePreference({ tema })} onContrast={(alto_contraste) => changePreference({ alto_contraste })} onBack={() => setSideSelected('perfil')} />}
        {(sideSelected === 'sobre' || sideSelected === 'como-funciona' || sideSelected === 'erro') && <section className="location-section"><h1 className="location-section__title">{sideSelected === 'sobre' ? 'Sobre o Lê Solo' : sideSelected === 'como-funciona' ? 'Como funciona' : 'Reportar problema'}</h1><p>{sideSelected === 'sobre' ? 'Aplicação para consulta de informações relacionadas à aptidão agrícola das terras.' : sideSelected === 'como-funciona' ? 'Informe latitude e longitude para consultar altitude, declividade, tipo de solo e aptidão agrícola disponíveis para o local.' : 'Para relatar um problema, informe as coordenadas consultadas e a mensagem de erro exibida ao responsável pelo projeto.'}</p></section>}
        <section className="location-section" aria-labelledby="location-title" style={{ display: sideSelected ? 'none' : undefined }}>
          <h1 id="location-title" className="location-section__title">
            Localização atual
          </h1>

          <form className="location-form" onSubmit={handleSubmit} aria-busy={loading}>
            <div className="location-section__fields">
              <label className="location-field" htmlFor="latitude">
                <span className="location-field__label">Latitude</span>
                <input
                  id="latitude"
                  className="location-field__input"
                  type="text"
                  inputMode="decimal"
                  value={latitude}
                  placeholder="Inserir valor"
                  disabled={loading || Boolean(duplicatePrompt)}
                  onChange={(event) => setLatitude(formatCoordinate(event.target.value))}
                />
              </label>

              <label className="location-field" htmlFor="longitude">
                <span className="location-field__label">Longitude</span>
                <input
                  id="longitude"
                  className="location-field__input"
                  type="text"
                  inputMode="decimal"
                  value={longitude}
                  placeholder="Inserir valor"
                  disabled={loading || Boolean(duplicatePrompt)}
                  onChange={(event) => setLongitude(formatCoordinate(event.target.value))}
                />
              </label>
            </div>

            <Button variant="primary" type="submit" disabled={loading || Boolean(duplicatePrompt)}>
              {loading ? 'Consultando...' : 'Consultar'}
            </Button>
          </form>

          {duplicatePrompt && <section className="duplicate-consultation" role="group" aria-labelledby="duplicate-consultation-title">
            <h2 id="duplicate-consultation-title">Já existe consulta para estas coordenadas</h2>
            <p>Latitude {duplicatePrompt.coordenadas.latitude.toFixed(6)}, longitude {duplicatePrompt.coordenadas.longitude.toFixed(6)}. Escolha criar outro registro ou atualizar um dos anteriores.</p>
            <Button variant="primary" type="button" onClick={() => prosseguirConsulta('NOVO')}>Criar novo registro</Button>
            <div className="duplicate-consultation__records">{duplicatePrompt.registros.map((record) => <div key={record.id}>
              <span>{record.status === 'TEMPORARIO' ? 'Temporário' : 'Permanente'} · {record.nome || 'Consulta'} · {new Date(record.data_consulta).toLocaleString('pt-BR')}</span>
              <Button variant="secondary" type="button" onClick={() => prosseguirConsulta('ATUALIZAR', record.id)}>Atualizar este registro</Button>
            </div>)}</div>
            <Button variant="secondary" type="button" onClick={() => setDuplicatePrompt(null)}>Cancelar consulta</Button>
          </section>}

          {loading && <p role="status">Consultando coordenadas...</p>}
          {error && (
            <div role="alert">
              <ErrorMessage>{error}</ErrorMessage>
            </div>
          )}
          {result && (
            <>
              {temporaryRecord && <Button variant="success" type="button" onClick={async () => { try { await salvarRegistro(temporaryRecord.id); setTemporaryRecord(null); await refreshHistory(); setSideSelected('historico') } catch(e) { setPanelError(e.message) } }}>Salvar consulta no histórico</Button>}
              {result.status_consulta === 'PARCIAL' && <p role="status">Consulta parcial. Não foram obtidos: {(result.dados_ausentes || []).map((key) => geographicLabels[key] || key).join(', ') || 'dados não identificados'}.{result.falhas_fontes?.length ? ` Falha nas fontes: ${result.falhas_fontes.map((key) => geographicLabels[key] || key).join(', ')}.` : ''}</p>}
              {result.status_consulta === 'SEM_RESULTADOS' && <p role="status">{result.falhas_fontes?.length ? `Não foi possível obter resultados. Falha nas fontes: ${result.falhas_fontes.map((key) => geographicLabels[key] || key).join(', ')}.` : 'As fontes consultadas não retornaram dados para estas coordenadas.'}</p>}
              <section className="results-grid" aria-label="Resultados geoespaciais">
                <ResultCard
                  label="Altitude (MDE)"
                  value={valueWithFreshness(result, 'altitude_m', formatMetric(result.altitude_m))}
                  unit="m"
                  icon="altitude"
                />
                <ResultCard
                  label="Declividade"
                  value={valueWithFreshness(result, 'declividade_percentual', formatMetric(result.declividade_percentual))}
                  unit="%"
                  icon="slope"
                />
                <ResultCard
                  label="Tipo de solo"
                  value={valueWithFreshness(result, 'tipo_solo', result.tipo_solo)}
                  icon="soil"
                />
                <ResultCard
                  label="Aptidão agrícola"
                  value={valueWithFreshness(result, 'aptidao_agricola', result.aptidao_agricola)}
                  icon="agriculture"
                />
              </section>

              <section className="explanation-panel" aria-labelledby="explanation-title">
                <h2 id="explanation-title" className="explanation-panel__title">
                  Interpretação dos resultados
                </h2>
                <Button
                  variant="primary"
                  type="button"
                  disabled={explanationLoading}
                  onClick={handleExplain}
                >
                  {explanationLoading ? 'Gerando explicação...' : 'Gerar explicação'}
                </Button>

                {explanationLoading && (
                  <p role="status">A IA está analisando os resultados e as referências técnicas.</p>
                )}
                {explanationError && (
                  <div role="alert">
                    <ErrorMessage>{explanationError}</ErrorMessage>
                  </div>
                )}
                {explanation && (
                  <div className="explanation-content">
                    <p className="explanation-content__status">
                      Explicação {explanation.status === 'parcial' ? 'parcial' : 'concluída'}
                    </p>
                    <p>{buildExplanationSummary(result, explanation)}</p>

                    {explanation.referencias.length > 0 && (
                      <div className="explanation-reference">
                        {explanation.referencias.map((referencia, index) => (
                          <div key={`${referencia.titulo}-${index}`}>
                            <p>
                              <strong>Referência técnica:</strong> {referencia.titulo} — {referencia.origem}
                            </p>
                            <details>
                              <summary>Ver trecho consultado</summary>
                              <p>{referencia.trecho_utilizado}</p>
                            </details>
                          </div>
                        ))}
                      </div>
                    )}

                    {explanation.avisos.length > 0 && (
                      <>
                        <h3>Avisos</h3>
                        <ul>
                          {explanation.avisos.map((aviso, index) => (
                            <li key={`${aviso}-${index}`}>{aviso}</li>
                          ))}
                        </ul>
                      </>
                    )}
                  </div>
                )}
              </section>
            </>
          )}
        </section>
      </main>

      <BottomMenu onNewConsultation={startNewConsultation} />
    </div>
  )
}
