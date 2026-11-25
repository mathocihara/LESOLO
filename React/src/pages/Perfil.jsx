import Button from '../components/Button.jsx'

export default function Perfil({ user, preferences, onPreference, onOpenAccountSettings, onOpenAccessibility, onBack }) {
  return <section className="reference-screen profile-screen" aria-labelledby="profile-title">
    <header className="screen-heading"><button className="screen-back" type="button" onClick={onBack} aria-label="Voltar ao painel">←</button><h1 id="profile-title">Perfil</h1></header>
    <p className="config-welcome">{user?.nome || 'Meu perfil'}</p>
    <div className="setting-card notification-card"><span className="setting-icon" aria-hidden="true">{'\u2667'}</span><div className="setting-copy"><strong>{'Notifica\u00e7\u00e3o'}</strong><small>{'Ativar notifica\u00e7\u00e3o'}</small></div><input className="reference-switch" type="checkbox" role="switch" aria-label={'Ativar notifica\u00e7\u00f5es'} checked={Boolean(preferences?.notificacoes)} onChange={(event) => onPreference({ notificacoes: event.target.checked })} /></div>
    <section className="account-card" aria-labelledby="profile-account-title">
      <h2 id="profile-account-title"><span aria-hidden="true">♙</span> Conta</h2>
      <div className="account-row"><span>Nome</span><strong title={user?.nome}>{user?.nome || '—'}</strong></div>
      <div className="account-row"><span>E-mail</span><strong title={user?.email}>{user?.email || '—'}</strong></div>
      <div className="account-row"><span>Data de nascimento</span><strong>{user?.data_nascimento || '—'}</strong></div>
    </section>
    <Button variant="secondary" type="button" onClick={onOpenAccountSettings}>Configurações da conta</Button>
    <Button variant="secondary" type="button" onClick={onOpenAccessibility}>Acessibilidade</Button>
  </section>
}
