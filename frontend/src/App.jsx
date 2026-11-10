// The page: set up a ground stop, run it, and compare the three recovery strategies.
import { useEffect, useState } from 'react'
import { getModelMetrics, runSimulation } from './api'
import BacklogChart from './components/BacklogChart'
import Controls from './components/Controls'
import CrewTimeline from './components/CrewTimeline'
import DeparturesBoard from './components/DeparturesBoard'
import Scoreboard from './components/Scoreboard'
import { STRATEGIES, hhmm } from './strategies'

const DEFAULTS = { groundStopStart: 13, groundStopEnd: 18, reserveCrews: 6, useRisk: true }

export default function App() {
  const [form, setForm] = useState(DEFAULTS)
  const [ranWith, setRanWith] = useState(DEFAULTS)
  const [result, setResult] = useState(null)
  const [model, setModel] = useState(null)
  const [selected, setSelected] = useState('optimized')
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function run(params = form) {
    setRunning(true)
    setError('')
    try {
      setResult(await runSimulation(params))
      setRanWith(params)
    } catch (e) {
      setError(`${e.message}. Is the backend running on port 8000?`)
    } finally {
      setRunning(false)
    }
  }

  // Load the model numbers and run the default scenario when the page opens.
  useEffect(() => {
    getModelMetrics().then(setModel).catch(() => {})
    run(DEFAULTS)
  }, [])

  const strategy = STRATEGIES.find((s) => s.key === selected)
  const stop = [ranWith.groundStopStart, ranWith.groundStopEnd]

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="station">ATL</span>
          <div>
            <h1>IRROPS Crew Recovery</h1>
            <p className="sub">Thunderstorm ground stop simulation · hub-and-spoke day · simplified FAA duty rules</p>
          </div>
        </div>
        <Controls value={form} onChange={setForm} onRun={() => run()} running={running} />
      </header>

      {error && <p className="error banner">{error}</p>}
      {!result && !error && <p className="loading">Building the day and running the first scenario…</p>}

      {result && (
        <main className="grid">
          <div className="status-line">
            <span>Ground stop <b>{hhmm(stop[0] * 60)}–{hhmm(stop[1] * 60)}</b></span>
            <span><b>{result.strategies.original.metrics.flights}</b> flights</span>
            <span><b>{result.scenario.planned_crews}</b> planned crews</span>
            <span><b>{ranWith.reserveCrews}</b> reserves</span>
            <span>Delay model <b>{ranWith.useRisk ? 'on' : 'off'}</b></span>
            {model && (
              <span className="model-note">
                Delay model AUC <b>{model.model_auc}</b> vs {model.baseline_auc} baseline · trained on{' '}
                <b>{model.data_source === 'real' ? 'real DOT flight data' : 'sample data'}</b>
              </span>
            )}
          </div>
          <Scoreboard result={result} selected={selected} onSelect={setSelected} />
          <BacklogChart result={result} groundStop={stop} />
          <CrewTimeline crews={result.strategies[selected].crews} groundStop={[stop[0] * 60, stop[1] * 60]}
                        strategyName={strategy.name} />
          <DeparturesBoard flights={result.strategies[selected].flights} strategyName={strategy.name} />
        </main>
      )}
    </div>
  )
}
