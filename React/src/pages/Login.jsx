import { useState } from 'react'
import AuthLayout from '../components/AuthLayout.jsx'
import Logo from '../components/Logo.jsx'
import FormField from '../components/FormField.jsx'
import Input from '../components/Input.jsx'
import PasswordInput from '../components/PasswordInput.jsx'
import Button from '../components/Button.jsx'
import Divider from '../components/Divider.jsx'
import { GoogleIcon } from '../components/icons.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { entrar } from '../services/api.js'

export default function Login({ onGoRegister, onLogin }) {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [requestError, setRequestError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    const next = {}
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier.trim())) {
      next.identifier = 'Nome ou e-mail inválido'
    }
    if (!password) {
      next.password = 'Senha incorreta'
    }
    setErrors(next)

    setRequestError('')
    if (Object.keys(next).length) return
    setLoading(true)
    try { onLogin(await entrar({ email: identifier.trim(), senha: password })) }
    catch (error) { setRequestError(error.message || 'Não foi possível entrar.') }
    finally { setLoading(false) }
  }

  return (
    <AuthLayout>
      <div className="auth-intro">
        <Logo variant="hero" />
        <h1 className="auth-title">Bem-vindo</h1>
        <span className="auth-subtitle">Leitura com precisão</span>
      </div>

      <form className="form" onSubmit={handleSubmit} noValidate>
        <FormField label="E-mail" htmlFor="identifier" error={errors.identifier}>
          <Input
            id="identifier"
            type="email"
            value={identifier}
            placeholder="seu@email.com"
            onChange={(e) => setIdentifier(e.target.value)}
            size="lg"
            variant="strong"
            error={Boolean(errors.identifier)}
          />
        </FormField>

        <FormField label="Senha" htmlFor="password" error={errors.password}>
          <PasswordInput
            id="password"
            value={password}
            placeholder="••••••••"
            onChange={(e) => setPassword(e.target.value)}
            size="lg"
            variant="strong"
            error={Boolean(errors.password)}
          />
        </FormField>

        {requestError && <div role="alert"><ErrorMessage>{requestError}</ErrorMessage></div>}
        <Button variant="primary" type="submit" disabled={loading}>
          {loading ? 'ENTRANDO...' : 'ENTRAR'}
        </Button>
      </form>

      <Divider>OU</Divider>

      <Button variant="secondary" type="button">
        <GoogleIcon />
        Entrar com Google
      </Button>

      <div className="auth-footer">
        <div className="auth-link">
          <span className="auth-link__muted">Não tem uma conta? </span>
          <button
            type="button"
            className="auth-link__action"
            onClick={onGoRegister}
          >
            Cadastre-se
          </button>
        </div>
      </div>
    </AuthLayout>
  )
}
