// One row per strategy. Click a row to see that strategy in the timeline and board.
import { STRATEGIES } from '../strategies'

export default function Scoreboard({ result, selected, onSelect }) {
  const base = result.strategies.original.metrics.cancelled
  return (
    <section className="panel scoreboard">
      <h2 className="panel-title">Recovery comparison</h2>
      <div className="scroll-x">
        <table className="score">
          <thead>
            <tr>
              <th>Strategy</th>
              <th className="num">Cancelled</th>
              <th className="num">vs hold</th>
              <th className="num">Flown</th>
              <th className="num">Avg delay</th>
              <th className="num">Stranded crews</th>
              <th className="num">Reserves used</th>
              <th className="num">Last disruption</th>
            </tr>
          </thead>
          <tbody>
            {STRATEGIES.map((s) => {
              const m = result.strategies[s.key].metrics
              const diff = m.cancelled - base
              return (
                <tr
                  key={s.key}
                  className={selected === s.key ? 'is-selected' : ''}
                  onClick={() => onSelect(s.key)}
                  tabIndex={0}
                  onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(s.key)}
                  aria-selected={selected === s.key}
                >
                  <td>
                    <span className="key" style={{ background: s.color }} />
                    <span className="strat-name">{s.name}</span>
                    <span className="strat-blurb">{s.blurb}</span>
                  </td>
                  <td className="num big">{m.cancelled}</td>
                  <td className={`num ${diff < 0 ? 'good' : diff > 0 ? 'bad' : 'dim'}`}>
                    {s.key === 'original' ? '·' : diff > 0 ? `+${diff}` : diff}
                  </td>
                  <td className="num">{m.completed}/{m.flights}</td>
                  <td className="num">{m.avg_delay_min}m</td>
                  <td className={`num ${m.stranded_crews ? 'bad' : ''}`}>{m.stranded_crews}</td>
                  <td className="num">{m.reserves_used}</td>
                  <td className="num">{m.last_disrupted_flight ?? 'None'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
