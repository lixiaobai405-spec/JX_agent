import type { DiagnosticReport, Indicator } from '@/types'

type TrafficLightStatus = 'green' | 'yellow' | 'red'

const TRAFFIC_LIGHT_VALUES = new Set(['green', 'yellow', 'red'])

export const C_GRADE_RULES = [
  { grade: 'S', range: '[90, 100]', label: '优秀' },
  { grade: 'A', range: '[80, 90)', label: '良好' },
  { grade: 'B', range: '[70, 80)', label: '合格' },
  { grade: 'C', range: '[0, 70)', label: '待改进' },
]

export const C_GRADE_RULE_TEXT = '定级规则：S 为 [90, 100]，A 为 [80, 90)，B 为 [70, 80)，C 为 [0, 70)；红线触发按次数扣分。'

export function getPlanText(value: unknown): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object' && 'text' in value) {
    const text = (value as { text?: unknown }).text
    return typeof text === 'string' ? text : ''
  }
  return ''
}

export function getDiagnosticIndicatorStatus(
  diagnostic: DiagnosticReport | null | undefined,
  indicator: Pick<Indicator, 'id' | 'name'>,
): TrafficLightStatus | null {
  const results = diagnostic?.indicators_analysis?.indicator_results
  if (!Array.isArray(results)) return null

  const match = results.find((item) => {
    if (!item || typeof item !== 'object') return false
    const result = item as Record<string, unknown>
    if (result.indicator_id !== undefined && result.indicator_id !== null && result.indicator_id !== '') {
      return result.indicator_id === indicator.id
    }
    return result.name === indicator.name || result.indicator_name === indicator.name
  })

  if (!match || typeof match !== 'object') return null
  const status = (match as Record<string, unknown>).status
  return typeof status === 'string' && TRAFFIC_LIGHT_VALUES.has(status)
    ? status as TrafficLightStatus
    : null
}

export function getSuggestionSummary(suggestions: unknown): string {
  if (typeof suggestions === 'string') return suggestions
  if (!suggestions || typeof suggestions !== 'object') return '暂无可展示的继承建议'

  const data = suggestions as Record<string, unknown>
  if (typeof data.summary === 'string' && data.summary.trim()) return data.summary

  if (Array.isArray(data.recommendations) && data.recommendations.length > 0) {
    return data.recommendations
      .map((item) => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return ''
        const record = item as Record<string, unknown>
        return [record.name, record.target_display, record.reason]
          .filter((part): part is string => typeof part === 'string' && part.trim().length > 0)
          .join(' · ')
      })
      .filter(Boolean)
      .join('；')
  }

  return 'AI 已生成继承建议，请结合本期 IDP 继续完善下周期目标。'
}
