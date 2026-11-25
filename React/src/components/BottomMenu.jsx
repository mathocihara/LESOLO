export default function BottomMenu({ onNewConsultation }) {
  return (
    <div className="bottom-menu">
      <button type="button" className="bottom-menu__item bottom-menu__item--new" aria-label="Iniciar nova consulta" onClick={onNewConsultation}>
        <span className="bottom-menu__label">+</span>
      </button>
    </div>
  )
}
