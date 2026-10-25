const VARIABLE_LABELS = {
  grind: 'Grind', dose: 'Dose', yield: 'Yield', time: 'Time', temperature: 'Temperature', puck_prep: 'Puck prep', none: 'No change',
}
const CONFIDENCE = {
  low: { label: 'Low confidence', icon: '◔' },
  medium: { label: 'Medium confidence', icon: '◑' },
  high: { label: 'High confidence', icon: '●' },
}

export function ShotSummary({ shot }) {
  return (
    <div className="shot-summary">
      <span className="tag">Shot #{shot.id}</span>
      <span>{shot.dose_g} g → {shot.yield_g} g</span>
      <span>{shot.time_s} s</span>
      <span>1:{Number(shot.brew_ratio).toFixed(2)}</span>
      {shot.grind_setting && <span>grind {shot.grind_setting}</span>}
      <span className={`taste-tag t-${shot.taste}`}>{shot.taste}</span>
    </div>
  )
}

export function UsageLine({ usage, tools }) {
  if (!usage) return null
  const cost = usage.cost_usd == null ? 'cost n/a' : `≈ $${usage.cost_usd.toFixed(5)}`
  return (
    <p className="usage-line">
      {usage.input_tokens?.toLocaleString()} in / {usage.output_tokens?.toLocaleString()} out tokens · {usage.requests} requests · {cost}
      {tools?.length ? ` · tools: ${[...new Set(tools)].join(', ')}` : ''}
    </p>
  )
}

export default function DiagnosisCard({ selected, loading, onRetry, canDiagnose }) {
  if (!selected) {
    return (
      <div className="empty">
        <p>Record a shot and press <strong>Save &amp; diagnose</strong>.</p>
        <p className="muted">The doctor compares it with your previous shots and suggests one change.</p>
      </div>
    )
  }
  const { shot, diagnosis: d, error, usage, tools, safety_flags } = selected

  return (
    <div className="diagnosis">
      <ShotSummary shot={shot} />

      {loading && (
        <div className="loading" role="status">
          <span className="spinner" aria-hidden="true" /> Analysing this shot against your history…
        </div>
      )}

      {error && !loading && (
        <div className="banner error" role="alert">
          {error}
          {canDiagnose && <button className="btn small" onClick={onRetry}>Retry</button>}
          <UsageLine usage={usage} />
        </div>
      )}

      {!d && !loading && !error && (
        <div className="empty">
          <p>No diagnosis yet for this shot.</p>
          {canDiagnose && <button className="btn primary" onClick={onRetry}>Diagnose this shot</button>}
        </div>
      )}

      {d && !loading && (
        <>
          {safety_flags?.includes('provider_filter_blocked_notes_retried_without_them') && (
            <div className="banner info">The AI provider's safety filter rejected this shot's notes, so the diagnosis was made without them.</div>
          )}
          {safety_flags?.includes('notes_look_like_instructions') && !safety_flags?.includes('provider_filter_blocked_notes_retried_without_them') && (
            <div className="banner info">Your notes contained text that looked like instructions to the AI. It was treated as plain data and ignored.</div>
          )}

          <div className="next-shot">
            <span className="eyebrow">Next shot · change one thing</span>
            <div className="adjustment">
              <span className="var-chip">{VARIABLE_LABELS[d.recommended_adjustment.variable] ?? d.recommended_adjustment.variable}</span>
              <strong>{d.recommended_adjustment.action}</strong>
            </div>
            {d.recommended_adjustment.target && <p className="target">Aim for: {d.recommended_adjustment.target}</p>}
          </div>

          <h3>What probably happened</h3>
          <p>{d.diagnosis}</p>

          <h3>Why this change</h3>
          <p>{d.explanation}</p>

          <div className="fact-hyp">
            <div>
              <h4>Facts <span className="muted">(from your numbers)</span></h4>
              <ul>{d.facts.map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
            <div>
              <h4>Hypotheses <span className="muted">(not certain)</span></h4>
              <ul>{d.hypotheses.map((h, i) => <li key={i}>{h}</li>)}</ul>
            </div>
          </div>

          <div className={`confidence c-${d.confidence}`}>
            <span aria-hidden="true">{CONFIDENCE[d.confidence]?.icon}</span>
            <strong>{CONFIDENCE[d.confidence]?.label}.</strong> {d.uncertainty}
          </div>

          <UsageLine usage={usage} tools={tools} />
        </>
      )}
    </div>
  )
}
