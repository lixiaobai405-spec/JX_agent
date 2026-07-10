import assert from 'node:assert/strict'

import { normalizeDiagnosticMarkdown } from '../src/lib/diagnosticMarkdown.ts'

const raw = {
  content:
    '### 根因分析\\n\\n1. **销售回款率**\\n- 客户付款审批延迟。\\n\\n### 改进建议\\n- 每周三跟进应收账款。',
}

const markdown = normalizeDiagnosticMarkdown(raw)

assert.equal(markdown.includes('{"content"'), false)
assert.equal(markdown.includes('\\n'), false)
assert.equal(markdown.includes('### 根因分析'), true)
assert.equal(markdown.includes('**销售回款率**'), true)
assert.equal(markdown.includes('- 每周三跟进应收账款。'), true)

assert.equal(
  normalizeDiagnosticMarkdown(JSON.stringify(raw)),
  markdown,
)

console.log('diagnostic markdown tests passed')

