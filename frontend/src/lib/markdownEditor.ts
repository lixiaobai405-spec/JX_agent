export type MarkdownEditorMode = 'preview' | 'edit'

export const DEFAULT_MARKDOWN_EDITOR_MODE: MarkdownEditorMode = 'preview'

export function toggleMarkdownEditorMode(mode: MarkdownEditorMode): MarkdownEditorMode {
  return mode === 'preview' ? 'edit' : 'preview'
}
