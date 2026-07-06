import { Badge } from '@/components/ui/badge'
import type { PeriodStatus } from '@/types'

const MAP: Record<PeriodStatus | 'P' | 'D' | 'C' | 'A', { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  draft: { label: '草稿', variant: 'secondary' },
  open: { label: '进行中', variant: 'default' },
  closed: { label: '已结束', variant: 'outline' },
  archived: { label: '已归档', variant: 'outline' },
  P: { label: 'P 目标设定', variant: 'secondary' },
  D: { label: 'D 执行追踪', variant: 'default' },
  C: { label: 'C 考核评估', variant: 'default' },
  A: { label: 'A 复盘发展', variant: 'outline' },
}

export function PhaseStatusBadge({ status }: { status: string }) {
  const config = MAP[status as keyof typeof MAP] ?? { label: status, variant: 'secondary' as const }
  return <Badge variant={config.variant}>{config.label}</Badge>
}
