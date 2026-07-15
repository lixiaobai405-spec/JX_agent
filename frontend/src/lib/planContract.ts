import type { ContractIndicator } from '@/types'

export type ContractTargetsPayload = {
  targets: Array<{ indicator_id: string | number; target: number }>
}

export function buildContractTargets(
  indicators: Array<Pick<ContractIndicator, 'id' | 'target' | 'is_redline'>>,
  targetInputs: Record<string, string>,
): ContractTargetsPayload {
  return {
    targets: indicators
      .filter((indicator) => !indicator.is_redline)
      .map((indicator) => {
        const input = targetInputs[String(indicator.id)]
        const target = input?.trim() ? Number(input) : Number.NaN
        if (!Number.isFinite(target)) throw new Error('请为每个非红线指标填写有效目标值')
        return { indicator_id: indicator.id, target }
      }),
  }
}
