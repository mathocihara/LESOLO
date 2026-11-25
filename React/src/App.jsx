import { useEffect, useState } from 'react'
import Header from './components/Header.jsx'
import Login from './pages/Login.jsx'
import Cadastro from './pages/Cadastro.jsx'
import Home from './pages/Home.jsx'
import { obterUsuarioAtual, sair } from './services/api.js'

export default function App() {
  const [view, setView] = useState('login')
  const [user, setUser] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    let active = true
    obterUsuarioAtual()
      .then((currentUser) => { if (active) { setUser(currentUser); setView('painel') } })
      .catch(() => { if (active) { setUser(null); setView('login') } })
      .finally(() => { if (active) setCheckingSession(false) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const expireSession = () => { setUser(null); setView('login') }
    window.addEventListener('lesolo:session-expired', expireSession)
    return () => window.removeEventListener('lesolo:session-expired', expireSession)
  }, [])

  async function handleLogout() {
    try { await sair() } catch { /* A sessão local é encerrada mesmo se a API estiver indisponível. */ }
    setUser(null)
    setView('login')
  }

  if (checkingSession) return <main role="status" aria-live="polite">Verificando sessão...</main>
  if (user) return <Home user={user} onLogout={handleLogout} onUserUpdate={setUser} />

  return (
    <div className="app">
      <Header />
      {view === 'cadastro' ? (
        <Cadastro onGoLogin={() => setView('login')} onRegistered={() => setView('login')} />
      ) : (
        <Login onGoRegister={() => setView('cadastro')} onLogin={async (currentUser) => { try { setUser(await obterUsuarioAtual()) } catch { setUser(currentUser) }; setView('painel') }} />
      )}
    </div>
  )
}
