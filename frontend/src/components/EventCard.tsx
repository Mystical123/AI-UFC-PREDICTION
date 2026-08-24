import { Link } from 'react-router-dom'
import type { EventSummary } from '../api/types'
import { formatEventDate, isUpcoming } from '../utils/format'
import Badge from './Badge'

export default function EventCard({ event }: { event: EventSummary }) {
  return (
    <Link
      to={`/events/${event.event_slug}`}
      className="group block cursor-pointer rounded-2xl border border-border bg-surface p-5 transition-colors duration-200 hover:border-brand hover:bg-surface-hover"
    >
      <div className="mb-2 flex items-center justify-between">
        <Badge variant={isUpcoming(event.date_timestamp) ? 'brand' : 'muted'}>
          {isUpcoming(event.date_timestamp) ? 'Upcoming' : 'Past'}
        </Badge>
        <span className="text-sm text-text-muted">{formatEventDate(event.date_timestamp)}</span>
      </div>
      <h3 className="font-display text-2xl font-semibold tracking-wide text-text group-hover:text-brand-hover">
        {event.event_name}
      </h3>
      {event.venue && <p className="mt-1 text-sm text-text-muted">{event.venue}</p>}
    </Link>
  )
}
