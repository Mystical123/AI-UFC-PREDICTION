import type { Citation } from '../api/types'
import Badge from './Badge'

export default function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) {
    return <p className="text-sm text-text-muted">No fan/analyst commentary found for this fight yet.</p>
  }

  return (
    <div className="space-y-3">
      {citations.map((c, i) => (
        <div key={i} className="rounded-xl border border-border bg-surface p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-border text-xs font-semibold text-text">
              {i + 1}
            </span>
            <Badge variant="muted">{c.source}</Badge>
            {c.author && <span className="text-xs text-text-muted">{c.author}</span>}
          </div>
          {c.title && <p className="mb-1 font-medium text-text">{c.title}</p>}
          <p className="text-sm text-text-muted">"{c.text}"</p>
          {c.url && (
            <a
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block cursor-pointer text-xs text-brand-hover hover:underline"
            >
              Read source →
            </a>
          )}
        </div>
      ))}
    </div>
  )
}
