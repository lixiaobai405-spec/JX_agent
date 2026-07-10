import assert from 'node:assert/strict'

import {
  C_GRADE_RULE_TEXT,
  getDiagnosticIndicatorStatus,
  getPlanText,
  getSuggestionSummary,
} from '../src/lib/pdcaFeedback.ts'

assert.equal(C_GRADE_RULE_TEXT.includes('S 90-100'), true)

const diagnostic = {
  indicators_analysis: {
    indicator_results: [
      { name: '铺货率', status: 'green' },
      { indicator_id: 'indicator-2', status: 'yellow' },
      { indicator_name: '事故次数', status: 'red' },
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
  getDiagnosticIndicatorStatus(diagnostic as never, { id: 'indicator-4', name: '未知指标' }),
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
