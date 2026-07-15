import assert from 'node:assert/strict'

import {
  C_GRADE_RULES,
  C_GRADE_RULE_TEXT,
  getDiagnosticIndicatorStatus,
  getPlanText,
  getSuggestionSummary,
} from '../src/lib/pdcaFeedback.ts'

assert.deepEqual(
  C_GRADE_RULES.map(({ grade, range }) => ({ grade, range })),
  [
    { grade: 'S', range: '[90, 100]' },
    { grade: 'A', range: '[80, 90)' },
    { grade: 'B', range: '[70, 80)' },
    { grade: 'C', range: '[0, 70)' },
  ],
)
assert.equal(C_GRADE_RULE_TEXT.includes('A 为 [80, 90)'), true)

const diagnostic = {
  indicators_analysis: {
    indicator_results: [
      { indicator_id: 'indicator-1', name: '已改名的铺货率', status: 'green' },
      { indicator_id: 'indicator-2', status: 'yellow' },
      { indicator_id: 'indicator-3', indicator_name: '事故次数', status: 'red' },
      { name: '仅同名指标', status: 'green' },
    ],
  },
}

assert.equal(
  getDiagnosticIndicatorStatus(diagnostic as never, { id: 'indicator-1', name: '铺货率' }),
  'green',
)
assert.equal(
  getDiagnosticIndicatorStatus(diagnostic as never, { id: 'indicator-2', name: '陈列达标率' }),
  'yellow',
)
assert.equal(
  getDiagnosticIndicatorStatus(diagnostic as never, { id: 'indicator-3', name: '事故次数' }),
  'red',
)
assert.equal(
  getDiagnosticIndicatorStatus(diagnostic as never, { id: 'indicator-4', name: '仅同名指标' }),
  'green',
)
assert.equal(
  getDiagnosticIndicatorStatus(
    { indicators_analysis: { indicator_results: [{ indicator_id: 'other-id', name: '同名不同指标', status: 'red' }] } } as never,
    { id: 'indicator-5', name: '同名不同指标' },
  ),
  null,
)

assert.equal(getPlanText({ text: '提升项目管理能力' }), '提升项目管理能力')
assert.equal(getPlanText({ value: 'ignored' }), '')
assert.equal(getPlanText('直接文本'), '直接文本')

assert.equal(
  getSuggestionSummary({
    summary: '延续本期 IDP 改进项',
    recommendations: [],
  }),
  '延续本期 IDP 改进项',
)
assert.equal(
  getSuggestionSummary({
    recommendations: [
      { name: '改进完成度', target_display: '100%', reason: '承接 IDP' },
    ],
  }),
  '改进完成度 · 100% · 承接 IDP',
)

console.log('pdca feedback tests passed')
