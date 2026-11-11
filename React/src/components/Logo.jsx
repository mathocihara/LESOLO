import { LeafIcon } from './icons.jsx'

export default function Logo({ variant = 'header' }) {
  const size = variant === 'hero' ? 34 : 26
  return (
    <span className={`logo logo--${variant}`}>
      <LeafIcon size={size} />
    </span>
  )
}