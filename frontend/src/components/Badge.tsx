const VARIANTS = {
  gold: 'bg-gold/15 text-gold border-gold/30',
  brand: 'bg-brand/15 text-brand-hover border-brand/30',
  muted: 'bg-surface text-text-muted border-border',
  win: 'bg-win/15 text-win border-win/30',
} as const

export default function Badge({
  children,
  variant = 'muted',
}: {
  children: React.ReactNode
  variant?: keyof typeof VARIANTS
}) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${VARIANTS[variant]}`}>
      {children}
    </span>
  )
}
