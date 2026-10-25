import { useState } from 'react'

// Single-series line chart (one per measure, never a dual axis) with a shaded rule-of-thumb band
// and a hover tooltip. The title names the series, so no legend box is needed.
const W = 480
const H = 190
const PAD = { top: 14, right: 16, bottom: 28, left: 40 }

function niceTicks(min, max, count = 4) {
  const span = max - min || 1
  const step = Math.pow(10, Math.floor(Math.log10(span / count)))
  const err = span / count / step
  const mult = err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1
  const s = step * mult
  const ticks = []
  for (let v = Math.ceil(min / s) * s; v <= max + 1e-9; v += s) ticks.push(Number(v.toFixed(6)))
  return ticks
}

export default function TrendChart({ title, points, band, format, bandLabel }) {
  const [hover, setHover] = useState(null)
  if (points.length < 2) return null

  const ys = points.map((p) => p.y).concat(band)
  let yMin = Math.min(...ys)
  let yMax = Math.max(...ys)
  const padY = (yMax - yMin) * 0.12 || 1
  yMin -= padY
  yMax += padY
  const ticks = niceTicks(yMin, yMax)
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const x = (i) => PAD.left + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW)
  const y = (v) => PAD.top + innerH - ((v - yMin) / (yMax - yMin)) * innerH
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.y).toFixed(1)}`).join(' ')
  const colW = innerW / Math.max(points.length - 1, 1)
  const last = points[points.length - 1]
  const hp = hover != null ? points[hover] : null

  return (
    <figure className="chart">
      <figcaption>
        <strong>{title}</strong> <span className="muted">· shaded = {bandLabel} (rule of thumb)</span>
      </figcaption>
      <div className="chart-box" onMouseLeave={() => setHover(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title} for your last ${points.length} shots`}>
          <rect x={PAD.left} y={y(band[1])} width={innerW} height={Math.max(0, y(band[0]) - y(band[1]))} className="band" />
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} className="grid" />
              <text x={PAD.left - 6} y={y(t)} className="axis" textAnchor="end" dominantBaseline="middle">{format(t)}</text>
            </g>
          ))}
          <line x1={PAD.left} x2={W - PAD.right} y1={PAD.top + innerH} y2={PAD.top + innerH} className="baseline" />
          <text x={PAD.left} y={H - 8} className="axis">#{points[0].id}</text>
          <text x={W - PAD.right} y={H - 8} className="axis" textAnchor="end">#{last.id}</text>
          <path d={path} className="line" />
          {hover != null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + innerH} className="crosshair" />}
          {points.map((p, i) => (
            <circle key={p.id} cx={x(i)} cy={y(p.y)} r={hover === i ? 6 : 4.5} className={`dot ${p.taste === 'balanced' ? 'dot-good' : ''}`} />
          ))}
          <text x={x(points.length - 1) - 8} y={y(last.y) - 10} className="direct-label" textAnchor="end">{format(last.y)}</text>
          {points.map((p, i) => (
            <rect key={`hit-${p.id}`} x={x(i) - colW / 2} y={PAD.top} width={colW} height={innerH}
              fill="transparent" onMouseEnter={() => setHover(i)} onFocus={() => setHover(i)} tabIndex={0}
              aria-label={`Shot ${p.id}: ${format(p.y)}, ${p.taste}`} />
          ))}
        </svg>
        {hp && (
          <div className="tooltip" style={{ left: `${(x(hover) / W) * 100}%`, top: `${(y(hp.y) / H) * 100}%` }}>
            <strong>Shot #{hp.id}</strong>
            <span>{format(hp.y)}</span>
            <span>Taste: {hp.taste}</span>
            {hp.grind && <span>Grind: {hp.grind}</span>}
          </div>
        )}
      </div>
    </figure>
  )
}
