import assert from 'node:assert/strict'

import { getIndicatorReviewContext } from '../src/lib/indicatorReview.ts'
import type { DiagnosticReport, Indicator } from '../src/types/index.ts'

const indicator = {
  id: 'indicator-1',
  name: '区域净销售额',
  target_value: 800,
  target_display: '800万元',
  scoring_rule: '(实际/目标)*100%',
  target_logic: '自上而下（年度目标分解）',
  unit: '万元',
} as Indicator

const diagnostic = {
  indicators_analysis: {
    indicator_results: [
      {
        indicator_id: 'indicator-1',
        name: '诊断侧旧名称',
        actual: '760',
        actual_value: 760,
        target_display: '800万元',
        status: 'yellow',
      },
    ],
  },
} as unknown as DiagnosticReport

const context = getIndicatorReviewContext(indicator, diagnostic)

assert.equal(context.targetDisplay, '800万元')
assert.equal(context.actualDisplay, '760')
assert.equal(context.status, 'yellow')
assert.equal(context.scoringRule, '(实际/目标)*100%')
assert.equal(context.targetLogic, '自上而下（年度目标分解）')

const sameNameOnlyContext = getIndicatorReviewContext(
  indicator,
  {
    indicators_analysis: {
      indicator_results: [{ indicator_id: 'other-id', name: indicator.name, actual: 999, status: 'red' }],
    },
  } as unknown as DiagnosticReport,
)

assert.equal(sameNameOnlyContext.actualDisplay, null)
assert.equal(sameNameOnlyContext.status, null)

const legacyNameContext = getIndicatorReviewContext(
  indicator,
  {
    indicators_analysis: {
      indicator_results: [{ name: indicator.name, actual: 760, status: 'green' }],
    },
  } as unknown as DiagnosticReport,
)

assert.equal(legacyNameContext.actualDisplay, '760')
assert.equal(legacyNameContext.status, 'green')

const fallbackContext = getIndicatorReviewContext(
  { name: '新品铺货率', target_value: 85, unit: '%' } as Indicator,
  null,
)

assert.equal(fallbackContext.targetDisplay, '85%')
assert.equal(fallbackContext.actualDisplay, null)
assert.equal(fallbackContext.status, null)

console.log('indicator review tests passed')
