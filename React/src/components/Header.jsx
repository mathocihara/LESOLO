import Logo from './Logo.jsx'

export default function Header() {
  return (
    <header className="header">
      <div className="header__brand">
        <Logo variant="header" />
        <span>Lê Solo</span>
      </div>
    </header>
  )
}