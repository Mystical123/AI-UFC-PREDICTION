import { Link } from 'react-router-dom'
import type { FightSummary } from '../api/types'
import { cardSegmentLabel } from '../utils/format'
import Badge from './Badge'

export default function FightCard({ fight }: { fight: FightSummary }) {
  const isTitleFight = fight.weight_class?.toLowerCase().includes('title')

  return (
    <Link
      to={`/fights/${fight.id}`}
      className="group flex cursor-pointer items-center justify-between gap-4 rounded-2xl border border-border bg-surface p-4 transition-colors duration-200 hover:border-brand hover:bg-surface-hover sm:p-5"
    >
      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex flex-wrap items-center gap-2">
          {isTitleFight && <Badge variant="gold">Title Bout</Badge>}
          <Badge variant="muted">{cardSegmentLabel(fight.card_segment)}</Badge>
        </div>
        <p className="truncate font-display text-xl font-semibold text-text group-hover:text-brand-hover sm:text-2xl">
          {fight.fighter_red_name} <span className="text-text-muted">vs</span> {fight.fighter_blue_name}
        </p>
        {fight.weight_class && <p className="text-sm text-text-muted">{fight.weight_class}</p>}
      </div>
      <svg className="h-5 w-5 shrink-0 text-text-muted group-hover:text-brand-hover" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </Link>
  )
}
