import { useState } from 'react'
import SideMenu from '../components/SideMenu.jsx'
import BottomMenu from '../components/BottomMenu.jsx'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { consultarCoordenada, solicitarExplicacao } from '../services/consultas.js'

const metricFormatter = new Intl.NumberFormat('pt-BR', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

function formatMetric(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return metricFormatter.format(value)
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
    parts.push(`A declividade registrada é ${declividade}%.`)
  }
  if (tipoSolo) {
    parts.push(`O tipo de solo informado é "${tipoSolo}".`)
  }
  if (altitude !== null) {
    parts.push(`A altitude registrada é ${altitude} m.`)
  }

  if (content.interpretacao_aptidao) {
    parts.push(content.interpretacao_aptidao)
  } else if (aptidao) {
    parts.push(`A aptidão agrícola retornada pelo sistema é "${aptidao}".`)
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

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [sideSelected, setSideSelected] = useState('')
  const [bottomSelected, setBottomSelected] = useState('painel')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [explanationLoading, setExplanationLoading] = useState(false)
  const [explanationError, setExplanationError] = useState('')
  const [explanation, setExplanation] = useState(null)

  function handleSideSelect(id) {
    setSideSelected(id)
  }

  function handleBottomSelect(id) {
    setBottomSelected(id)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setResult(null)
    setExplanationError('')
    setExplanation(null)

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

    setLoading(true)

    try {
      const data = await consultarCoordenada({
        latitude: parsedLatitude,
        longitude: parsedLongitude,
      })
      setResult(data)
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível concluir a consulta.')
    } finally {
      setLoading(false)
    }
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
      <SideMenu
        open={menuOpen}
        selected={sideSelected}
        onSelect={handleSideSelect}
        onToggle={() => setMenuOpen(false)}
      />

      <header className="painel-header">
        <button
          type="button"
          className="painel-header__toggle"
          onClick={() => setMenuOpen((open) => !open)}
          aria-expanded={menuOpen}
          aria-label={menuOpen ? 'Fechar menu lateral' : 'Abrir menu lateral'}
        >
          Menu
        </button>
        <span className="painel-header__title">Painel de Campo</span>
        <span className="painel-header__spacer" aria-hidden="true" />
      </header>

      <main className="painel-body">
        <section className="location-section" aria-labelledby="location-title">
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
                  onChange={(event) => setLongitude(formatCoordinate(event.target.value))}
                />
              </label>
            </div>

            <Button variant="primary" type="submit" disabled={loading}>
              {loading ? 'Consultando...' : 'Consultar'}
            </Button>
          </form>

          {loading && <p role="status">Consultando coordenadas...</p>}
          {error && (
            <div role="alert">
              <ErrorMessage>{error}</ErrorMessage>
            </div>
          )}
          {result && (
            <>
              <section className="results-grid" aria-label="Resultados geoespaciais">
                <ResultCard
                  label="Altitude (MDE)"
                  value={formatMetric(result.altitude_m)}
                  unit="m"
                  icon="altitude"
                />
                <ResultCard
                  label="Declividade"
                  value={formatMetric(result.declividade_percentual)}
                  unit="%"
                  icon="slope"
                />
                <ResultCard
                  label="Tipo de solo"
                  value={result.tipo_solo}
                  icon="soil"
                />
                <ResultCard
                  label="Aptidão agrícola"
                  value={result.aptidao_agricola}
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

      <BottomMenu selected={bottomSelected} onSelect={handleBottomSelect} />
    </div>
  )
}
