import { NAVIGATION_ITEMS } from '../navigation.js'

export default function SideMenu({ open, selected, onSelect, onToggle }) {
  return (
    <div className="side-menu">
      <button type="button" className="painel-header__toggle" onClick={() => onToggle(!open)} aria-expanded={open} aria-controls="primary-navigation" aria-label={open ? 'Fechar menu' : 'Abrir menu'}>
        <span className="hamburger-icon" aria-hidden="true"><i /><i /><i /></span>
        <span>Menu</span>
      </button>
      <nav id="primary-navigation" className={`side-menu__nav${open ? ' is-open' : ''}`} aria-label="Navegação principal">
        <ul className="side-menu__list">
          {NAVIGATION_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={`side-menu__item${item.leave ? ' side-menu__item--leave' : ''}${selected === item.id ? ' is-selected' : ''}`}
                aria-current={selected === item.id ? 'page' : undefined}
                onClick={() => { onSelect(item.id); onToggle(false) }}
              >
                <span className="side-menu__dot" aria-hidden="true" />
                <span className="side-menu__label">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )
}
