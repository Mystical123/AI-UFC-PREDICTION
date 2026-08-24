import { useState } from 'react'

const SIZES = {
  sm: 'h-10 w-10 text-xs',
  md: 'h-16 w-16 text-lg',
  lg: 'h-28 w-28 text-3xl',
} as const

function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[parts.length - 1]?.[0] ?? '')).toUpperCase()
}

export default function Avatar({
  src,
  name,
  size = 'md',
  ring,
}: {
  src: string | null
  name: string
  size?: keyof typeof SIZES
  ring?: 'win' | 'brand'
}) {
  const [failed, setFailed] = useState(false)
  const ringClass = ring === 'win' ? 'ring-win/50' : ring === 'brand' ? 'ring-brand/50' : 'ring-border'

  if (!src || failed) {
    return (
      <div
        className={`flex shrink-0 items-center justify-center rounded-full bg-surface-hover font-display font-semibold text-text-muted ring-2 ${ringClass} ${SIZES[size]}`}
      >
        {initials(name)}
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={name}
      onError={() => setFailed(true)}
      // UFC's fight-card images are tall "upper body standing" crops, not
      // square headshots -- bias toward the top so faces aren't cut off.
      className={`shrink-0 rounded-full bg-surface-hover object-cover object-top ring-2 ${ringClass} ${SIZES[size]}`}
    />
  )
}
