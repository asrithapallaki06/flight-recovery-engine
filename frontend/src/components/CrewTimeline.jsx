// The crew timeline: one row per crew, one bar per flight, across the whole day.
// This is the layout airline crew schedulers work in. It shows at a glance
// which crews are waiting out the storm, which run into their duty limit
// (red tick), and which end the night stuck away from the hub.
import { useMemo, useState } from 'react'
import { hhmm } from '../strategies'

const START = 5 * 60    // 05:00
const END = 26 * 60     // 02:00 the next morning
const W = 1120
const LABEL = 92
const ROW = 15
const TOP = 26

export default function CrewTimeline({ crews, groundStop, strategyName }) {
  const [hover, setHover] = useState(null)
  const [onlyIssues, setOnlyIssues] = useState(false)

  const rows = useMemo(() => {
    const used = crews.filter((c) => c.flights.length || !c.reserve)
    const idle = crews.filter((c) => !c.flights.length && c.reserve).length
    const list = onlyIssues
      ? used.filter((c) => c.stranded || c.flights.some((f) => f.delay_min >= 15))
      : used
    return { list, idle }
  }, [crews, onlyIssues])

  const x = (m) => LABEL + ((Math.min(Math.max(m, START), END) - START) / (END - START)) * (W - LABEL - 8)
  const H = TOP + rows.list.length * ROW + 8
  const hours = Array.from({ length: (END - START) / 60 + 1 }, (_, i) => START + i * 60)

  return (
    <section className="panel timeline">
      <div className="panel-head">
        <h2 className="panel-title">Crew timeline · {strategyName}</h2>
        <ul className="legend">
          <li><span className="sw sw-ontime" />On time</li>
          <li><span className="sw sw-late" />Left 15+ min late</li>
          <li><span className="sw sw-limit" />13-hr duty limit</li>
          <li><span className="sw sw-stop" />Ground stop</li>
        </ul>
        <label className="check">
          <input id="only-issues" type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} />
          Only crews with delays or strandings
        </label>
      </div>

      <div className="scroll-x">
        <svg viewBox={`0 0 ${W} ${H}`} className="gantt" role="img"
             aria-label={`Timeline of ${rows.list.length} crews and the flights they flew`}>
          <defs>
            <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="6" height="6" fill="var(--stop-fill)" />
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--stop-line)" strokeWidth="2" />
            </pattern>
          </defs>

          <rect x={x(groundStop[0])} y={TOP - 6} width={x(groundStop[1]) - x(groundStop[0])} height={H - TOP}
                fill="url(#hatch)" />

          {hours.map((m) => (
            <g key={m}>
              <line x1={x(m)} x2={x(m)} y1={TOP - 6} y2={H} stroke="var(--grid)" />
              {(m / 60) % 2 === 0 && (
                <text x={x(m)} y={TOP - 12} textAnchor="middle" className="axis">{hhmm(m)}</text>
              )}
            </g>
          ))}

          {rows.list.map((c, i) => {
            const y = TOP + i * ROW
            const label = c.reserve ? `RSV ${c.crew}` : `CRW ${String(c.crew).padStart(2, '0')}`
            return (
              <g key={c.crew}>
                <text x={4} y={y + 10} className={`row-label ${c.stranded ? 'is-stranded' : ''}`}>{label}</text>
                {c.stranded && <text x={LABEL - 6} y={y + 10} textAnchor="end" className="stuck">{c.ends_at}</text>}
                {c.flights.map((f) => {
                  const x1 = x(f.dep)
                  const w = Math.max(2, x(f.arr) - x1)
                  return (
                    <g key={f.flight_no}
                       onMouseEnter={() => setHover({ ...f, crew: label, y })}
                       onMouseLeave={() => setHover(null)}>
                      <rect x={x1} y={y + 2} width={w} height={ROW - 5} rx="1.5"
                            className={f.delay_min >= 15 ? 'bar bar-late' : 'bar'} />
                      {w > 26 && (
                        <text x={x1 + 3} y={y + 10} className="bar-text">{f.dest === 'ATL' ? f.origin : f.dest}</text>
                      )}
                    </g>
                  )
                })}
                {c.duty_limit_at && c.duty_limit_at < END && (
                  <line x1={x(c.duty_limit_at)} x2={x(c.duty_limit_at)} y1={y + 1} y2={y + ROW - 2}
                        className="limit" />
                )}
              </g>
            )
          })}

          {hover && (
            <g className="tip" transform={`translate(${Math.min(x(hover.dep), W - 210)}, ${Math.max(0, hover.y - 30)})`}>
              <rect width="206" height="26" rx="3" />
              <text x="8" y="17">
                {hover.crew} · {hover.flight_no} {hover.origin}→{hover.dest} {hhmm(hover.dep)}
                {hover.delay_min >= 15 ? ` (+${hover.delay_min}m)` : ''}
              </text>
            </g>
          )}
        </svg>
      </div>
      <p className="foot">
        Red airport code: crew ended the day stranded there. A bar running past its red tick was
        legal at takeoff and hit storm holding in the air; FAA rules allow limited extensions for that.
        {rows.idle > 0 && ` ${rows.idle} reserve crew${rows.idle > 1 ? 's' : ''} not needed and not shown.`}
      </p>
    </section>
  )
}
