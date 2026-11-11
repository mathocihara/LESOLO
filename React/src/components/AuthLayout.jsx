export default function AuthLayout({ children }) {
  return (
    <main className="auth-layout">
      <div className="auth-content">{children}</div>
    </main>
  )
}