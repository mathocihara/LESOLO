export function LeafIcon({ size = 24, color = '#4BE277' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M20 3.5C11.5 3.5 5 8 5 14.5c0 3.5 2 6 4.7 6C15 20.5 20.5 14.5 20 3.5Z"
        fill={color}
      />
      <path
        d="M6.5 14.5C9.5 10.5 14 6.5 19 4.5"
        stroke="#020617"
        strokeWidth="1"
        strokeLinecap="round"
        opacity="0.18"
      />
    </svg>
  )
}

export function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <path
        d="M10 4.09c1.53 0 2.9.53 3.98 1.57l2.9-2.9C15.32 1.37 12.87.4 10 .4 6.2.4 2.9 2.64 1.36 5.9l3.41 2.65C5.55 6.2 7.58 4.09 10 4.09Z"
        fill="#EA4335"
      />
      <path
        d="M10 15.91c-1.56 0-2.87-.8-3.55-2.03l-3.41 2.65C4.3 19.36 6.9 19.6 10 19.6c2.82 0 5.27-1.04 6.9-2.84l-3.28-2.55c-.91.62-2.18 1.06-3.62 1.06Z"
        fill="#34A853"
      />
      <path
        d="M19.6 10c0-.68-.06-1.34-.17-1.97H10v3.8h5.4c-.23 1.28-.93 2.36-1.99 3.09l3.28 2.55c1.92-1.77 2.91-4.38 2.91-7.47Z"
        fill="#4285F4"
      />
      <path
        d="M4.77 7.65A5.98 5.98 0 0 0 4.42 10c0 .82.13 1.6.35 2.35L1.36 15C.48 13.53.4 11.8.4 10s.08-3.53 2.96-5l1.41 2.65Z"
        fill="#FBBC05"
      />
    </svg>
  )
}

export function EyeIcon({ size = 20, color = 'currentColor' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="12" cy="12" r="2.6" stroke={color} strokeWidth="1.5" />
    </svg>
  )
}

export function EyeOffIcon({ size = 20, color = 'currentColor' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M2 12s3.5-6.5 10-6.5 10 6.5 10 6.5-3.5 6.5-10 6.5S2 12 2 12Z"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M4 4l16 16" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

export function ArrowRightIcon({ size = 16, color = 'currentColor' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M5 12h14M13 6l6 6-6 6"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function AlertIcon({ size = 14, color = '#FFB4AB' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="9" fill={color} />
      <path
        d="M12 7.5v5.5"
        stroke="#020617"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <circle cx="12" cy="16.3" r="1.1" fill="#020617" />
    </svg>
  )
}