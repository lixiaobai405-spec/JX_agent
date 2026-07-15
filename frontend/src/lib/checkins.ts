import type { CheckinValue, Indicator, QualitativeCheckinStatus } from '@/types'

export type IndicatorCheckinKind = CheckinValue['value_type']

export const QUALITATIVE_STATUS_LABELS: Record<QualitativeCheckinStatus, string> = {
  not_started: '未开始',
  in_progress: '进行中',
  completed: '已完成',
  exceeded: '超预期完成',
}

const QUALITATIVE_STATUSES = new Set<QualitativeCheckinStatus>(
  Object.keys(QUALITATIVE_STATUS_LABELS) as QualitativeCheckinStatus[],
)

export function getIndicatorCheckinKind(
  indicator: Pick<Indicator, 'indicator_type' | 'redline' | 'score_method'>,
): IndicatorCheckinKind {
  if (indicator.redline || indicator.indicator_type === 'redline') return 'redline'
  if (indicator.indicator_type === 'qualitative' || indicator.score_method === 'manual') {
    return 'qualitative'
  }
  return 'quantitative'
}

export function isCheckinInputValid(
  indicator: Pick<Indicator, 'indicator_type' | 'redline' | 'score_method'>,
  input: string,
): boolean {
  const kind = getIndicatorCheckinKind(indicator)
  if (kind === 'qualitative') {
    return QUALITATIVE_STATUSES.has(input as QualitativeCheckinStatus)
  }
  if (!input.trim()) return false
  if (kind === 'redline') return /^\d+$/.test(input)
  return Number.isFinite(Number(input))
}

export function buildCheckinValue(
  indicator: Pick<Indicator, 'indicator_type' | 'redline' | 'score_method'>,
  input: string,
): CheckinValue {
  const kind = getIndicatorCheckinKind(indicator)
  if (!isCheckinInputValid(indicator, input)) {
    throw new Error(kind === 'redline' ? '请输入非负整数次数' : '请输入有效完成值')
  }
  if (kind === 'qualitative') {
    return { value_type: 'qualitative', value: input as QualitativeCheckinStatus }
  }
  return { value_type: kind, value: Number(input) }
}

export function formatCheckinValue(value: unknown, unit?: string | null): string {
  if (!value || typeof value !== 'object') return '—'
  const checkin = value as { value_type?: unknown; value?: unknown }
  if (checkin.value_type === 'qualitative') {
    return QUALITATIVE_STATUS_LABELS[checkin.value as QualitativeCheckinStatus] ?? '—'
  }
  if (typeof checkin.value !== 'number' || !Number.isFinite(checkin.value)) return '—'
  return `${checkin.value}${unit ?? ''}`
}
