import assert from 'node:assert/strict'

import {
  DEFAULT_MARKDOWN_EDITOR_MODE,
  formatMarkdownPreview,
  normalizeEditableMarkdown,
  toggleMarkdownEditorMode,
} from '../src/lib/markdownEditor.ts'

assert.equal(DEFAULT_MARKDOWN_EDITOR_MODE, 'preview')
assert.equal(toggleMarkdownEditorMode('preview'), 'edit')
assert.equal(toggleMarkdownEditorMode('edit'), 'preview')

const aiMarkdown = [
  '- **第1周**：与上级沟通，确定本周期重点任务。',
  '- **第1月**: 完成方案草案并向团队分享。',
  '',
  '**时间节点**：首个里程碑安排在2-3个月内。',
].join('\n')

const editableMarkdown = [
  '1. 第1周：与上级沟通，确定本周期重点任务。',
  '2. 第1月: 完成方案草案并向团队分享。',
  '',
  '时间节点：首个里程碑安排在2-3个月内。',
].join('\n')

assert.equal(normalizeEditableMarkdown(aiMarkdown), editableMarkdown)
assert.equal(normalizeEditableMarkdown(editableMarkdown), editableMarkdown)
assert.equal(
  formatMarkdownPreview(editableMarkdown),
  [
    '1. **第1周：**与上级沟通，确定本周期重点任务。',
    '2. **第1月:** 完成方案草案并向团队分享。',
    '',
    '**时间节点：**首个里程碑安排在2-3个月内。',
  ].join('\n'),
)

console.log('markdown editor tests passed')
