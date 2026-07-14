export const WEIGHTED_ACHIEVEMENT_EXPLANATION =
  '加权达成率 = Σ(单项达成率 × 权重) / 有效权重总和；红线指标不参与加权；单项达成率最高按 150% 计。'

export function formatAchievementRate(value: number | null | undefined): string {
  return value != null && Number.isFinite(value) ? `${Math.round(value)}%` : '—'
}

export function toAchievementProgress(value: number | null | undefined): number {
  if (value == null || !Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, value))
}
