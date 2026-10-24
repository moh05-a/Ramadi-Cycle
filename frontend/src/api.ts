// Mirrors backend/state.go JSON.
export type Patient = {
  id: string; alias: string; ageBand: string; area: string; status: 'waiting' | 'in_bed'
  arrivedAt: string; lastReassessedAt: string; pendingTest?: string
}
export type Task = { id: string; caseId: string; type: string; owner: string; dueAt: string; status: 'open' | 'done' }
export type Alert = {
  id: string; rule: string; ruleVersion: string; severity: 'high' | 'medium' | 'low'; title: string
  evidence: Record<string, unknown>; uncertainty: string; suggestion: string
  caseId?: string; taskId?: string; createdAt: string; status: string
}
export type AuditEvent = { id: number; at: string; alertId: string; reviewerRole: string; decision: string; reason: string; alert: Alert }
export type Snapshot = { at: string; waiting: number; bedsAvailable: number; pendingTasks: number; labTurnaroundMin: number }
export type Dashboard = {
  simulated: boolean; now: string
  metrics: { activePatients: number; waiting: number; longestWaitMin: number; pendingTasks: number; bedsAvailable: number; bedsTotal: number; labTurnaroundMin: number }
  patients: Patient[]; alerts: Alert[]; tasks: Task[]; history: Snapshot[]; audit: AuditEvent[]
}
export type Decision = 'acknowledge' | 'complete' | 'dismiss' | 'override'

async function call(path: string, init?: RequestInit): Promise<Dashboard> {
  const res = await fetch(path, init)
  const body = await res.json()
  if (!res.ok) throw new Error(body.error ?? res.statusText)
  return body
}

export const getDashboard = () => call('/api/dashboard')
export const runScenario = (id: string) => call(`/api/scenarios/${id}/run`, { method: 'POST' })
export const reviewAlert = (id: string, decision: Decision, reason: string, reviewerRole: string) =>
  call(`/api/alerts/${encodeURIComponent(id)}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason, reviewerRole }),
  })
