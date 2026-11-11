import ErrorMessage from './ErrorMessage.jsx'

export default function FormField({ label, htmlFor, error, alt, children }) {
  return (
    <div className={`form-field${alt ? ' form-field--alt' : ''}`}>
      {label && (
        <label className="form-field__label" htmlFor={htmlFor}>
          {label}
        </label>
      )}
      {children}
      <ErrorMessage>{error}</ErrorMessage>
    </div>
  )
}