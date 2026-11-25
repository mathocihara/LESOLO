import Button from '../components/Button.jsx'

function formatDate(value) {
  if (!value) return 'Data indisponível'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Data indisponível' : date.toLocaleDateString('pt-BR')
}

const geographicLabels = {
  altitude_m: 'altitude',
  declividade_percentual: 'declividade',
  tipo_solo: 'tipo de solo',
  aptidao_agricola: 'aptidão agrícola',
}

function valueAtual(record, field, value) {
  return (record.dados_desatualizados || []).includes(field)
    ? `Anterior, não atualizado nesta consulta: ${value ?? 'sem valor'}`
    : value ?? '—'
}

export default function Registros({ records, onOpen, onDelete, onSave, onClear, onBack }) {
  return <section className="reference-screen records-screen" aria-labelledby="records-title">
    <header className="screen-heading"><button className="screen-back" type="button" onClick={onBack} aria-label="Voltar ao painel">←</button><h1 id="records-title">Registros</h1></header>
    <div className="records-actions"><span>Registros temporários e permanentes</span>{records.some((record) => record.status === 'PERMANENTE') && <button type="button" onClick={onClear}>Limpar permanentes</button>}</div>
    {records.length === 0 ? <p className="empty-records">Nenhum registro disponível.</p> : <div className="records-list">{records.map((record) => <article className="record-card" key={record.id}>
      <button className="record-card__open" type="button" onClick={() => onOpen(record)} aria-label={`Abrir consulta ${record.nome || ''}`}>
        <span>{record.status === 'TEMPORARIO' ? 'Temporário · expira em ' + formatDate(record.data_expiracao) : 'Permanente'} · Consulta {record.status_consulta === 'NAO_CLASSIFICADA' ? 'anterior sem classificação' : record.status_consulta?.toLowerCase().replace('_', ' ')}</span><span>Data: {formatDate(record.data_consulta)}</span>
        <span>Longitude: {record.longitude}</span><span className="record-card__name">{record.nome || 'Consulta salva'}</span>
      </button>
      <div className="record-details"><span>Altitude {valueAtual(record, 'altitude_m', record.altitude_m)} m</span><span>Declividade {valueAtual(record, 'declividade_percentual', record.declividade_percentual)}%</span><span>Solo {valueAtual(record, 'tipo_solo', record.tipo_solo)}</span><span>Aptidão {valueAtual(record, 'aptidao_agricola', record.aptidao_agricola)}</span></div>
      {record.dados_ausentes?.length > 0 && <p role="status">Dados não obtidos: {record.dados_ausentes.map((key) => geographicLabels[key] || key).join(', ')}{record.falhas_fontes?.length ? `. Falhas nas fontes: ${record.falhas_fontes.map((key) => geographicLabels[key] || key).join(', ')}` : ''}.</p>}
      {record.status === 'TEMPORARIO' && <button type="button" onClick={() => onSave(record)}>Salvar como permanente</button>}
      <button className="record-delete" type="button" onClick={() => onDelete(record)} aria-label="Excluir registro">Excluir</button>
    </article>)}</div>}
  </section>
}
