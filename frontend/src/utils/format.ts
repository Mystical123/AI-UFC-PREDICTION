export function formatEventDate(timestamp: number | null): string {
  if (!timestamp) return 'Date TBA'
  return new Date(timestamp * 1000).toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

export function isUpcoming(timestamp: number | null): boolean {
  if (!timestamp) return true
  return timestamp * 1000 > Date.now()
}

const CARD_SEGMENT_LABELS: Record<string, string> = {
  main_card: 'Main Card',
  prelims: 'Prelims',
  early_prelims: 'Early Prelims',
}

export function cardSegmentLabel(segment: string | null): string {
  return segment ? CARD_SEGMENT_LABELS[segment] ?? segment : ''
}
