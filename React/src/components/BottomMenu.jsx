import { BOTTOM_MENU_ITEMS } from '../navigation.js'

export default function BottomMenu({ selected, onSelect }) {
  return (
    <nav className="bottom-menu" aria-label="Menu inferior">
      <ul className="bottom-menu__list">
        {BOTTOM_MENU_ITEMS.map((item) => (
          <li key={item.id} className="bottom-menu__entry">
            <button
              type="button"
              className={`bottom-menu__item${selected === item.id ? ' is-active' : ''}`}
              onClick={() => onSelect(item.id)}
            >
              <span className="bottom-menu__dot" aria-hidden="true" />
              <span className="bottom-menu__label">{item.label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}