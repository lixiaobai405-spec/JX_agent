import client from './client'
import type { SelfAssessment, EvaluationTask, Evaluation, FinalResult } from '@/types'

export const checkApi = {
  createSelfAssessment: (goal_id: string, items: Record<string, { score: number; comment: string }>) =>
    client.post<SelfAssessment>('/check/self-assessments', { goal_id, items }).then((r) => r.data),

  getSelfAssessment: (goal_id: string) =>
    client.get<SelfAssessment>(`/check/self-assessments/goal/${goal_id}`).then((r) => r.data),

  updateSelfAssessment: (id: string, items: Record<string, { score: number; comment: string }>) =>
    client.put<SelfAssessment>(`/check/self-assessments/${id}`, { items }).then((r) => r.data),

  submitSelfAssessment: (id: string) =>
    client.post<SelfAssessment>(`/check/self-assessments/${id}/submit`).then((r) => r.data),

  generateEvaluationTasks: (goal_id: string) =>
    client.post<EvaluationTask[]>('/check/evaluation-tasks/generate', { goal_id }).then((r) => r.data),

  listEvaluationTasks: (status?: string) =>
    client.get<EvaluationTask[]>('/check/evaluation-tasks', { params: status ? { status } : undefined }).then((r) => r.data),

  pendingEvaluationTasks: () =>
    client.get<EvaluationTask[]>('/check/evaluation-tasks/my-pending').then((r) => r.data),

  getGoalEvaluations: (goal_id: string) =>
    client.get<Evaluation[]>(`/check/evaluations/goal/${goal_id}`).then((r) => r.data),

  submitEvaluation: (data: { task_id: string; indicator_id: string; score: number; comment?: string }) =>
    client.post<Evaluation>('/check/evaluations', data).then((r) => r.data),

  generateFinalResult: (goal_id: string) =>
    client.post<FinalResult>('/check/final-results/generate', { goal_id }).then((r) => r.data),

  getFinalResult: (goal_id: string) =>
    client.get<FinalResult>(`/check/final-results/goal/${goal_id}`).then((r) => r.data),

  confirmFinalResult: (id: string) =>
    client.put<FinalResult>(`/check/final-results/${id}/confirm`).then((r) => r.data),

  adjustFinalResult: (id: string, final_grade: string, adjustment_reason: string) =>
    client.put<FinalResult>(`/check/final-results/${id}/adjust`, { final_grade, adjustment_reason }).then((r) => r.data),
}
