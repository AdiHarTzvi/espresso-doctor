import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'
import ShotForm from './components/ShotForm.jsx'
import DiagnosisCard from './components/DiagnosisCard.jsx'
import HistoryList from './components/HistoryList.jsx'
import ProgressPanel from './components/ProgressPanel.jsx'
import UsagePanel from './components/UsagePanel.jsx'

export default function App() {
  const [health, setHealth] = useState(null)
  const [shots, setShots] = useState([])
  const [progress, setProgress] = useState(null)
  const [usage, setUsage] = useState(null)
  const [selected, setSelected] = useState(null) // { shot, diagnosis, error, usage, safety_flags }
  const [diagnosingId, setDiagnosingId] = useState(null)
  const [loadError, setLoadError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [s, p, u] = await Promise.all([api.shots(), api.progress(), api.usage()])
      setShots(s)
      setProgress(p)
      setUsage(u)
      setLoadError(null)
    } catch (e) {
      setLoadError(e.message)
    }
  }, [])

  useEffect(() => {
    api.health().then(setHealth).catch((e) => setLoadError(e.message))
    refresh()
  }, [refresh])

  async function runDiagnosis(shot) {
    setSelected({ shot, diagnosis: null, error: null })
    setDiagnosingId(shot.id)
    try {
      const res = await api.diagnose(shot.id)
      setSelected({ shot, diagnosis: res.result, usage: res.usage, tools: res.tools_used, safety_flags: res.safety_flags })
    } catch (e) {
      setSelected({ shot, diagnosis: null, error: e.message, usage: e.body?.usage })
    } finally {
      setDiagnosingId(null)
      refresh()
    }
  }

  async function handleSaved(shot, diagnoseNow) {
    await refresh()
    if (diagnoseNow) runDiagnosis(shot)
    else setSelected({ shot, diagnosis: null, error: null })
  }

  async function openShot(shot) {
    try {
      const detail = await api.shot(shot.id)
      const d = detail.diagnosis
      setSelected({
        shot: detail,
        diagnosis: d?.result ?? null,
        tools: d?.tools_used,
        safety_flags: detail.safety_flags,
        usage: d && {
          model: d.model, input_tokens: d.input_tokens, output_tokens: d.output_tokens,
          requests: d.requests, tool_calls: d.tool_calls, cost_usd: d.cost_usd,
        },
      })
    } catch (e) {
      setLoadError(e.message)
    }
  }

  async function removeShot(shot) {
    if (!window.confirm(`Delete shot #${shot.id}? This cannot be undone.`)) return
    try {
      await api.deleteShot(shot.id)
      if (selected?.shot?.id === shot.id) setSelected(null)
      refresh()
    } catch (e) {
      setLoadError(e.message)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <img src="/cup.svg" alt="" className="logo" />
        <div>
          <h1>Espresso Doctor</h1>
          <p className="tagline">Log a shot, get one clear change for the next one, and watch your dial-in improve.</p>
        </div>
        {health && <span className="model-chip" title="Configured AI model">AI model: {health.model} · {health.provider}</span>}
      </header>

      {health && !health.api_key_configured && (
        <div className="banner warn" role="alert">
          <strong>No AI key found.</strong> You can still record shots, but diagnosis needs
          <code>PORTKEY_API_KEY</code> or <code>OPENAI_API_KEY</code> in a <code>.env</code> file (see README), then restart the backend.
        </div>
      )}
      {loadError && <div className="banner error" role="alert">{loadError}</div>}

      <main className="grid">
        <section className="card">
          <h2>Record a shot</h2>
          <ShotForm onSaved={handleSaved} busy={diagnosingId !== null} canDiagnose={health?.api_key_configured} />
        </section>

        <section className="card diagnosis-card" aria-live="polite">
          <h2>Diagnosis</h2>
          <DiagnosisCard
            selected={selected}
            loading={selected && diagnosingId === selected.shot.id}
            onRetry={() => selected && runDiagnosis(selected.shot)}
            canDiagnose={health?.api_key_configured}
          />
        </section>

        <section className="card wide">
          <h2>Progress</h2>
          <ProgressPanel progress={progress} />
        </section>

        <section className="card wide">
          <h2>Shot history</h2>
          <HistoryList
            shots={shots}
            selectedId={selected?.shot?.id}
            diagnosingId={diagnosingId}
            onOpen={openShot}
            onDiagnose={runDiagnosis}
            onDelete={removeShot}
            canDiagnose={health?.api_key_configured}
          />
        </section>

        <section className="card wide">
          <h2>AI usage &amp; cost</h2>
          <UsagePanel usage={usage} />
        </section>
      </main>

      <footer className="footer">
        Advice is a hypothesis, not a guarantee. Change one thing at a time and trust your taste.
      </footer>
    </div>
  )
}
