export default function Input({
  id,
  type = 'text',
  value,
  placeholder,
  onChange,
  size,
  variant,
  error,
  hasToggle,
  ...rest
}) {
  const classNames = [
    'input',
    size === 'lg' && 'input--lg',
    variant === 'alt' && 'input--alt',
    variant === 'strong' && 'input--strong',
    variant === 'strong' && 'input--alt',
    error && 'input--error',
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <input
      id={id}
      type={type}
      value={value}
      placeholder={placeholder}
      onChange={onChange}
      className={classNames}
      aria-invalid={error ? true : undefined}
      {...rest}
    />
  )
}