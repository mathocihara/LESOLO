import { useState } from 'react'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import FormField from '../components/FormField.jsx'
import Input from '../components/Input.jsx'
import PasswordInput from '../components/PasswordInput.jsx'
import { atualizarConta } from '../services/api.js'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
const todayLocal = () => {
  const current = new Date()
  return new Date(current.getTime() - current.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
}

export default function EditarConta({ user, onUpdated, onOpenCloseAccount, onBack }) {
  const [nome, setNome] = useState(user?.nome || '')
  const [email, setEmail] = useState(user?.email || '')
  const [dataNascimento, setDataNascimento] = useState(user?.data_nascimento || '')
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [erro, setErro] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [loading, setLoading] = useState(false)

  async function salvar(event) {
    event.preventDefault()
    setErro('')
    setMensagem('')
    const hoje = todayLocal()
    if (!nome.trim() || nome.trim().length > 200) return setErro('Informe um nome válido, com até 200 caracteres.')
    if (!EMAIL_PATTERN.test(email.trim()) || email.trim().length > 320) return setErro('Informe um e-mail válido.')
    if (dataNascimento && dataNascimento > hoje) return setErro('A data de nascimento não pode estar no futuro.')
    if (novaSenha && (novaSenha.length < 8 || novaSenha.length > 1024)) return setErro('A nova senha deve ter entre 8 e 1024 caracteres.')
    if (!senhaAtual) return setErro('Informe sua senha atual para confirmar as alterações.')

    setLoading(true)
    try {
      const updated = await atualizarConta({
        senha_atual: senhaAtual,
        nome: nome.trim(),
        email: email.trim(),
        data_nascimento: dataNascimento || null,
        ...(novaSenha ? { nova_senha: novaSenha } : {}),
      })
      onUpdated(updated)
      setSenhaAtual('')
      setNovaSenha('')
      setMensagem('Dados da conta atualizados.')
    } catch (requestError) {
      setErro(requestError.message || 'Não foi possível atualizar os dados da conta.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="reference-screen account-edit-screen" aria-labelledby="account-edit-title">
    <header className="screen-heading"><button className="screen-back" type="button" onClick={onBack} aria-label="Voltar para configurações">←</button><h1 id="account-edit-title">Editar dados da conta</h1></header>
    <form className="account-form" onSubmit={salvar} noValidate>
      <FormField label="Nome" htmlFor="account-name"><Input id="account-name" value={nome} onChange={(event) => setNome(event.target.value)} autoComplete="name" maxLength={200} /></FormField>
      <FormField label="E-mail" htmlFor="account-email"><Input id="account-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" maxLength={320} /></FormField>
      <FormField label="Data de nascimento" htmlFor="account-birth-date"><Input id="account-birth-date" type="date" value={dataNascimento} onChange={(event) => setDataNascimento(event.target.value)} max={todayLocal()} /></FormField>
      <FormField label="Nova senha (opcional)" htmlFor="account-new-password"><PasswordInput id="account-new-password" value={novaSenha} onChange={(event) => setNovaSenha(event.target.value)} autoComplete="new-password" placeholder="Mínimo de 8 caracteres" /></FormField>
      <FormField label="Senha atual para confirmar" htmlFor="account-current-password"><PasswordInput id="account-current-password" value={senhaAtual} onChange={(event) => setSenhaAtual(event.target.value)} autoComplete="current-password" /></FormField>
      {erro && <div role="alert"><ErrorMessage>{erro}</ErrorMessage></div>}
      {mensagem && <p className="account-success" role="status">{mensagem}</p>}
      <Button variant="primary" type="submit" disabled={loading}>{loading ? 'Salvando...' : 'Salvar alterações'}</Button>
    </form>
    <section className="sensitive-settings" aria-labelledby="sensitive-settings-title">
      <h2 id="sensitive-settings-title">Dados sensíveis</h2>
      <p>O encerramento da conta remove definitivamente seus dados associados.</p>
      <Button variant="danger" type="button" onClick={onOpenCloseAccount}>Fechar conta</Button>
    </section>
  </section>
}
