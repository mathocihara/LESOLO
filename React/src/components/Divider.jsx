export default function Divider({ children }) {
  return (
    <div className="divider">
      <span className="divider__line" aria-hidden="true" />
      <span className="divider__label">{children}</span>
      <span className="divider__line" aria-hidden="true" />
    </div>
  )
}