import client from './client'
import { normalizeList } from '@/lib/api-normalizers'
import { buildCoachingStatusUpdatePayload } from '@/lib/coaching'
import type { Period, Goal, Indicator, DiagnosticReport, DataCheckin, CoachingRequest } from '@/types'

export const periodsApi = {
  list: () => client.get<{ items: Period[] | null }>('/periods/').then((r) => normalizeList<Period>(r.data.items)),
  listByStatus: (status: string) => client.get<{ items: Period[] | null }>('/periods/', { params: { status } }).then((r) => normalizeList<Period>(r.data.items)),
  current: () => client.get<Period>('/periods/current').then((r) => r.data),
  create: (data: Partial<Period>) => client.post<Period>('/periods/', data).then((r) => r.data),
  updateStatus: (id: string, status: string) =>
    client.put<Period>(`/periods/${id}/status`, { status }).then((r) => r.data),
  completeDPhase: (id: string) =>
    client.post<Period>(`/periods/${id}/complete-d-phase`).then((r) => r.data),
}

export const planApi = {
  analyzeJob: (user_id: string, jd_text: string) =>
    client.post('/plan/job-analysis', { user_id, jd_text }).then((r) => r.data),

  getAnalysis: (id: string) => client.get(`/plan/job-analysis/${id}`).then((r) => r.data),

  generateContract: (data: {
    period_id: string
    user_id: string
    job_analysis_id: string
    feedback?: string
  }) => client.post('/plan/contracts/generate', data).then((r) => r.data),

  getContract: (id: string) => client.get(`/plan/contracts/${id}`).then((r) => r.data),

  confirmContract: (id: string, confirmed_by: string) =>
    client.post(`/plan/contracts/${id}/confirm`, { confirmed_by }).then((r) => r.data),

  getTemplates: (prototype_code?: string) =>
    client.get('/plan/templates', { params: { prototype_code } }).then((r) => r.data),
}

export const doApi = {
  currentGoal: (period_id: string, user_id?: string) =>
    client.get<Goal>('/do/goals/current', { params: { period_id, ...(user_id ? { user_id } : {}) } }).then((r) => r.data),

  indicators: (goal_id: string) =>
    client.get<Indicator[]>(`/do/goals/${goal_id}/indicators`).then((r) => r.data),

  submitCheckin: (data: { indicator_id: string; actual_value: number; progress_description?: string; issues?: string }) =>
    client.post<DataCheckin>('/do/checkins', data).then((r) => r.data),

  updateCheckin: (id: string, data: Partial<DataCheckin>) =>
    client.put<DataCheckin>(`/do/checkins/${id}`, data).then((r) => r.data),

  indicatorCheckins: (indicator_id: string) =>
    client.get<DataCheckin[]>(`/do/checkins/indicator/${indicator_id}`).then((r) => r.data),

  generateDiagnostic: (goal_id: string, feedback?: string) =>
    client.post<DiagnosticReport>('/do/diagnostic-reports/generate', { goal_id, feedback }).then((r) => r.data),

  latestDiagnostic: (goal_id: string) =>
    client.get<DiagnosticReport>(`/do/diagnostic-reports/goal/${goal_id}/latest`).then((r) => r.data),

  createCoachingRequest: (data: { diagnostic_report_id: string; request_reason?: string; urgency_level: string }) =>
    client.post<CoachingRequest>('/do/coaching-requests', data).then((r) => r.data),

  myCoachingRequests: () =>
    client.get<CoachingRequest[]>('/do/coaching-requests/my-requests').then((r) => r.data),

  teamCoachingRequests: () =>
    client.get<CoachingRequest[]>('/do/coaching-requests/my-team').then((r) => r.data),

  updateCoachingStatus: (id: string, status: string, notes?: string) =>
    client.put(`/do/coaching-requests/${id}/status`, buildCoachingStatusUpdatePayload(status, notes)).then((r) => r.data),
}
