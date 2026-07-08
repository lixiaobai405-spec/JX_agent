export type CoachingStatus = 'pending' | 'accepted' | 'rejected' | 'completed'

const coachingStatusLabels: Record<CoachingStatus, string> = {
  pending: '待处理',
  accepted: '已接受',
  rejected: '已拒绝',
  completed: '已完成',
}

export function getDiagnosticToggleLabel(isOpen: boolean) {
  return isOpen ? '收起诊断结果' : '展开诊断结果'
}

export function getCoachingStatusLabel(status: CoachingStatus) {
  return coachingStatusLabels[status]
}

export function getCoachingResponseText(notes: string | null | undefined) {
  const text = notes?.trim()
  return text || '上级暂未填写回复内容'
}

export function buildCoachingStatusUpdatePayload(status: string, notes?: string) {
  return {
    status,
    response: notes?.trim() || undefined,
  }
}

export function filterCoachingRequestsByGoal<T extends { goal_id: string | null | undefined }>(
  requests: T[] | null | undefined,
  goalId: string | null | undefined,
): T[] {
  if (!requests || !goalId) return []
  return requests.filter((request) => request.goal_id === goalId)
}
