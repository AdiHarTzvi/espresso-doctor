import TrendChart from './TrendChart.jsx'

const VERDICTS = {
  improving: { icon: '▲', label: 'Improving', cls: 'good' },
  steady: { icon: '●', label: 'Dialed in', cls: 'good' },
  worse: { icon: '▼', label: 'Got worse', cls: 'bad' },
  no_change: { icon: '■', label: 'No change yet', cls: 'neutral' },
  changed: { icon: '◆', label: 'Changed', cls: 'neutral' },
  not_enough_data: { icon: '…', label: 'Not enough data', cls: 'neutral' },
}

function signed(n, unit = '', digits = 1) {
  if (n === 0) return `±0${unit}`
  return `${n > 0 ? '+' : '−'}${Math.abs(n).toFixed(digits)}${unit}`
}

export default function ProgressPanel({ progress }) {
  if (!progress) return <p className="muted">Loading…</p>
  const v = VERDICTS[progress.verdict] ?? VERDICTS.not_enough_data
  const { latest, previous, deltas, rule_of_thumb: rot } = progress
  const pts = progress.series

  return (
    <div className="progress">
      <div className="progress-top">
        <div className={`verdict ${v.cls}`}>
          <span className="verdict-icon" aria-hidden="true">{v.icon}</span>
          <div>
            <strong>{v.label}</strong>
            <p>{progress.verdict_text}</p>
            <p className="muted small">Judged from your taste ratings (latest vs previous shot).</p>
          </div>
        </div>
        <div className="stats">
          <div className="stat"><span className="stat-num">{progress.total_shots}</span><span>shots logged</span></div>
          <div className="stat"><span className="stat-num">{progress.balanced_shots}</span><span>balanced</span></div>
          {progress.balanced_rate_last_5 != null && (
            <div className="stat"><span className="stat-num">{Math.round(progress.balanced_rate_last_5 * 100)}%</span><span>balanced, last 5</span></div>
          )}
        </div>
      </div>

      {deltas && (
        <div className="table-wrap">
          <table className="compare">
            <thead>
              <tr><th></th><th>Previous #{previous.id}</th><th>Latest #{latest.id}</th><th>Change</th></tr>
            </thead>
            <tbody>
              <tr><th>Dose</th><td>{previous.dose_g} g</td><td>{latest.dose_g} g</td><td>{signed(deltas.dose_g, ' g')}</td></tr>
              <tr><th>Yield</th><td>{previous.yield_g} g</td><td>{latest.yield_g} g</td><td>{signed(deltas.yield_g, ' g')}</td></tr>
              <tr><th>Ratio</th><td>1:{previous.brew_ratio.toFixed(2)}</td><td>1:{latest.brew_ratio.toFixed(2)}</td><td>{signed(deltas.brew_ratio, '', 2)}</td></tr>
              <tr><th>Time</th><td>{previous.time_s} s</td><td>{latest.time_s} s</td><td>{signed(deltas.time_s, ' s', 0)}</td></tr>
              <tr><th>Grind</th><td>{previous.grind_setting ?? '—'}</td><td>{latest.grind_setting ?? '—'}</td><td>{deltas.grind_changed ? 'changed' : 'same'}</td></tr>
              <tr><th>Taste</th><td>{previous.taste}</td><td>{latest.taste}</td><td>{previous.taste === latest.taste ? 'same' : 'changed'}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      {pts.length >= 2 && (
        <div className="charts">
          <TrendChart
            title="Extraction time (s)"
            points={pts.map((p) => ({ id: p.id, y: p.time_s, taste: p.taste, grind: p.grind_setting }))}
            band={[rot.time_low, rot.time_high]}
            bandLabel={`${rot.time_low}–${rot.time_high} s`}
            format={(n) => `${Math.round(n)} s`}
          />
          <TrendChart
            title="Brew ratio (yield ÷ dose)"
            points={pts.map((p) => ({ id: p.id, y: p.brew_ratio, taste: p.taste, grind: p.grind_setting }))}
            band={[rot.ratio_low, rot.ratio_high]}
            bandLabel={`1:${rot.ratio_low}–1:${rot.ratio_high}`}
            format={(n) => `1:${n.toFixed(1)}`}
          />
        </div>
      )}
      {pts.length >= 2 && <p className="muted small">Filled dots = shots you rated balanced. Hover a point for details.</p>}
    </div>
  )
}
