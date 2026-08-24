import { Link } from 'react-router-dom'
import type { FightSummary } from '../api/types'
import Avatar from './Avatar'
import Badge from './Badge'

// A dense list row (not its own bordered/rounded card) -- meant to sit inside
// a shared divided container per card-segment, closer to how Sleeper lists
// games as compact rows rather than spaced-out standalone cards.
export default function FightCard({ fight }: { fight: FightSummary }) {
  const isTitleFight = fight.weight_class?.toLowerCase().includes('title')

  return (
    <Link
      to={`/fights/${fight.id}`}
      className="group flex cursor-pointer items-center gap-3 px-4 py-3 transition-colors duration-150 hover:bg-surface-hover"
    >
      <div className="flex shrink-0 items-center">
        <Avatar src={fight.fighter_red_image_url} name={fight.fighter_red_name} size="sm" ring="win" />
        <div className="-ml-3">
          <Avatar src={fight.fighter_blue_image_url} name={fight.fighter_blue_name} size="sm" ring="brand" />
        </div>
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate font-display text-lg font-semibold tracking-wide text-text group-hover:text-brand-hover sm:text-xl">
          {fight.fighter_red_name} <span className="text-text-muted">vs</span> {fight.fighter_blue_name}
        </p>
        <div className="mt-0.5 flex items-center gap-1.5 text-xs text-text-muted">
          {isTitleFight && <Badge variant="gold">Title</Badge>}
          <span className="truncate">{fight.weight_class}</span>
        </div>
      </div>
      <svg className="h-4 w-4 shrink-0 text-text-muted group-hover:text-brand-hover" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9 6l6 6-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </Link>
  )
}
