import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { api } from '../api/client'
import type { FightDetail, PredictionResponse } from '../api/types'
import FighterHeader from '../components/FighterHeader'
import StatCompareRow from '../components/StatCompareRow'
import CitationList from '../components/CitationList'
import Badge from '../components/Badge'
import { ErrorState } from './EventsPage'

export default function FightDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [fight, setFight] = useState<FightDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [predicting, setPredicting] = useState(false)
  const [predictionError, setPredictionError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setFight(null)
    setPrediction(null)
    setPredictionError(null)

    // Fired in parallel, not sequentially -- the prediction doesn't need the
    // fight data client-side (the backend looks it up itself), and it's
    // cached server-side after the first request for a given fight, so this
    // is fast on every visit after the first.
    api.getFight(Number(id)).then(setFight).catch((e) => setError(e.message))

    setPredicting(true)
    api
      .getPrediction(Number(id))
      .then(setPrediction)
      .catch((e) => setPredictionError(e.message))
      .finally(() => setPredicting(false))
  }, [id])

  if (error) return <ErrorState message={error} />
  if (!fight) return <div className="h-96 animate-pulse rounded-xl border border-border bg-surface" />

  const red = fight.fighter_red
  const blue = fight.fighter_blue

  return (
    <div className="space-y-8">
      <div>
        <Link to={`/events/${fight.event.event_slug}`} className="cursor-pointer text-sm text-text-muted hover:text-text">
          ← {fight.event.event_name}
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {fight.weight_class?.toLowerCase().includes('title') && <Badge variant="gold">Title Bout</Badge>}
          <Badge variant="muted">{fight.weight_class ?? 'Weight class TBA'}</Badge>
        </div>
      </div>

      {/* Fighter matchup */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="grid grid-cols-1 items-center gap-6 sm:grid-cols-[1fr_auto_1fr]">
          <FighterHeader fighter={red} side="red" />
          <p className="font-display text-2xl font-bold text-text-muted">VS</p>
          <FighterHeader fighter={blue} side="blue" />
        </div>

        {red && blue && (
          <div className="mt-8 border-t border-border pt-6">
            <StatCompareRow label="Reach (in)" redValue={red.reach_inches} blueValue={blue.reach_inches} />
            <StatCompareRow label="Strikes Landed/min" redValue={red.sig_strikes_landed_per_min} blueValue={blue.sig_strikes_landed_per_min} />
            <StatCompareRow
              label="Strike Accuracy"
              redValue={red.sig_strike_accuracy_pct}
              blueValue={blue.sig_strike_accuracy_pct}
              format={(v) => `${v.toFixed(0)}%`}
            />
            <StatCompareRow label="Takedowns/15min" redValue={red.takedown_avg_per_15min} blueValue={blue.takedown_avg_per_15min} />
            <StatCompareRow
              label="Takedown Defense"
              redValue={red.takedown_defense_pct}
              blueValue={blue.takedown_defense_pct}
              format={(v) => `${v.toFixed(0)}%`}
            />
            <StatCompareRow label="Submissions/15min" redValue={red.submission_avg_per_15min} blueValue={blue.submission_avg_per_15min} />
          </div>
        )}
      </div>

      {/* AI Prediction */}
      <div className="rounded-xl border border-border bg-surface p-6">
        <div className="mb-4 flex items-center gap-2">
          <h2 className="font-display text-2xl font-bold tracking-wide text-text">AI Prediction</h2>
          {predicting && (
            <span className="h-2 w-2 animate-pulse rounded-full bg-brand" aria-hidden="true" />
          )}
        </div>

        {predictionError && <ErrorState message={predictionError} />}

        {predicting && (
          <div className="space-y-2">
            <div className="h-4 w-3/4 animate-pulse rounded bg-border" />
            <div className="h-4 w-full animate-pulse rounded bg-border" />
            <div className="h-4 w-5/6 animate-pulse rounded bg-border" />
          </div>
        )}

        {prediction && (
          <div className="space-y-6">
            <div className="prose prose-invert prose-sm max-w-none text-text [&_strong]:text-text [&_p]:text-text/90">
              <ReactMarkdown>{prediction.prediction}</ReactMarkdown>
            </div>
            <div>
              <h3 className="mb-3 font-display text-lg font-semibold tracking-wide text-text-muted">Sources</h3>
              <CitationList citations={prediction.citations} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
