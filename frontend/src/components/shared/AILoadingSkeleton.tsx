import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

const LINE_WIDTHS = [92, 84, 96, 88, 90, 82]

export function AILoadingSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" style={{ width: `${LINE_WIDTHS[i % LINE_WIDTHS.length]}%` }} />
        ))}
      </CardContent>
    </Card>
  )
}
