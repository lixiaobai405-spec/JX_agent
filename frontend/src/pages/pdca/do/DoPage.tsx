import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sparkles, RefreshCw, MessageSquarePlus, ClipboardList, AlertCircle } from 'lucide-react'
import {
  useCurrentPeriod, useCurrentGoal, useIndicators,
  useLatestDiagnostic, useMyCoachingRequests, useIndicatorCheckins,
} from '@/hooks'
import { doApi } from '@/api/do'
import { TrafficLight } from '@/components/shared/TrafficLight'
import { AILoadingSkeleton } from '@/components/shared/AILoadingSkeleton'
import type { Indicator } from '@/types'

function CheckinDialog({ indicator, onCheckinSubmit }: { indicator: Indicator; onCheckinSubmit?: () => void }) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState('')
  const [desc, setDesc] = useState('')
  const [issues, setIssues] = useState('')
  const qc = useQueryClient()
  const { data: checkins } = useIndicatorCheckins(indicator.id)
  const latestCheckin = checkins?.[0]

  const { mutate, isPending } = useMutation({
    mutationFn: () => doApi.submitCheckin({
      indicator_id: indicator.id,
      actual_value: parseFloat(value),
      progress_description: desc || undefined,
      issues: issues || undefined,
    }),
    onSuccess: () => {
      toast.success('打卡成功，请重新生成诊断报告以查看最新分析')
      qc.invalidateQueries({ queryKey: ['checkins', indicator.id] })
      onCheckinSubmit?.()
      setOpen(false)
    },
  })

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <ClipboardList data-icon="inline-start" />
        打卡
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>提交进度 · {indicator.name}</DialogTitle></DialogHeader>
          <div className="flex flex-col gap-4 pt-2">
            {indicator.target_value != null && (
              <p className="text-sm text-muted-foreground">目标值：<span className="font-medium text-foreground">{indicator.target_value}</span></p>
            )}
            {latestCheckin && (
              <p className="text-sm text-muted-foreground">上次填报：<span className="font-medium text-foreground">{(latestCheckin.actual_value as Record<string, number>).value}</span></p>
            )}
            <div className="flex flex-col gap-1.5">
              <Label>实际值</Label>
              <Input type="number" value={value} onChange={(e) => setValue(e.target.value)} placeholder="输入本期实际数值" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>进展说明</Label>
              <Textarea rows={3} value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="描述本期主要工作进展..." />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>问题/障碍</Label>
              <Textarea rows={2} value={issues} onChange={(e) => setIssues(e.target.value)} placeholder="遇到的困难或需要协调的资源..." />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button onClick={() => mutate()} disabled={isPending || !value.trim()}>
                {isPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                提交打卡
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function CoachingDialog({ reportId }: { reportId?: string }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [urgency, setUrgency] = useState('normal')
  const qc = useQueryClient()

  const { mutate, isPending } = useMutation({
    mutationFn: () => doApi.createCoachingRequest({
      diagnostic_report_id: reportId ?? '',
      request_reason: reason,
      urgency_level: urgency,
    }),
    onSuccess: () => {
      toast.success('辅导请求已发送给上级')
      qc.invalidateQueries({ queryKey: ['coaching'] })
      setOpen(false)
    },
  })

  return (
    <>
      <Button variant="outline" size="sm" disabled={!reportId} onClick={() => setOpen(true)}>
        <MessageSquarePlus data-icon="inline-start" />
        申请辅导
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>申请辅导</DialogTitle></DialogHeader>
          <div className="flex flex-col gap-4 pt-2">
            <div className="flex flex-col gap-1.5">
              <Label>紧急程度</Label>
              <Select value={urgency} onValueChange={(v) => v && setUrgency(v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">低</SelectItem>
                  <SelectItem value="normal">一般</SelectItem>
                  <SelectItem value="high">紧急</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>请求原因</Label>
              <Textarea rows={4} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="说明需要辅导的具体问题..." />
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
              <Button onClick={() => mutate()} disabled={isPending}>
                {isPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                提交请求
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function IndicatorCard({ indicator, onCheckinSubmit }: { indicator: Indicator; onCheckinSubmit?: () => void }) {
  const { data: checkins } = useIndicatorCheckins(indicator.id)
  const latestValue = checkins?.[0] ? (checkins[0].actual_value as Record<string, number>).value : null

  return (
    <Card>
      <CardContent className="flex items-center justify-between py-3">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{indicator.name}</span>
            {indicator.redline && <Badge variant="destructive" className="text-xs">一票否决</Badge>}
          </div>
          <div className="flex gap-2 text-xs text-muted-foreground">
            <span>权重 {Math.round(indicator.weight * 100)}%</span>
            {indicator.target_value != null && <span>目标 {indicator.target_value}</span>}
            {latestValue != null && <span className="text-foreground font-medium">实际 {latestValue}</span>}
          </div>
        </div>
        <CheckinDialog indicator={indicator} onCheckinSubmit={onCheckinSubmit} />
      </CardContent>
    </Card>
  )
}

export function DoPage() {
  const { data: period } = useCurrentPeriod()
  const { data: goal } = useCurrentGoal(period?.id)
  const { data: indicators, isLoading: indLoading } = useIndicators(goal?.id)
  const { data: diagnostic } = useLatestDiagnostic(goal?.id)
  const { data: allCoachingRequests } = useMyCoachingRequests()
  const qc = useQueryClient()

  // Filter coaching requests to only show those for the current goal
  const coachingRequests = allCoachingRequests?.filter(r => r.goal_id === goal?.id)

  const [diagFeedback, setDiagFeedback] = useState('')
  const [hasPendingCheckin, setHasPendingCheckin] = useState(false)

  const { mutate: generateDiag, isPending: genDiagPending } = useMutation({
    mutationFn: () => doApi.generateDiagnostic(goal!.id, diagFeedback || undefined),
    onSuccess: () => {
      toast.success('诊断报告生成完成')
      qc.invalidateQueries({ queryKey: ['diagnostic'] })
      setHasPendingCheckin(false)
    },
  })

  if (!period) {
    return (
      <div className="flex flex-col gap-4 max-w-3xl">
        <h1 className="text-2xl font-semibold">D - 执行追踪</h1>
        <Card><CardContent className="py-10 text-center text-muted-foreground">暂无考核期或合同未确认，请先完成 P 阶段</CardContent></Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">D - 执行追踪</h1>
          <p className="text-sm text-muted-foreground mt-1">{period.name}</p>
        </div>
        {diagnostic && <TrafficLight status={diagnostic.traffic_light_status} />}
      </div>

      {diagnostic && (
        <Card>
          <CardContent className="pt-4 flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">加权完成率</span>
              <span className="font-semibold text-base">
                {diagnostic.weighted_achievement_rate != null ? `${Math.round(diagnostic.weighted_achievement_rate)}%` : '—'}
              </span>
            </div>
            {diagnostic.weighted_achievement_rate != null && <Progress value={diagnostic.weighted_achievement_rate} />}
            <div className="flex gap-4 text-xs text-muted-foreground">
              <span>时间进度：{diagnostic.time_progress != null ? `${Math.round(diagnostic.time_progress)}%` : '—'}</span>
              {diagnostic.progress_deviation != null && (
                <span className={diagnostic.progress_deviation < 0 ? 'text-destructive' : 'text-green-600'}>
                  进度偏差：{diagnostic.progress_deviation > 0 ? '+' : ''}{Math.round(diagnostic.progress_deviation)}%
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 左栏：指标列表 */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">指标进度</h2>
          </div>
          {indLoading ? (
            <div className="flex flex-col gap-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
          ) : !indicators?.length ? (
            <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">暂无指标，请先完成 P 阶段确认合同</CardContent></Card>
          ) : (
            <div className="flex flex-col gap-2">
              {indicators.map((ind) => (
                <IndicatorCard key={ind.id} indicator={ind} onCheckinSubmit={() => setHasPendingCheckin(true)} />
              ))}
            </div>
          )}
        </div>

        {/* 右栏：诊断报告 */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">AI 诊断报告</h2>
            <CoachingDialog reportId={diagnostic?.id} />
          </div>
          {hasPendingCheckin && (
            <Alert className="border-orange-300 bg-orange-50 text-orange-800 dark:bg-orange-950 dark:text-orange-200">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>有新打卡数据，请点击「生成诊断报告」查看最新分析</AlertDescription>
            </Alert>
          )}
          <div className="flex flex-col gap-1.5">
            <Textarea rows={2} value={diagFeedback} onChange={(e) => setDiagFeedback(e.target.value)} placeholder="可补充背景（如：本月市场竞争加剧）..." className="text-sm" />
            <Button variant="outline" size="sm" className="self-start" onClick={() => generateDiag()} disabled={genDiagPending || !goal}>
              {genDiagPending ? <><RefreshCw data-icon="inline-start" className="animate-spin" />生成中...</> : <><Sparkles data-icon="inline-start" />生成诊断报告</>}
            </Button>
          </div>

          {genDiagPending && <AILoadingSkeleton lines={5} />}

          {diagnostic && !genDiagPending && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-sm">
                  <span>诊断结果 · {diagnostic.report_date?.slice(0, 10)}</span>
                  <TrafficLight status={diagnostic.traffic_light_status} />
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3 text-sm">
                {diagnostic.root_cause_analysis && (
                  <div>
                    <p className="font-medium mb-1 text-muted-foreground">根因分析</p>
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown>{
                        typeof diagnostic.root_cause_analysis === 'string'
                          ? diagnostic.root_cause_analysis
                          : JSON.stringify(diagnostic.root_cause_analysis)
                      }</ReactMarkdown>
                    </div>
                  </div>
                )}
                {diagnostic.improvement_suggestions && (
                  <div>
                    <p className="font-medium mb-1 text-muted-foreground">改进建议</p>
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown>{
                        typeof diagnostic.improvement_suggestions === 'string'
                          ? diagnostic.improvement_suggestions
                          : (diagnostic.improvement_suggestions as Record<string, string>).feedback ?? JSON.stringify(diagnostic.improvement_suggestions)
                      }</ReactMarkdown>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {(coachingRequests?.length ?? 0) > 0 && (
            <div className="flex flex-col gap-2">
              <h3 className="text-sm font-medium text-muted-foreground">我的辅导请求</h3>
              {coachingRequests!.map((req) => (
                <Card key={req.id}>
                  <CardContent className="flex items-center justify-between py-3 text-sm">
                    <span className="text-muted-foreground">{req.request_reason?.slice(0, 30) ?? '辅导请求'}</span>
                    <Badge variant={req.status === 'completed' ? 'secondary' : req.status === 'accepted' ? 'default' : 'outline'}>
                      {{ pending: '待处理', accepted: '已接受', completed: '已完成', rejected: '已拒绝' }[req.status]}
                    </Badge>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
