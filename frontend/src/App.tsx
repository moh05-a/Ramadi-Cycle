import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getDashboard, reviewAlert, runScenario, type Alert, type Dashboard, type Decision } from './api'

const SCENARIOS = [
  ['reset', 'Reset'],
  ['stable', 'Stable Shift'],
  ['surge', 'Surge'],
  ['lab_delay', 'Lab Delay'],
  ['bed_block', 'Bed Block'],
] as const

const SEVERITY = { high: 'border-red-500 bg-red-50', medium: 'border-amber-500 bg-amber-50', low: 'border-slate-400 bg-slate-50' }

const hhmm = (iso: string) => new Date(iso).toISOString().slice(11, 16)
const minsBetween = (from: string, to: string) => Math.round((Date.parse(to) - Date.parse(from)) / 60000)

export default function App() {
  const [d, setD] = useState<Dashboard>()
  const [error, setError] = useState('')
  const [role, setRole] = useState('charge_nurse')

  const run = (p: Promise<Dashboard>) =>
    p.then((next) => { setD(next); setError('') }).catch((e: Error) => setError(e.message))

  useEffect(() => { run(getDashboard()) }, [])

  const review = (a: Alert, decision: Decision) => {
    let reason = ''
    if (decision === 'dismiss' || decision === 'override') {
      reason = window.prompt(`Reason to ${decision} "${a.title}" (required):`)?.trim() ?? ''
      if (!reason) return
    }
    run(reviewAlert(a.id, decision, reason, role))
  }

  if (!d) return <p className="p-8">{error ? `Backend unreachable: ${error}` : 'Loading…'}</p>

  const m = d.metrics
  const active = d.alerts.filter((a) => a.status === 'open' || a.status === 'acknowledged')
  const closed = d.alerts.filter((a) => !active.includes(a))

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 text-sm">
      <div className="bg-purple-700 text-white text-center font-semibold py-1 tracking-wide">
        SIMULATED ENVIRONMENT — FICTIONAL PATIENTS — NOT FOR CLINICAL USE
      </div>

      <header className="flex flex-wrap items-center gap-2 p-4 bg-white border-b">
        <h1 className="text-xl font-bold mr-4">CARE <span className="font-normal text-slate-500">ED board · sim time {hhmm(d.now)} UTC</span></h1>
        {SCENARIOS.map(([id, label]) => (
          <button key={id} onClick={() => run(runScenario(id))} className="px-3 py-1.5 rounded bg-slate-800 text-white hover:bg-slate-700">
            {label}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2">
          Reviewer
          <select value={role} onChange={(e) => setRole(e.target.value)} className="border rounded px-2 py-1">
            <option value="charge_nurse">Charge nurse</option>
            <option value="clinician">Clinician</option>
          </select>
        </label>
      </header>

      {error && <div role="alert" className="m-4 p-2 rounded bg-red-100 text-red-800">{error}</div>}

      <section className="grid grid-cols-2 md:grid-cols-6 gap-3 p-4">
        <Tile label="Active patients" value={m.activePatients} />
        <Tile label="Waiting" value={m.waiting} />
        <Tile label="Longest wait" value={`${m.longestWaitMin} min`} />
        <Tile label="Pending tasks" value={m.pendingTasks} />
        <Tile label="Beds available" value={`${m.bedsAvailable} / ${m.bedsTotal}`} />
        <Tile label="Lab turnaround" value={`${m.labTurnaroundMin} min`} />
      </section>

      <main className="grid lg:grid-cols-3 gap-4 px-4">
        <Panel title={`Patient queue (${d.patients.length})`}>
          {d.patients.map((p) => (
            <div key={p.id} className="p-2 rounded bg-white border">
              <div className="flex justify-between font-medium">
                <span>{p.alias} <span className="text-slate-500">· {p.ageBand || '—'}</span></span>
                <span className={p.status === 'waiting' ? 'text-amber-700' : 'text-green-700'}>{p.status.replace('_', ' ')}</span>
              </div>
              <div className="text-slate-600">
                {p.area || <span className="text-red-600">area missing</span>} · waited {minsBetween(p.arrivedAt, d.now)} min ·
                reassessed {minsBetween(p.lastReassessedAt, d.now)} min ago{p.pendingTest && ` · pending ${p.pendingTest}`}
              </div>
            </div>
          ))}
        </Panel>

        <Panel title={`Alerts (${active.length} active)`}>
          {active.length === 0 && <p className="text-slate-500">No active alerts.</p>}
          {active.map((a) => <AlertCard key={a.id} a={a} onReview={review} />)}
          {closed.length > 0 && (
            <details className="text-slate-600">
              <summary className="cursor-pointer">Closed / resolved ({closed.length})</summary>
              {closed.map((a) => <div key={a.id} className="pl-2">{a.title} — {a.status}</div>)}
            </details>
          )}
        </Panel>

        <Panel title="Action queue">
          {d.tasks.map((t) => {
            const overdue = t.status === 'open' && Date.parse(t.dueAt) < Date.parse(d.now)
            return (
              <div key={t.id} className={`p-2 rounded border bg-white ${t.status === 'done' ? 'opacity-50 line-through' : ''}`}>
                <div className="font-medium">{t.type} <span className="text-slate-500">· {t.caseId}</span></div>
                <div className={overdue ? 'text-red-700' : 'text-slate-600'}>
                  {t.owner} · due {hhmm(t.dueAt)}{overdue && ' (overdue)'} · {t.status}
                </div>
              </div>
            )
          })}
        </Panel>
      </main>

      <section className="grid lg:grid-cols-2 gap-4 p-4">
        <Panel title="Department trend">
          <div className="h-64 bg-white rounded border p-2">
            <ResponsiveContainer>
              <LineChart data={d.history.map((h) => ({ ...h, at: hhmm(h.at) }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="at" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line dataKey="waiting" name="Waiting" stroke="#d97706" />
                <Line dataKey="pendingTasks" name="Pending tasks" stroke="#7c3aed" />
                <Line dataKey="bedsAvailable" name="Beds free" stroke="#16a34a" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Audit trail">
          {d.audit.length === 0 && <p className="text-slate-500">No decisions recorded yet.</p>}
          {[...d.audit].reverse().map((e) => (
            <div key={e.id} className="p-2 rounded bg-white border">
              <span className="font-mono">{hhmm(e.at)}</span> · <b>{e.reviewerRole}</b> {e.decision}d “{e.alert.title}”
              {e.reason && <span className="text-slate-600"> — {e.reason}</span>}
            </div>
          ))}
        </Panel>
      </section>
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded border p-3">
      <div className="text-slate-500">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="font-semibold text-base">{title}</h2>
      {children}
    </section>
  )
}

function AlertCard({ a, onReview }: { a: Alert; onReview: (a: Alert, d: Decision) => void }) {
  return (
    <article className={`p-3 rounded border-l-4 ${SEVERITY[a.severity]}`}>
      <div className="flex justify-between">
        <b>{a.title}</b>
        <span className="uppercase text-xs font-bold">{a.severity}{a.status === 'acknowledged' && ' · ack'}</span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-2 my-1 font-mono text-xs">
        {Object.entries(a.evidence).map(([k, v]) => (
          <Fragment key={k}><dt className="text-slate-500">{k}</dt><dd>{String(v)}</dd></Fragment>
        ))}
      </dl>
      <p>→ {a.suggestion}</p>
      <p className="text-xs text-slate-500 mt-1">{a.rule} · {a.ruleVersion} · raised {hhmm(a.createdAt)} · {a.uncertainty}</p>
      <div className="flex gap-1 mt-2">
        {(['acknowledge', 'complete', 'dismiss', 'override'] as const)
          .filter((x) => !(x === 'acknowledge' && a.status === 'acknowledged'))
          .map((x) => (
            <button key={x} onClick={() => onReview(a, x)} className="px-2 py-1 rounded border bg-white hover:bg-slate-100 capitalize">{x}</button>
          ))}
      </div>
    </article>
  )
}
