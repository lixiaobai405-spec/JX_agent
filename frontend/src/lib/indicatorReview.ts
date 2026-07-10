import type { DiagnosticReport, Indicator, TrafficLight } from '@/types'

type DiagnosticIndicatorResult = {
  name?: unknown
  actual?: unknown
  actual_value?: unknown
  target_display?: unknown
  status?: unknown
}

export type IndicatorReviewContext = {
  targetDisplay: string | null
  actualDisplay: string | null
  status: TrafficLight | null
  scoringRule: string | null
  targetLogic: string | null
  indicatorType: string | null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function toDisplay(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)))
  if (typeof value === 'string') return value
  return String(value)
}

function formatTarget(value: number | null | undefined, unit?: string | null): string | null {
  const display = toDisplay(value)
  if (!display) return null
  return unit ? `${display}${unit}` : display
}

function normalizeStatus(value: unknown): TrafficLight | null {
  return value === 'green' || value === 'yellow' || value === 'red' ? value : null
}

function findDiagnosticIndicatorResult(
  indicator: Indicator,
  diagnostic: DiagnosticReport | null | undefined,
): DiagnosticIndicatorResult | null {
  const analysis = diagnostic?.indicators_analysis
  if (!isRecord(analysis) || !Array.isArray(analysis.indicator_results)) return null

  return (
    analysis.indicator_results.find(
      (item): item is DiagnosticIndicatorResult =>
        isRecord(item) && item.name === indicator.name,
    ) ?? null
  )
}

export function getIndicatorReviewContext(
  indicator: Indicator,
  diagnostic: DiagnosticReport | null | undefined,
): IndicatorReviewContext {
  const result = findDiagnosticIndicatorResult(indicator, diagnostic)
  return {
    targetDisplay:
      indicator.target_display ??
      toDisplay(result?.target_display) ??
      formatTarget(indicator.target_value, indicator.unit),
    actualDisplay: toDisplay(result?.actual) ?? toDisplay(result?.actual_value),
    status: normalizeStatus(result?.status),
    scoringRule: indicator.scoring_rule ?? null,
    targetLogic: indicator.target_logic ?? null,
    indicatorType: indicator.indicator_type ?? null,
  }
}
