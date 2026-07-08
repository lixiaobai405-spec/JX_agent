import assert from 'node:assert/strict'

import { normalizeAgreementTerm } from '../src/lib/copy.ts'

const oldTerm = '\u5408\u540c'
const newTerm = '\u5408\u7ea6'

assert.equal(normalizeAgreementTerm(`绩效${oldTerm}已生效`), `绩效${newTerm}已生效`)
assert.equal(normalizeAgreementTerm(`生成${oldTerm} / 确认${oldTerm}`), `生成${newTerm} / 确认${newTerm}`)
assert.equal(normalizeAgreementTerm(`无${oldTerm}${oldTerm}`), `无${newTerm}${newTerm}`)

console.log('copy tests passed')
