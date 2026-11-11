export default function Button({ variant, type = 'button', disabled, onClick, children }) {
  const classNames = ['button', `button--${variant}`].join(' ')
  return (
    <button
      type={type}
      className={classNames}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  )
}