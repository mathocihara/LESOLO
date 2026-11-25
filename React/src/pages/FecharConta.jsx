import { useState } from 'react'
import Button from '../components/Button.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'
import FormField from '../components/FormField.jsx'
import PasswordInput from '../components/PasswordInput.jsx'
import { excluirConta } from '../services/api.js'

export default function FecharConta({ onBack }) {
  const [confirmando, setConfirmando] = useState(false)
  const [senha, setSenha] = useState('')
  const [frase, setFrase] = useState('')
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)
  const [solicitada, setSolicitada] = useState(false)

  async function confirmarExclusao(event) {
    event.preventDefault()
    setErro('')
    if (frase.trim() !== 'EXCLUIR') return setErro('Digite EXCLUIR para confirmar a solicitação.')
    if (!senha) return setErro('Informe sua senha atual para verificar sua identidade.')
    setLoading(true)
    try {
      await excluirConta({ senha_atual: senha, confirmacao: 'EXCLUIR' })
      setSolicitada(true)
    } catch (requestError) {
      setErro(requestError.message || 'Não foi possível excluir a conta.')
    } finally {
      setLoading(false)
    }
  }

  return <section className="reference-screen close-account-screen" aria-labelledby="close-account-title">
    <header className="screen-heading"><button className="screen-back" type="button" onClick={confirmando ? () => setConfirmando(false) : onBack} aria-label="Voltar">←</button><h1 id="close-account-title">Fechar conta</h1></header>
    <div className="sensitive-data-card">
      <h2>Encerramento da conta</h2>
      <p>A solicitação inicia um prazo de 30 dias. Durante esse período, sua conta e seus dados permanecem disponíveis. Um novo acesso cancela a solicitação.</p>
      <p>Após 30 dias sem acesso, a conta e os registros associados serão excluídos definitivamente.</p>
    </div>
    {solicitada ? <div role="status" aria-live="polite"><p>Solicitação registrada. Você continua com acesso à conta; entre novamente durante os próximos 30 dias para cancelar a exclusão.</p></div> : !confirmando ? <Button variant="danger" type="button" onClick={() => setConfirmando(true)}>Solicitar exclusão da conta</Button> : <form className="account-form delete-confirmation" onSubmit={confirmarExclusao}>
      <div className="delete-warning" role="alert">
        <strong>Tem certeza de que deseja excluir sua conta?</strong>
        <p>A conta será mantida por 30 dias. Qualquer novo acesso nesse período cancela a solicitação.</p>
      </div>
      <FormField label="Digite EXCLUIR para confirmar" htmlFor="delete-confirmation"><input id="delete-confirmation" className="input" value={frase} onChange={(event) => setFrase(event.target.value)} autoComplete="off" /></FormField>
      <FormField label="Senha atual" htmlFor="delete-password"><PasswordInput id="delete-password" value={senha} onChange={(event) => setSenha(event.target.value)} autoComplete="current-password" /></FormField>
      {erro && <div role="alert"><ErrorMessage>{erro}</ErrorMessage></div>}
      <Button variant="danger" type="submit" disabled={loading || frase.trim() !== 'EXCLUIR' || !senha.trim()}>{loading ? 'Enviando solicitação...' : 'Confirmar solicitação de exclusão'}</Button>
    </form>}
  </section>
}
