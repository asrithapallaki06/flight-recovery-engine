// A gate-style flight board for the selected strategy.
import { useMemo, useState } from 'react'

const CITY = {
  SAV: 'Savannah', BNA: 'Nashville', CLT: 'Charlotte', JAX: 'Jacksonville', RDU: 'Raleigh-Durham',
  MCO: 'Orlando', TPA: 'Tampa', DCA: 'Washington', FLL: 'Fort Lauderdale', MIA: 'Miami',
  ORD: 'Chicago', DTW: 'Detroit', IAH: 'Houston', LGA: 'New York-LGA', JFK: 'New York-JFK',
  DFW: 'Dallas', AUS: 'Austin', BOS: 'Boston', MSP: 'Minneapolis', DEN: 'Denver',
  PHX: 'Phoenix', SLC: 'Salt Lake City', LAX: 'Los Angeles', SFO: 'San Francisco', SEA: 'Seattle',
}

function remark(f) {
  if (f.status === 'cancelled') return { text: 'CANCELLED', cls: 'r-cxl' }
  if (f.delay_min >= 15) {
    const h = Math.floor(f.delay_min / 60)
    const m = String(f.delay_min % 60).padStart(2, '0')
    return { text: `DELAYED ${h ? `${h}H${m}` : `${f.delay_min}M`}`, cls: 'r-late' }
  }
  return { text: 'ON TIME', cls: 'r-ok' }
}

export default function DeparturesBoard({ flights, strategyName }) {
  const [direction, setDirection] = useState('out')
  const [onlyIssues, setOnlyIssues] = useState(true)

  const rows = useMemo(() => {
    return flights
      .filter((f) => (direction === 'out' ? f.route.startsWith('ATL') : f.route.endsWith('ATL')))
      .filter((f) => !onlyIssues || f.status === 'cancelled' || f.delay_min >= 15)
  }, [flights, direction, onlyIssues])

  return (
    <section className="panel board-panel">
      <div className="panel-head">
        <h2 className="panel-title">ATL {direction === 'out' ? 'departures' : 'arrivals'} · {strategyName}</h2>
        <div className="seg" role="tablist">
          <button role="tab" aria-selected={direction === 'out'} className={direction === 'out' ? 'on' : ''}
                  onClick={() => setDirection('out')}>Departures</button>
          <button role="tab" aria-selected={direction === 'in'} className={direction === 'in' ? 'on' : ''}
                  onClick={() => setDirection('in')}>Arrivals</button>
        </div>
        <label className="check">
          <input id="board-issues" type="checkbox" checked={onlyIssues} onChange={(e) => setOnlyIssues(e.target.checked)} />
          Only delayed or cancelled
        </label>
      </div>
      <div className="board-scroll">
        <table className="board">
          <thead>
            <tr>
              <th>Sched</th><th>Flight</th><th>{direction === 'out' ? 'To' : 'From'}</th>
              <th>Actual</th><th>Remarks</th><th className="num">Delay risk</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((f) => {
              const r = remark(f)
              const code = direction === 'out' ? f.route.slice(4) : f.route.slice(0, 3)
              return (
                <tr key={f.id}>
                  <td>{f.sched_dep}</td>
                  <td>{f.flight_no}</td>
                  <td><span className="city">{CITY[code] ?? code}</span> <span className="code">{code}</span></td>
                  <td>{f.actual_dep ?? '--:--'}</td>
                  <td className={r.cls}>{r.text}</td>
                  <td className="num">{Math.round(f.risk * 100)}%</td>
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr><td colSpan="6" className="empty">All flights operating normally.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
