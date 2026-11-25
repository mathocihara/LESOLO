function Switch({ checked, onChange, label }) {
  return <input className="reference-switch" type="checkbox" role="switch" aria-label={label} checked={Boolean(checked)} onChange={(event) => onChange(event.target.checked)} />
}

export default function Acessibilidade({ preferences, onToggle, onTheme, onContrast, onBack }) {
  return <section className="reference-screen accessibility-screen" aria-labelledby="accessibility-title">
    <header className="screen-heading"><button className="screen-back" type="button" onClick={onBack} aria-label="Voltar para configurações">←</button><h1 id="accessibility-title">Acessibilidade</h1></header>
    <h2 className="setting-group-title">INTERFACE DE CAMPO</h2>
    <div className="setting-card"><span className="setting-icon" aria-hidden="true">⌕</span><div className="setting-copy"><strong>Ampliadores de telas</strong><small>Aumente partes da tela para melhor visibilidade.</small></div><Switch label="Ampliadores de telas" checked={preferences.ampliadores} onChange={(value) => onToggle('ampliadores', value)} /></div>
    <div className="setting-card"><span className="setting-icon" aria-hidden="true">◉</span><div className="setting-copy"><strong>Leitores de telas</strong><small>Realce o foco e anuncie mensagens importantes.</small></div><Switch label="Modo compatível com leitores de tela" checked={preferences.leitores} onChange={(value) => onToggle('leitores', value)} /></div>
    <div className="setting-card"><span className="setting-icon" aria-hidden="true">▦</span><div className="setting-copy"><strong>Teclados alternativos</strong><small>Atalhos: Alt+L para latitude e Alt+O para longitude.</small></div><Switch label="Atalhos de teclado" checked={preferences.teclado} onChange={(value) => onToggle('teclado', value)} /></div>
    <hr className="settings-divider" />
    <h2 className="setting-group-title">VISUALIZAÇÃO</h2>
    <div className="setting-card theme-card"><span className="setting-icon" aria-hidden="true">◐</span><div className="setting-copy"><strong>MODO ({preferences.tema === 'escuro' ? 'ESCURO' : 'CLARO'})</strong><small>Recomendado para uso em campo noturno.</small></div><Switch label="Tema escuro" checked={preferences.tema === 'escuro'} onChange={(value) => onTheme(value ? 'escuro' : 'claro')} /></div>
    <div className="setting-card"><span className="setting-icon" aria-hidden="true">◉</span><div className="setting-copy"><strong>Alto contraste</strong><small>Realce textos, controles e limites dos cartões.</small></div><Switch label="Alto contraste" checked={preferences.alto_contraste} onChange={onContrast} /></div>
    <aside className="accessibility-tip"><strong><span aria-hidden="true">ⓘ</span> Dica Técnica</strong><p>As preferências de tema e contraste são sincronizadas com sua conta. As opções de ampliação e atalhos ficam salvas neste dispositivo.</p></aside>
  </section>
}
