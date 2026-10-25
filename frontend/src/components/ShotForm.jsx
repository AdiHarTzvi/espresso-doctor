import { useState } from 'react'
import { api } from '../api.js'

// Same limits as the backend (backend/app/schemas.py). The backend re-validates everything.
const LIMITS = {
  dose_g: { min: 5, max: 30, label: 'Dose', unit: 'g', step: 0.1, hint: 'Ground coffee in the basket' },
  yield_g: { min: 5, max: 120, label: 'Yield', unit: 'g', step: 0.1, hint: 'Espresso in the cup' },
  time_s: { min: 5, max: 120, label: 'Time', unit: 's', step: 1, hint: 'From pump on to stop' },
}
const TASTES = [
  { value: 'sour', label: 'Sour', icon: '🍋' },
  { value: 'bitter', label: 'Bitter', icon: '🌰' },
  { value: 'balanced', label: 'Balanced', icon: '✨' },
  { value: 'weak', label: 'Weak', icon: '💧' },
  { value: 'other', label: 'Other', icon: '❔' },
]
const STORAGE_KEY = 'espresso-doctor:last-recipe'

function initialValues() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    return { dose_g: saved.dose_g ?? '18', yield_g: saved.yield_g ?? '36', time_s: '', grind_setting: saved.grind_setting ?? '', taste: '', notes: '' }
  } catch {
    return { dose_g: '18', yield_g: '36', time_s: '', grind_setting: '', taste: '', notes: '' }
  }
}

function validate(v) {
  const errors = {}
  for (const [key, lim] of Object.entries(LIMITS)) {
    const n = Number(v[key])
    if (v[key] === '' || Number.isNaN(n)) errors[key] = 'Required'
    else if (n < lim.min || n > lim.max) errors[key] = `Must be ${lim.min}–${lim.max} ${lim.unit}`
  }
  if (!errors.dose_g && !errors.yield_g) {
    const r = Number(v.yield_g) / Number(v.dose_g)
    if (r < 0.5 || r > 6) errors.yield_g = `Ratio 1:${r.toFixed(2)} looks wrong – check grams`
  }
  if (!v.taste) errors.taste = 'Pick how it tasted'
  if (v.notes.length > 500) errors.notes = 'Max 500 characters'
  if (v.grind_setting.length > 40) errors.grind_setting = 'Max 40 characters'
  return errors
}

export default function ShotForm({ onSaved, busy, canDiagnose }) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [saving, setSaving] = useState(false)

  const set = (key) => (e) => setValues((v) => ({ ...v, [key]: e.target.value }))
  const dose = Number(values.dose_g)
  const yld = Number(values.yield_g)
  const ratio = dose > 0 && yld > 0 ? yld / dose : null

  async function submit(diagnoseNow) {
    const errs = validate(values)
    setErrors(errs)
    setServerError(null)
    if (Object.keys(errs).length) return
    setSaving(true)
    try {
      const shot = await api.createShot({
        dose_g: Number(values.dose_g),
        yield_g: Number(values.yield_g),
        time_s: Number(values.time_s),
        grind_setting: values.grind_setting.trim() || null,
        taste: values.taste,
        notes: values.notes.trim() || null,
      })
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ dose_g: values.dose_g, yield_g: values.yield_g, grind_setting: values.grind_setting }))
      setValues((v) => ({ ...v, time_s: '', taste: '', notes: '' }))
      onSaved(shot, diagnoseNow)
    } catch (e) {
      setServerError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="shot-form" onSubmit={(e) => { e.preventDefault(); submit(canDiagnose) }} noValidate>
      <div className="num-row">
        {Object.entries(LIMITS).map(([key, lim]) => (
          <label key={key} className={`field ${errors[key] ? 'has-error' : ''}`}>
            <span className="field-label">{lim.label} <em>({lim.unit})</em></span>
            <input
              type="number" inputMode="decimal" min={lim.min} max={lim.max} step={lim.step}
              value={values[key]} onChange={set(key)} name={key} placeholder={key === 'time_s' ? 'e.g. 28' : ''}
              aria-invalid={!!errors[key]}
            />
            <span className="field-hint">{errors[key] || lim.hint}</span>
          </label>
        ))}
      </div>

      <div className="ratio-preview" aria-live="polite">
        Brew ratio: <strong>{ratio ? `1:${ratio.toFixed(2)}` : '—'}</strong>
        <span className="muted"> · a common starting point is about 1:2</span>
      </div>

      <label className={`field ${errors.grind_setting ? 'has-error' : ''}`}>
        <span className="field-label">Grind setting <em>(optional)</em></span>
        <input type="text" value={values.grind_setting} onChange={set('grind_setting')} name="grind_setting" maxLength={40} placeholder="e.g. 12" />
        {errors.grind_setting && <span className="field-hint">{errors.grind_setting}</span>}
      </label>

      <fieldset className={`taste ${errors.taste ? 'has-error' : ''}`}>
        <legend className="field-label">Taste</legend>
        <div className="taste-options">
          {TASTES.map((t) => (
            <label key={t.value} className={`taste-pill ${values.taste === t.value ? 'active' : ''}`}>
              <input type="radio" name="taste" value={t.value} checked={values.taste === t.value} onChange={set('taste')} />
              <span aria-hidden="true">{t.icon}</span> {t.label}
            </label>
          ))}
        </div>
        {errors.taste && <span className="field-hint">{errors.taste}</span>}
      </fieldset>

      <label className={`field ${errors.notes ? 'has-error' : ''}`}>
        <span className="field-label">Notes <em>(optional)</em></span>
        <textarea rows={3} value={values.notes} onChange={set('notes')} name="notes" maxLength={500}
          placeholder="e.g. channeling, beans roasted 2 weeks ago, thin body" />
        <span className="field-hint">{errors.notes || `${values.notes.length}/500`}</span>
      </label>

      {serverError && <div className="banner error" role="alert">{serverError}</div>}

      <div className="actions">
        <button type="submit" className="btn primary" disabled={saving || busy || !canDiagnose}
          title={canDiagnose ? '' : 'Add PORTKEY_API_KEY or OPENAI_API_KEY to enable diagnosis'}>
          {saving ? 'Saving…' : 'Save & diagnose'}
        </button>
        <button type="button" className="btn ghost" disabled={saving} onClick={() => submit(false)}>
          Save only
        </button>
      </div>
    </form>
  )
}
