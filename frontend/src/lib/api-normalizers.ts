export function normalizeList<T>(items: unknown): T[] {
  return Array.isArray(items) ? items : []
}
