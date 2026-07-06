import { cn } from '@/lib/utils'

interface TrafficLightProps {
  status: 'green' | 'yellow' | 'red' | null | undefined
  showLabel?: boolean
  className?: string
}

const MAP = {
  green: { color: 'bg-green-500', label: '正常' },
  yellow: { color: 'bg-yellow-400', label: '偏差' },
  red: { color: 'bg-red-500', label: '预警' },
}

export function TrafficLight({ status, showLabel = true, className }: TrafficLightProps) {
  if (!status) return null
  const { color, label } = MAP[status]
  return (
    <span className={cn('inline-flex items-center gap-1.5', className)}>
      <span className={cn('inline-block size-2.5 rounded-full', color)} />
      {showLabel && <span className="text-sm text-muted-foreground">{label}</span>}
    </span>
  )
}
