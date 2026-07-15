import assert from 'node:assert/strict'

import { buildContractTargets } from '../src/lib/planContract.ts'

const payload = buildContractTargets(
  [
    { id: 17, target: 100, is_redline: false },
    { id: 'stable-id', target: 2, is_redline: false },
    { id: 99, target: 0, is_redline: true },
  ],
  {
    '17': '120.5',
    'stable-id': '3',
    '99': '1',
  },
)

assert.deepEqual(payload, {
  targets: [
    { indicator_id: 17, target: 120.5 },
    { indicator_id: 'stable-id', target: 3 },
  ],
})

assert.throws(
  () => buildContractTargets([{ id: 1, target: 10 }], { '1': '' }),
  /有效目标值/,
)

console.log('plan contract tests passed')
