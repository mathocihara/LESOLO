import { useState } from 'react'
import AuthLayout from '../components/AuthLayout.jsx'
import Logo from '../components/Logo.jsx'
import FormField from '../components/FormField.jsx'
import Input from '../components/Input.jsx'
import Button from '../components/Button.jsx'
import Divider from '../components/Divider.jsx'
import { GoogleIcon } from '../components/icons.jsx'

export default function Login({ onGoRegister, onLogin }) {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})

  function handleSubmit(event) {
    event.preventDefault()
    const next = {}
    if (!identifier.trim()) {
      next.identifier = 'Nome ou e-mail inválido'
    }
    if (!password) {
      next.password = 'Senha incorreta'
    }
    setErrors(next)

    if (!next.identifier && !next.password) {
      onLogin()
    }
  }

  return (
    <AuthLayout>
      <div className="auth-intro">
        <Logo variant="hero" />
        <h1 className="auth-title">Bem-vindo</h1>
        <span className="auth-subtitle">Leitura com precisão</span>
      </div>

      <form className="form" onSubmit={handleSubmit} noValidate>
        <FormField label="Nome ou e-mail" htmlFor="identifier" error={errors.identifier}>
          <Input
            id="identifier"
            type="text"
            value={identifier}
            placeholder="Seu nome ou e-mail"
            onChange={(e) => setIdentifier(e.target.value)}
            size="lg"
            variant="strong"
            error={Boolean(errors.identifier)}
          />
        </FormField>

        <FormField label="Senha" htmlFor="password" error={errors.password}>
          <Input
            id="password"
            type="password"
            value={password}
            placeholder="••••••••"
            onChange={(e) => setPassword(e.target.value)}
            size="lg"
            variant="strong"
            error={Boolean(errors.password)}
          />
        </FormField>

        <Button variant="primary" type="submit">
          ENTRAR
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