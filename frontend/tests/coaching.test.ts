import assert from 'node:assert/strict'

import {
  buildCoachingStatusUpdatePayload,
  filterCoachingRequestsByGoal,
  getCoachingResponseText,
  getCoachingStatusLabel,
  getDiagnosticToggleLabel,
} from '../src/lib/coaching.ts'

assert.equal(getDiagnosticToggleLabel(true), '收起诊断结果')
assert.equal(getDiagnosticToggleLabel(false), '展开诊断结果')

assert.equal(getCoachingStatusLabel('pending'), '待处理')
assert.equal(getCoachingStatusLabel('accepted'), '已接受')
assert.equal(getCoachingStatusLabel('completed'), '已完成')
assert.equal(getCoachingStatusLabel('rejected'), '已拒绝')

assert.equal(getCoachingResponseText(' 请周五下午沟通 '), '请周五下午沟通')
assert.equal(getCoachingResponseText(null), '上级暂未填写回复内容')

assert.deepEqual(buildCoachingStatusUpdatePayload('accepted', ' 可以，本周五沟通 '), {
  status: 'accepted',
  response: '可以，本周五沟通',
})

assert.deepEqual(buildCoachingStatusUpdatePayload('rejected'), {
  status: 'rejected',
  response: undefined,
})

const requests = [
  { id: 'request-1', goal_id: 'goal-1' },
  { id: 'request-2', goal_id: 'goal-2' },
  { id: 'request-3', goal_id: null },
]

assert.deepEqual(filterCoachingRequestsByGoal(undefined, 'goal-1'), [])
assert.deepEqual(filterCoachingRequestsByGoal(requests, undefined), [])
assert.deepEqual(filterCoachingRequestsByGoal(requests, 'goal-1'), [requests[0]])
