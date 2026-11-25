import { useState } from 'react'
import AuthLayout from '../components/AuthLayout.jsx'
import AuthCard from '../components/AuthCard.jsx'
import FormField from '../components/FormField.jsx'
import Input from '../components/Input.jsx'
import PasswordInput from '../components/PasswordInput.jsx'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import { cadastrar } from '../services/api.js'

export default function Cadastro({ onGoLogin, onRegistered }) {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!nome.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()) || senha.length < 8) {
      setError('Informe nome e e-mail válidos e uma senha com pelo menos 8 caracteres.')
      return
    }
    setLoading(true)
    try { await cadastrar({ nome: nome.trim(), email: email.trim(), senha }); onRegistered() }
    catch (requestError) { setError(requestError.message || 'Não foi possível concluir o cadastro.') }
    finally { setLoading(false) }
  }

  return <AuthLayout><div className="auth-intro"><h1 className="auth-title auth-title--register">CADASTRAR</h1><div className="auth-link"><span className="auth-link__muted">Você já tem uma conta? </span><button type="button" className="auth-link__action" onClick={onGoLogin}>Entrar</button></div></div><AuthCard><form className="form" onSubmit={handleSubmit} noValidate>
    <FormField label="Nome" htmlFor="nome"><Input id="nome" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Seu nome completo" /></FormField>
    <FormField label="E-mail" htmlFor="email"><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="seu@email.com" /></FormField>
    <FormField label="Senha" htmlFor="senha"><PasswordInput id="senha" value={senha} onChange={(e) => setSenha(e.target.value)} placeholder="Mínimo de 8 caracteres" /></FormField>
    {error && <div role="alert"><ErrorMessage>{error}</ErrorMessage></div>}
    <Button variant="success" type="submit" disabled={loading}>{loading ? 'Cadastrando...' : 'Cadastrar'}</Button>
  </form></AuthCard></AuthLayout>
}
