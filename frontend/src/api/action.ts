import client from './client'
import type { ReviewReport, DevelopmentPlan, InheritanceSuggestion } from '@/types'

export const actionApi = {
  generateReviewReport: (final_result_id: string) =>
    client.post<ReviewReport>('/action/review-reports/generate', { final_result_id }).then((r) => r.data),

  getReviewReport: (id: string) =>
    client.get<ReviewReport>(`/action/review-reports/${id}`).then((r) => r.data),

  getReviewReportByUser: (user_id: string, period_id: string) =>
    client.get<ReviewReport>(`/action/review-reports/user/${user_id}/period/${period_id}`).then((r) => r.data),

  submitReviewFeedback: (id: string, user_feedback: string) =>
    client.put<ReviewReport>(`/action/review-reports/${id}/feedback`, { user_feedback }).then((r) => r.data),

  createDevelopmentPlan: (data: {
    review_report_id: string
    goals: Record<string, unknown>
    actions: Record<string, unknown>
    required_resources?: Record<string, unknown>
    timeline?: Record<string, unknown>
  }) => client.post<DevelopmentPlan>('/action/development-plans', data).then((r) => r.data),

  getDevelopmentPlan: (id: string) =>
    client.get<DevelopmentPlan>(`/action/development-plans/${id}`).then((r) => r.data),

  updateDevelopmentPlan: (id: string, data: {
    goals?: Record<string, unknown>
    actions?: Record<string, unknown>
    required_resources?: Record<string, unknown>
    timeline?: Record<string, unknown>
  }) => client.put<DevelopmentPlan>(`/action/development-plans/${id}`, data).then((r) => r.data),

  myPlans: () =>
    client.get<DevelopmentPlan[]>('/action/development-plans/my-plans').then((r) => r.data),

  teamPlans: () =>
    client.get<DevelopmentPlan[]>('/action/development-plans/my-team').then((r) => r.data),

  aiReviewPlan: (id: string, feedback?: string) =>
    client.post<DevelopmentPlan>(`/action/development-plans/${id}/ai-review`, { feedback }).then((r) => r.data),

  submitPlan: (id: string) =>
    client.post<DevelopmentPlan>(`/action/development-plans/${id}/submit`).then((r) => r.data),

  approvePlan: (id: string, approved: boolean, comment?: string) =>
    client.post<DevelopmentPlan>(`/action/development-plans/${id}/approve`, { approved, comment }).then((r) => r.data),

  generateInheritanceSuggestions: (user_id: string, from_period_id: string, to_period_id: string) =>
    client.post<InheritanceSuggestion>('/action/inheritance-suggestions/generate', {
      user_id, from_period_id, to_period_id,
    }).then((r) => r.data),

  getInheritanceSuggestions: (user_id: string, period_id: string) =>
    client.get<InheritanceSuggestion[]>(`/action/inheritance-suggestions/user/${user_id}/period/${period_id}`).then((r) => r.data),

  acceptSuggestion: (id: string) =>
    client.post<InheritanceSuggestion>(`/action/inheritance-suggestions/${id}/accept`).then((r) => r.data),

  rejectSuggestion: (id: string, rejected_reason: string) =>
    client.post<InheritanceSuggestion>(`/action/inheritance-suggestions/${id}/reject`, { rejected_reason }).then((r) => r.data),
}
