export type MarkdownEditorMode = 'preview' | 'edit'

export const DEFAULT_MARKDOWN_EDITOR_MODE: MarkdownEditorMode = 'preview'

export function toggleMarkdownEditorMode(mode: MarkdownEditorMode): MarkdownEditorMode {
  return mode === 'preview' ? 'edit' : 'preview'
}

export function normalizeEditableMarkdown(markdown: string): string {
  let convertedListNumber = 0
  let convertingBulletList = false

  return markdown
    .replaceAll('**', '')
    .split('\n')
    .map((line) => {
      const bulletMatch = line.match(/^(\s*)[-+*]\s+(.+)$/)
      if (bulletMatch) {
        if (!convertingBulletList) convertedListNumber = 0
        convertingBulletList = true
        convertedListNumber += 1
        return `${bulletMatch[1]}${convertedListNumber}. ${bulletMatch[2]}`
      }

      if (line.trim() && !/^\s+/.test(line)) convertingBulletList = false
      return line
    })
    .join('\n')
}

export function formatMarkdownPreview(markdown: string): string {
  return normalizeEditableMarkdown(markdown)
    .split('\n')
    .map((line) => {
      const labelMatch = line.match(/^(\s*(?:\d+[.)]\s+)?)([^：:\n]{1,24})([：:])(\s*.*)$/)
      if (!labelMatch) return line

      const [, prefix, rawLabel, colon, remainder] = labelMatch
      const label = rawLabel.trim()
      if (!label || /[，,。；;！？!?]/.test(label) || /^https?$/i.test(label)) return line

      return `${prefix}**${label}${colon}**${remainder}`
    })
    .join('\n')
}
