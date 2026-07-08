import assert from 'node:assert/strict'

import {
  clampScore,
  parseScoreInput,
  isScoreInRange,
  hasInvalidScores,
} from '../src/lib/scores.ts'

assert.equal(clampScore(-1), 0)
assert.equal(clampScore(0), 0)
assert.equal(clampScore(55.5), 55.5)
assert.equal(clampScore(100), 100)
assert.equal(clampScore(101), 100)

assert.equal(parseScoreInput(''), '')
assert.equal(parseScoreInput('abc'), '')
assert.equal(parseScoreInput('-8'), '0')
assert.equal(parseScoreInput('66'), '66')
assert.equal(parseScoreInput('6666'), '100')

assert.equal(isScoreInRange(''), false)
assert.equal(isScoreInRange('0'), true)
assert.equal(isScoreInRange('100'), true)
assert.equal(isScoreInRange('-1'), false)
assert.equal(isScoreInRange('101'), false)
assert.equal(isScoreInRange('abc'), false)

assert.equal(hasInvalidScores({ a: { score: '90' }, b: { score: '100' } }), false)
assert.equal(hasInvalidScores({ a: { score: '90' }, b: { score: '101' } }), true)
assert.equal(hasInvalidScores({ a: { score: '' } }), true)

console.log('scores tests passed')
