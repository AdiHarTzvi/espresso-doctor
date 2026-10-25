export default function UsagePanel({ usage }) {
  if (!usage) return <p className="muted">Loading…</p>
  if (!usage.runs) return <p className="muted">No AI diagnoses yet. Token usage and approximate cost will be logged here for every run.</p>
  const cost = usage.cost_usd == null ? 'n/a' : `$${usage.cost_usd.toFixed(4)}`
  return (
    <div className="usage">
      <div className="stats">
        <div className="stat"><span className="stat-num">{usage.runs}</span><span>AI runs ({usage.ok_runs} ok)</span></div>
        <div className="stat"><span className="stat-num">{usage.input_tokens.toLocaleString()}</span><span>input tokens</span></div>
        <div className="stat"><span className="stat-num">{usage.output_tokens.toLocaleString()}</span><span>output tokens</span></div>
        <div className="stat"><span className="stat-num">{cost}</span><span>approx. total cost</span></div>
      </div>
      <details>
        <summary>Last {usage.recent.length} runs</summary>
        <div className="table-wrap">
          <table className="history">
            <thead><tr><th>Run</th><th>Shot</th><th>Status</th><th>Model</th><th>In</th><th>Out</th><th>Req.</th><th>Cost</th></tr></thead>
            <tbody>
              {usage.recent.map((r) => (
                <tr key={r.id}>
                  <td data-label="Run">{r.id}</td>
                  <td data-label="Shot">#{r.shot_id}</td>
                  <td data-label="Status" title={r.error ?? ''}>{r.status === 'ok' ? '✓ ok' : '✕ error'}</td>
                  <td data-label="Model">{r.model}</td>
                  <td data-label="In">{r.input_tokens}</td>
                  <td data-label="Out">{r.output_tokens}</td>
                  <td data-label="Req.">{r.requests}</td>
                  <td data-label="Cost">{r.cost_usd == null ? 'n/a' : `$${r.cost_usd.toFixed(5)}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="muted small">Estimated cost = measured tokens × official OpenAI list price for the configured model (cached input at the cached rate). Actual gateway billing may differ.</p>
    </div>
  )
}
