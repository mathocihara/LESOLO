import { useState } from 'react'
import Input from './Input.jsx'

export default function PasswordInput({ id, value, onChange, placeholder, ...props }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="input--password">
      <Input id={id} type={visible ? 'text' : 'password'} value={value} onChange={onChange} placeholder={placeholder} {...props} />
      <button type="button" className="password-toggle" aria-label={visible ? 'Ocultar senha' : 'Visualizar senha'} aria-pressed={visible} onClick={() => setVisible((current) => !current)}>
        <svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          {visible ? <><path d="M3 3l18 18" /><path d="M10.6 10.6a2 2 0 002.8 2.8" /><path d="M9.9 5.2A11 11 0 0121 12a11.8 11.8 0 01-3.3 4.1" /><path d="M6.2 6.2A12 12 0 003 12s3 7 9 7a9.8 9.8 0 004.1-.9" /></> : <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>}
        </svg>
      </button>
    </div>
  )
}
