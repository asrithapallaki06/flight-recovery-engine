// Display names, short explanations, and chart colors for each strategy.
export const STRATEGIES = [
  {
    key: 'original',
    name: 'No reassignment',
    short: 'Hold plan',
    blurb: 'Crews stay on their planned trips, like a tracking system that can’t keep up.',
    color: 'var(--s-original)',
  },
  {
    key: 'greedy',
    name: 'Greedy',
    short: 'Greedy',
    blurb: 'Flight by flight, take the first legal crew on the ground.',
    color: 'var(--s-greedy)',
  },
  {
    key: 'optimized',
    name: 'Optimizer',
    short: 'Optimizer',
    blurb: 'Re-plans all flights and crews together every hour (OR-Tools CP-SAT).',
    color: 'var(--s-optimized)',
  },
]

// Minutes after midnight -> "14:05". Past midnight shows as the next day's time.
export function hhmm(minutes) {
  if (minutes == null) return '--:--'
  const h = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}
