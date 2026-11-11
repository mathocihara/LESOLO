import { useState } from 'react'
import SideMenu from '../components/SideMenu.jsx'
import BottomMenu from '../components/BottomMenu.jsx'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { consultarCoordenada } from '../services/consultas.js'

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
            <pre className="location-result" aria-label="Resultado da consulta">
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </section>
      </main>

      <BottomMenu selected={bottomSelected} onSelect={handleBottomSelect} />
    </div>
  )
}
