import assert from 'node:assert/strict'

import {
  buildCheckinValue,
  formatCheckinValue,
  getIndicatorCheckinKind,
  isCheckinInputValid,
} from '../src/lib/checkins.ts'
import type { Indicator } from '../src/types/index.ts'

const quantitative = {
  indicator_type: 'positive',
  direction: 'positive',
  redline: false,
} as Indicator
const qualitative = {
  indicator_type: 'qualitative',
  direction: 'positive',
  redline: false,
} as Indicator
const redline = {
  indicator_type: 'redline',
  direction: 'negative',
  redline: true,
} as Indicator

assert.equal(getIndicatorCheckinKind(quantitative), 'quantitative')
assert.equal(getIndicatorCheckinKind(qualitative), 'qualitative')
assert.equal(getIndicatorCheckinKind(redline), 'redline')

assert.deepEqual(buildCheckinValue(quantitative, '12.5'), {
  value_type: 'quantitative',
  value: 12.5,
})
assert.deepEqual(buildCheckinValue(qualitative, 'completed'), {
  value_type: 'qualitative',
  value: 'completed',
})
assert.deepEqual(buildCheckinValue(redline, '2'), {
  value_type: 'redline',
  value: 2,
})

assert.equal(isCheckinInputValid(quantitative, ''), false)
assert.equal(isCheckinInputValid(qualitative, 'unknown'), false)
assert.equal(isCheckinInputValid(redline, '-1'), false)
assert.equal(isCheckinInputValid(redline, '1.5'), false)
assert.equal(isCheckinInputValid(redline, '0'), true)

assert.equal(formatCheckinValue({ value_type: 'qualitative', value: 'in_progress' }), '进行中')
assert.equal(formatCheckinValue({ value_type: 'redline', value: 2 }, '起'), '2起')
assert.equal(formatCheckinValue({ value: 3 }, '次'), '3次')

console.log('check-in tests passed')
