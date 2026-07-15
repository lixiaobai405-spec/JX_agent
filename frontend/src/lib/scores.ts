export type ScoreDraftMap = Record<string, { score?: string; comment?: string }>
export type PersistedScoreMap = Record<string, { score?: number; comment?: string | null }>

export function buildCompleteScoreDraft(
  indicatorIds: string[],
  edits: ScoreDraftMap,
  persisted: PersistedScoreMap,
): ScoreDraftMap {
  return Object.fromEntries(
    indicatorIds.map((indicatorId) => {
      const saved = persisted[indicatorId]
      return [
        indicatorId,
        {
          score: edits[indicatorId]?.score ?? (saved?.score == null ? '' : String(saved.score)),
          comment: edits[indicatorId]?.comment ?? saved?.comment ?? '',
        },
      ]
    }),
  )
}

export function mergeScoreDraft(
  edits: ScoreDraftMap,
  persisted: PersistedScoreMap,
): ScoreDraftMap {
  const indicatorIds = new Set([...Object.keys(persisted), ...Object.keys(edits)])
  return buildCompleteScoreDraft([...indicatorIds], edits, persisted)
}

export function clampScore(value: number): number {
  if (!Number.isFinite(value)) return 0
  if (value < 0) return 0
  if (value > 100) return 100
  return value
}

export function parseScoreInput(value: string): string {
  if (value.trim() === '') return ''
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return ''
  return String(clampScore(parsed))
}

export function isScoreInRange(value: string): boolean {
  if (value.trim() === '') return false
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100
}

export function hasInvalidScores(items: ScoreDraftMap): boolean {
  return Object.values(items).some((item) => !isScoreInRange(item.score ?? ''))
}

export function toScorePayload(items: ScoreDraftMap): Record<string, { score: number; comment: string }> {
  return Object.fromEntries(
    Object.entries(items).map(([id, value]) => [
      id,
      {
        score: clampScore(Number(value.score ?? '')),
        comment: value.comment ?? '',
      },
    ]),
  )
}
