import { SIDE_MENU_ITEMS } from '../navigation.js'

export default function SideMenu({ open, selected, onSelect, onToggle }) {
  return (
    <aside
      className={`side-menu${open ? ' is-open' : ''}`}
      aria-hidden={!open}
    >
      <div className="side-menu__header">
        <span className="side-menu__brand" aria-hidden="true" />
        <span className="side-menu__title">Menu</span>
      </div>

      <nav className="side-menu__nav" aria-label="Menu lateral">
        <ul className="side-menu__list">
          {SIDE_MENU_ITEMS.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={`side-menu__item${item.leave ? ' side-menu__item--leave' : ''}${
                  selected === item.id ? ' is-selected' : ''
                }`}
                onClick={() => onSelect(item.id)}
              >
                <span className="side-menu__dot" aria-hidden="true" />
                <span className="side-menu__label">{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="side-menu__footer">
        <button
          type="button"
          className="side-menu__close"
          onClick={onToggle}
        >
          Fechar
        </button>
      </div>
    </aside>
  )
}