function parseDateInput(value: string): [number, number, number] {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) throw new RangeError('Invalid date input')

  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(year, month - 1, day)
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    throw new RangeError('Invalid date input')
  }
  return [year, month, day]
}

function toPeriodBoundaryIso(value: string, endOfDay: boolean): string {
  const [year, month, day] = parseDateInput(value)
  const date = new Date(
    year,
    month - 1,
    day,
    endOfDay ? 23 : 0,
    endOfDay ? 59 : 0,
    endOfDay ? 59 : 0,
    endOfDay ? 999 : 0,
  )
  return date.toISOString()
}

export function toPeriodStartIso(value: string): string {
  return toPeriodBoundaryIso(value, false)
}

export function toPeriodEndIso(value: string): string {
  return toPeriodBoundaryIso(value, true)
}

export function toDateInputValue(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
