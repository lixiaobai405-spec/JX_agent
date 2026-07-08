import assert from 'node:assert/strict'

import { formatDateTimeLocal } from '../src/lib/datetime.ts'

assert.equal(
  formatDateTimeLocal('2026-07-06T12:27:40.327136', 'Asia/Shanghai'),
  '2026-07-06 20:27',
)

assert.equal(
  formatDateTimeLocal('2026-07-06 12:27:40.327136', 'Asia/Shanghai'),
  '2026-07-06 20:27',
)

assert.equal(
  formatDateTimeLocal('2026-07-06T12:27:40.327136Z', 'Asia/Shanghai'),
  '2026-07-06 20:27',
)

assert.equal(formatDateTimeLocal(null, 'Asia/Shanghai'), null)
