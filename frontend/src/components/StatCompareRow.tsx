export default function StatCompareRow({
  label,
  redValue,
  blueValue,
  format = (v: number) => v.toFixed(1),
}: {
  label: string
  redValue: number | null
  blueValue: number | null
  format?: (v: number) => string
}) {
  const red = redValue ?? 0
  const blue = blueValue ?? 0
  const total = red + blue
  const redPct = total > 0 ? (red / total) * 100 : 50

  return (
    <div className="py-2">
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-text">{redValue != null ? format(redValue) : '—'}</span>
        <span className="text-xs uppercase tracking-wider text-text-muted">{label}</span>
        <span className="font-medium text-text">{blueValue != null ? format(blueValue) : '—'}</span>
      </div>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-border">
        <div className="bg-brand transition-all duration-300" style={{ width: `${redPct}%` }} />
        <div className="bg-gold transition-all duration-300" style={{ width: `${100 - redPct}%` }} />
      </div>
    </div>
  )
}
