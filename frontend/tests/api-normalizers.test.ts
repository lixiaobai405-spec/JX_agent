import assert from 'node:assert/strict'
import { normalizeList } from '../src/lib/api-normalizers.ts'

assert.deepEqual(normalizeList(undefined), [])
assert.deepEqual(normalizeList(null), [])
assert.deepEqual(normalizeList({ items: [] }), [])
assert.deepEqual(normalizeList([]), [])

const items = [{ id: 'period-1' }]
assert.equal(normalizeList(items), items)

console.log('api-normalizers tests passed')
