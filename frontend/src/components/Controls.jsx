// The scenario bar across the top: ground stop window, reserves, risk model, run.
import { hhmm } from '../strategies'

const HOURS = Array.from({ length: 33 }, (_, i) => 6 + i * 0.5) // 06:00 to 22:00

export default function Controls({ value, onChange, onRun, running }) {
  const set = (key, cast = Number) => (e) => onChange({ ...value, [key]: cast(e.target.value) })
  const invalid = value.groundStopEnd <= value.groundStopStart

  return (
    <form
      className="controls"
      onSubmit={(e) => {
        e.preventDefault()
        if (!invalid) onRun()
      }}
    >
      <fieldset className="ctl">
        <legend>Ground stop</legend>
        <select id="gs-start" aria-label="Ground stop starts" value={value.groundStopStart} onChange={set('groundStopStart')}>
          {HOURS.map((h) => <option key={h} value={h}>{hhmm(h * 60)}</option>)}
        </select>
        <span className="dash">to</span>
        <select id="gs-end" aria-label="Ground stop ends" value={value.groundStopEnd} onChange={set('groundStopEnd')}>
          {HOURS.map((h) => <option key={h} value={h}>{hhmm(h * 60)}</option>)}
        </select>
      </fieldset>

      <fieldset className="ctl">
        <legend>Reserve crews</legend>
        <select id="reserves" aria-label="Reserve crews" value={value.reserveCrews} onChange={set('reserveCrews')}>
          {Array.from({ length: 16 }, (_, i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </fieldset>

      <fieldset className="ctl">
        <legend>Delay model</legend>
        <button
          type="button"
          id="use-risk"
          className={`switch ${value.useRisk ? 'switch--on' : ''}`}
          aria-pressed={value.useRisk}
          onClick={() => onChange({ ...value, useRisk: !value.useRisk })}
        >
          {value.useRisk ? 'ON' : 'OFF'}
        </button>
      </fieldset>

      <button type="submit" className="run" disabled={running || invalid}>
        {running ? 'Re-planning…' : 'Run recovery'}
      </button>
      {invalid && <p className="error">The ground stop has to end after it starts.</p>}
    </form>
  )
}
