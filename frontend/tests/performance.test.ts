import assert from 'node:assert/strict'

import {
  formatAchievementRate,
  toAchievementProgress,
  WEIGHTED_ACHIEVEMENT_EXPLANATION,
} from '../src/lib/performance.ts'

assert.equal(formatAchievementRate(95.7), '96%')
assert.equal(formatAchievementRate(null), '—')
assert.equal(formatAchievementRate(Number.NaN), '—')

assert.equal(toAchievementProgress(95.7), 95.7)
assert.equal(toAchievementProgress(150), 100)
assert.equal(toAchievementProgress(-1), 0)
assert.equal(toAchievementProgress(Number.NaN), 0)

assert.equal(WEIGHTED_ACHIEVEMENT_EXPLANATION.includes('红线'), true)
assert.equal(WEIGHTED_ACHIEVEMENT_EXPLANATION.includes('不参与加权'), true)

console.log('performance tests passed')
