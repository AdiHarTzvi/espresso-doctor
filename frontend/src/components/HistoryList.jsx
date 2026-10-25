function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function HistoryList({ shots, selectedId, diagnosingId, onOpen, onDiagnose, onDelete, canDiagnose }) {
  if (!shots.length) return <p className="muted">No shots yet. Your first one will appear here.</p>
  return (
    <div className="table-wrap">
      <table className="history">
        <thead>
          <tr>
            <th>#</th><th>When</th><th>Dose</th><th>Yield</th><th>Ratio</th><th>Time</th><th>Grind</th><th>Taste</th><th>Notes</th><th></th>
          </tr>
        </thead>
        <tbody>
          {shots.map((s) => (
            <tr key={s.id} className={s.id === selectedId ? 'selected' : ''}>
              <td data-label="#">{s.id}</td>
              <td data-label="When">{formatDate(s.created_at)}</td>
              <td data-label="Dose">{s.dose_g} g</td>
              <td data-label="Yield">{s.yield_g} g</td>
              <td data-label="Ratio">1:{s.brew_ratio.toFixed(2)}</td>
              <td data-label="Time">{s.time_s} s</td>
              <td data-label="Grind">{s.grind_setting ?? '—'}</td>
              <td data-label="Taste"><span className={`taste-tag t-${s.taste}`}>{s.taste}</span></td>
              <td data-label="Notes" className="notes-cell" title={s.notes ?? ''}>{s.notes ?? '—'}</td>
              <td className="row-actions">
                {s.has_diagnosis ? (
                  <button className="btn small" onClick={() => onOpen(s)}>View</button>
                ) : (
                  <button className="btn small" disabled={!canDiagnose || diagnosingId !== null} onClick={() => onDiagnose(s)}>
                    {diagnosingId === s.id ? '…' : 'Diagnose'}
                  </button>
                )}
                <button className="btn small ghost" aria-label={`Delete shot ${s.id}`} onClick={() => onDelete(s)}>✕</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
