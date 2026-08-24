import type { FighterDetail } from '../api/types'
import Badge from './Badge'

const STYLE_LABELS: Record<string, string> = {
  wrestler: 'Wrestler',
  grappler: 'Grappler',
  striker: 'Striker',
  balanced: 'Balanced',
}

export default function FighterHeader({ fighter, side }: { fighter: FighterDetail | null; side: 'red' | 'blue' }) {
  if (!fighter) {
    return (
      <div className="text-center">
        <p className="font-display text-2xl font-semibold text-text-muted">Unknown Fighter</p>
        <p className="text-sm text-text-muted">No stats available</p>
      </div>
    )
  }

  return (
    <div className="text-center">
      <p className={`font-display text-3xl font-bold tracking-wide ${side === 'red' ? 'text-brand-hover' : 'text-gold'}`}>
        {fighter.name}
      </p>
      <p className="mt-1 text-sm text-text-muted">{fighter.record ?? 'Record unknown'}</p>
      <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
        {fighter.style && <Badge variant="muted">{STYLE_LABELS[fighter.style] ?? fighter.style}</Badge>}
        {!!fighter.win_streak && fighter.win_streak > 0 && (
          <Badge variant="win">{fighter.win_streak}-fight win streak</Badge>
        )}
      </div>
    </div>
  )
}
