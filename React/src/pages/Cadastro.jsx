import { useState } from 'react'
import AuthLayout from '../components/AuthLayout.jsx'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import Input from '../components/Input.jsx'
import Button from '../components/Button.jsx'
import { EyeIcon, EyeOffIcon, ArrowRightIcon } from '../components/icons.jsx'

const PASSWORD_REQUIREMENTS = [
  'Mín. 8 caracteres',
  'Letras e números',
  'Maiúsculas',
  'Símbolos (!@#)',
]

export default function Cadastro({ onGoLogin }) {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [nascimento, setNascimento] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [emailError, setEmailError] = useState('')

  function validadeEmail(value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
  }

  function handleEmailBlur() {
    if (email && !validadeEmail(email)) {
      setEmailError('E-mail inválido')
    } else {
      setEmailError('')
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    if (!email || !validadeEmail(email)) {
      setEmailError('E-mail inválido')
    } else {
      setEmailError('')
    }
  }

  return (
    <AuthLayout>
      <div className="auth-intro">
        <h1 className="auth-title auth-title--register">CADASTRAR</h1>
        <div className="auth-link">
          <span className="auth-link__muted">Você já tem uma conta? </span>
          <button type="button" className="auth-link__action" onClick={onGoLogin}>
            Clique aqui
          </button>
        </div>
      </div>

      <AuthCard>
        <form className="form" onSubmit={handleSubmit} noValidate>
          <FormField label="Nome" htmlFor="nome" alt>
            <Input
              id="nome"
              type="text"
              value={nome}
              placeholder="Seu nome completo"
              onChange={(e) => setNome(e.target.value)}
              variant="alt"
            />
          </FormField>

          <FormField label="Email" htmlFor="email" alt error={emailError}>
            <Input
              id="email"
              type="email"
              value={email}
              placeholder="seu@email.com"
              onChange={(e) => setEmail(e.target.value)}
              onBlur={handleEmailBlur}
              variant="alt"
              error={Boolean(emailError)}
            />
          </FormField>

          <FormField label="Senha" htmlFor="senha" alt>
            <div className="input--password">
              <Input
                id="senha"
                type={showPassword ? 'text' : 'password'}
                value={senha}
                placeholder="••••••••"
                onChange={(e) => setSenha(e.target.value)}
                variant="alt"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <div className="password-requirements">
              <span className="password-requirements__title">
                Requisitos da senha:
              </span>
              {PASSWORD_REQUIREMENTS.map((requirement) => (
                <span key={requirement} className="password-requirements__item">
                  <span className="password-requirements__dot" aria-hidden="true" />
                  {requirement}
                </span>
              ))}
            </div>
          </FormField>

          <FormField label="Data de aniversário" htmlFor="nascimento" alt>
            <Input
              id="nascimento"
              type="text"
              value={nascimento}
              placeholder="DD/MM/AAAA"
              onChange={(e) => setNascimento(e.target.value)}
              variant="alt"
            />
          </FormField>

          <Button variant="success" type="submit">
            Cadastrar
            <ArrowRightIcon />
          </Button>
        </form>
      </AuthCard>

      <div className="auth-footer">
        <span className="auth-footer__tag">Leitura com precisão</span>
      </div>
    </AuthLayout>
  )
}