const TIMEZONE_SUFFIX = /(Z|[+-]\d{2}:?\d{2})$/i

function parseBackendDateTime(value: string): Date | null {
  const trimmed = value.trim()
  if (!trimmed) return null

  const withSeparator = trimmed.includes('T') ? trimmed : trimmed.replace(' ', 'T')
  const withMilliseconds = withSeparator.replace(/(\.\d{3})\d+/, '$1')
  const withTimezone = TIMEZONE_SUFFIX.test(withMilliseconds)
    ? withMilliseconds
    : `${withMilliseconds}Z`

  const date = new Date(withTimezone)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateTimeLocal(value?: string | null, timeZone?: string): string | null {
  if (!value) return null

  const date = parseBackendDateTime(value)
  if (!date) return value

  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  })

  const parts = Object.fromEntries(
    formatter.formatToParts(date).map((part) => [part.type, part.value]),
  )

  const { year, month, day, hour, minute } = parts
  if (!year || !month || !day || !hour || !minute) return value

  return `${year}-${month}-${day} ${hour}:${minute}`
}
