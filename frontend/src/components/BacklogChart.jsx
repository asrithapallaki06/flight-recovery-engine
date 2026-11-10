// Backlog = flights that should have left by this hour but haven't.
// It climbs during the ground stop. Where a line ends at night is what never flew.
import { STRATEGIES } from '../strategies'

const W = 440
const H = 230
const PAD = { top: 14, right: 14, bottom: 26, left: 30 }

export default function BacklogChart({ result, groundStop }) {
  const series = STRATEGIES.map((s) => ({
    ...s,
    points: result.strategies[s.key].curve.map((p) => ({ hour: p.hour, value: p.scheduled - p.flown })),
  }))
  const hours = series[0].points.map((p) => p.hour)
  const minH = hours[0]
  const maxH = hours.at(-1)
  const maxV = Math.max(5, ...series.flatMap((s) => s.points.map((p) => p.value)))
  const yMax = Math.ceil(maxV / 10) * 10

  const x = (h) => PAD.left + ((h - minH) / (maxH - minH)) * (W - PAD.left - PAD.right)
  const y = (v) => H - PAD.bottom - (v / yMax) * (H - PAD.top - PAD.bottom)
  const yTicks = Array.from({ length: yMax / 10 + 1 }, (_, i) => i * 10)

  return (
    <section className="panel backlog">
      <h2 className="panel-title">Backlog of unflown flights</h2>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Flights behind schedule by hour, per strategy">
        <rect x={x(groundStop[0])} y={PAD.top} width={x(groundStop[1]) - x(groundStop[0])}
              height={H - PAD.top - PAD.bottom} fill="var(--stop-fill)" />
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
            <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" className="axis">{t}</text>
          </g>
        ))}
        {hours.filter((h) => h % 4 === 0).map((h) => (
          <text key={h} x={x(h)} y={H - 8} textAnchor="middle" className="axis">
            {String(h % 24).padStart(2, '0')}:00
          </text>
        ))}
        {series.map((s) => (
          <polyline key={s.key} fill="none" stroke={s.color} strokeLinejoin="round"
                    strokeWidth={s.key === 'optimized' ? 2.5 : 1.75}
                    strokeDasharray={s.key === 'original' ? '4 3' : undefined}
                    points={s.points.map((p) => `${x(p.hour)},${y(p.value)}`).join(' ')} />
        ))}
        {series.map((s) => (
          <text key={s.key} x={x(maxH) - 4} y={y(s.points.at(-1).value) - 5} textAnchor="end"
                className="end-label" fill={s.color}>
            {s.points.at(-1).value}
          </text>
        ))}
      </svg>
      <p className="foot">Lines overlap until the stop lifts. Numbers at the right are flights that never flew.</p>
    </section>
  )
}
