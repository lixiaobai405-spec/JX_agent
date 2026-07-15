import assert from 'node:assert/strict'

import {
  toDateInputValue,
  toPeriodEndIso,
  toPeriodStartIso,
} from '../src/lib/periodDates.ts'

const dateInput = '2026-07-15'
const start = toPeriodStartIso(dateInput)
const end = toPeriodEndIso(dateInput)

assert.equal(toDateInputValue(start), dateInput)
assert.equal(toDateInputValue(end), dateInput)
assert.ok(new Date(start).getTime() < new Date(end).getTime())
assert.equal(toDateInputValue('not-a-date'), '')
assert.throws(() => toPeriodStartIso('2026-02-30'), RangeError)

console.log('period date tests passed')
