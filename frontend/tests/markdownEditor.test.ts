import assert from 'node:assert/strict'

import {
  DEFAULT_MARKDOWN_EDITOR_MODE,
  toggleMarkdownEditorMode,
} from '../src/lib/markdownEditor.ts'

assert.equal(DEFAULT_MARKDOWN_EDITOR_MODE, 'preview')
assert.equal(toggleMarkdownEditorMode('preview'), 'edit')
assert.equal(toggleMarkdownEditorMode('edit'), 'preview')

console.log('markdown editor tests passed')
