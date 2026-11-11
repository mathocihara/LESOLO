import { useState } from 'react'
import Header from './components/Header.jsx'
import Login from './pages/Login.jsx'
import Cadastro from './pages/Cadastro.jsx'
import Home from './pages/Home.jsx'

export default function App() {
  const [view, setView] = useState('login')

  if (view === 'painel') {
    return <Home />
  }

  return (
    <div className="app">
      <Header />
      {view === 'login' ? (
        <Login
          onGoRegister={() => setView('cadastro')}
          onLogin={() => setView('painel')}
        />
      ) : (
        <Cadastro onGoLogin={() => setView('login')} />
      )}
    </div>
  )
}