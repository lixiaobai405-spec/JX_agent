const PREFERRED_TEXT_KEYS = [
  'content',
  'feedback',
  'text',
  'message',
  'root_cause_analysis',
  'improvement_suggestions',
]

function extractText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (Array.isArray(value)) {
    return value.map((item) => extractText(item)).filter(Boolean).join('\n')
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    for (const key of PREFERRED_TEXT_KEYS) {
      const nested = record[key]
      if (nested) return extractText(nested)
    }
    return JSON.stringify(value)
  }
  return String(value)
}

function unwrapJsonText(value: string): string {
  let current = value.trim()
  for (let i = 0; i < 3; i += 1) {
    if (!current) return ''
    try {
      const parsed = JSON.parse(current) as unknown
      const next = extractText(parsed).trim()
      if (next === current) return current
      current = next
    } catch {
      return current
    }
  }
  return current
}

export function normalizeDiagnosticMarkdown(value: unknown): string {
  const text = unwrapJsonText(extractText(value))
    .replace(/\\r\\n/g, '\n')
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\n')
    .replace(/\\t/g, ' ')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')

  return text
    .split('\n')
    .map((line) => line.trim())
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

