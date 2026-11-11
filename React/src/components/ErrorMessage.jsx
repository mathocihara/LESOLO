import { AlertIcon } from './icons.jsx'

export default function ErrorMessage({ children }) {
  if (!children) return null
  return (
    <span className="error-message">
      <span className="error-message__icon">
        <AlertIcon />
      </span>
      {children}
    </span>
  )
}