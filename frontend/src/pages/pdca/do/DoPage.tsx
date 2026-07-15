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
import { Sparkles, RefreshCw, MessageSquarePlus, ClipboardList, AlertCircle, ChevronDown, ChevronUp, Eye } from 'lucide-react'
import {
  useCurrentPeriod, useCurrentGoal, useIndicators,
  useLatestDiagnostic, useMyCoachingRequests, useIndicatorCheckins,
} from '@/hooks'
import { doApi } from '@/api/do'
import { TrafficLight } from '@/components/shared/TrafficLight'
import { AILoadingSkeleton } from '@/components/shared/AILoadingSkeleton'
import {
  filterCoachingRequestsByGoal,
  getCoachingResponseText,
  getCoachingStatusLabel,
  getDiagnosticToggleLabel,
} from '@/lib/coaching'
import { normalizeDiagnosticMarkdown } from '@/lib/diagnosticMarkdown'
import { getDiagnosticIndicatorStatus } from '@/lib/pdcaFeedback'
import {
  buildCheckinValue,
  formatCheckinValue,
  getIndicatorCheckinKind,
  isCheckinInputValid,
  QUALITATIVE_STATUS_LABELS,
} from '@/lib/checkins'
import { formatAchievementRate, toAchievementProgress } from '@/lib/performance'
import type { CoachingRequest, DiagnosticReport, Indicator } from '@/types'

function CheckinDialog({ indicator, onCheckinSubmit }: { indicator: Indicator; onCheckinSubmit?: () => void }) {
  const [open, setOpen] = useState(false)
  const [value, setValue] = useState('')
  const [desc, setDesc] = useState('')
  const [issues, setIssues] = useState('')
  const qc = useQueryClient()
  const { data: checkins } = useIndicatorCheckins(indicator.id)
  const latestCheckin = checkins?.[0]
  const checkinKind = getIndicatorCheckinKind(indicator)
  const targetDisplay = indicator.target_display ?? (
    indicator.target_value != null ? `${indicator.target_value}${indicator.unit ?? ''}` : null
  )

  const { mutate, isPending } = useMutation({
    mutationFn: () => doApi.submitCheckin({
      indicator_id: indicator.id,
      actual_value: buildCheckinValue(indicator, value),
      progress_description: desc || undefined,
      issues: issues || undefined,
    }),
    onSuccess: () => {
      toast.success('打卡成功，请重新生成诊断报告以查看最新分析')
      qc.invalidateQueries({ queryKey: ['checkins', indicator.id] })
      onCheckinSubmit?.()
      setValue('')
      setDesc('')
      setIssues('')
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
            {targetDisplay && (
              <p className="text-sm text-muted-foreground">目标值：<span className="font-medium text-foreground">{targetDisplay}</span></p>
            )}
            {latestCheckin && (
              <p className="text-sm text-muted-foreground">上次填报：<span className="font-medium text-foreground">{formatCheckinValue(latestCheckin.actual_value, indicator.unit)}</span></p>
            )}
            <div className="flex flex-col gap-1.5">
              {checkinKind === 'qualitative' ? (
                <>
                  <Label>完成状态</Label>
                  <Select value={value} onValueChange={(nextValue) => nextValue && setValue(nextValue)}>
                    <SelectTrigger className="w-full"><SelectValue placeholder="选择完成状态" /></SelectTrigger>
                    <SelectContent>
                      {Object.entries(QUALITATIVE_STATUS_LABELS).map(([status, label]) => (
                        <SelectItem key={status} value={status}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </>
              ) : (
                <>
                  <Label>{checkinKind === 'redline' ? '发生次数' : '实际完成值'}</Label>
                  <Input
                    type="number"
                    min={checkinKind === 'redline' ? 0 : undefined}
                    step={checkinKind === 'redline' ? 1 : 'any'}
                    inputMode={checkinKind === 'redline' ? 'numeric' : 'decimal'}
                    value={value}
                    onChange={(event) => setValue(event.target.value)}
                    placeholder={checkinKind === 'redline' ? '输入非负整数次数' : '输入本期实际完成值'}
                  />
                </>
              )}
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
              <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>取消</Button>
              <Button onClick={() => mutate()} disabled={isPending || !isCheckinInputValid(indicator, value)}>
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
      qc.invalidateQueries({ queryKey: ['coaching', 'my'] })
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
              <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>取消</Button>
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

function CoachingRequestDetailDialog({ request }: { request: CoachingRequest }) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <Eye data-icon="inline-start" />
        查看
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>辅导请求详情</DialogTitle></DialogHeader>
          <div className="flex flex-col gap-4 pt-2 text-sm">
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <p className="text-xs text-muted-foreground">状态</p>
                <p className="mt-1 font-medium">{getCoachingStatusLabel(request.status)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">紧急程度</p>
                <p className="mt-1 font-medium">
                  {{ low: '低', normal: '一般', high: '紧急' }[request.urgency_level]}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">创建时间</p>
                <p className="mt-1 break-words font-medium">{request.created_at}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">更新时间</p>
                <p className="mt-1 break-words font-medium">{request.updated_at}</p>
              </div>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">请求原因</p>
              <p className="mt-1 whitespace-pre-wrap rounded-lg bg-muted/50 p-3">
                {request.request_reason?.trim() || '未填写请求原因'}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">上级回复</p>
              <p className="mt-1 whitespace-pre-wrap rounded-lg bg-muted/50 p-3">
                {getCoachingResponseText(request.notes)}
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

function IndicatorCard({
  indicator,
  diagnostic,
  onCheckinSubmit,
}: {
  indicator: Indicator
  diagnostic?: DiagnosticReport | null
  onCheckinSubmit?: () => void
}) {
  const { data: checkins } = useIndicatorCheckins(indicator.id)
  const latestValue = checkins?.[0] ? formatCheckinValue(checkins[0].actual_value, indicator.unit) : null
  const status = getDiagnosticIndicatorStatus(diagnostic, indicator)

  return (
    <Card>
      <CardContent className="flex flex-col items-stretch gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-col gap-0.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="break-words text-sm font-medium">{indicator.name}</span>
            {indicator.redline && <Badge variant="destructive" className="text-xs">一票否决</Badge>}
            <TrafficLight status={status} />
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
            <span>权重 {formatAchievementRate(indicator.weight * 100)}</span>
            {(indicator.target_display || indicator.target_value != null) && (
              <span>目标 {indicator.target_display ?? `${indicator.target_value}${indicator.unit ?? ''}`}</span>
            )}
            {latestValue != null && <span className="text-foreground font-medium">实际 {latestValue}</span>}
          </div>
        </div>
        <CheckinDialog indicator={indicator} onCheckinSubmit={onCheckinSubmit} />
      </CardContent>
    </Card>
  )
}

function DiagnosticMarkdown({ content }: { content: string }) {
  return (
    <div className="prose prose-sm max-w-none break-words leading-7 dark:prose-invert prose-headings:mb-2 prose-headings:mt-4 prose-p:my-2 prose-ol:my-2 prose-ol:pl-5 prose-ul:my-2 prose-ul:pl-5 prose-li:my-1 prose-hr:my-4 prose-hr:border-border">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}

export function DoPage() {
  const { data: period } = useCurrentPeriod()
  const { data: goal } = useCurrentGoal(period?.id)
  const { data: indicators, isLoading: indLoading } = useIndicators(goal?.id)
  const { data: diagnostic } = useLatestDiagnostic(goal?.id)
  const { data: allCoachingRequests } = useMyCoachingRequests()
  const qc = useQueryClient()

  const coachingRequests = filterCoachingRequestsByGoal(allCoachingRequests, goal?.id)

  const [diagFeedback, setDiagFeedback] = useState('')
  const [hasPendingCheckin, setHasPendingCheckin] = useState(false)
  const [isDiagnosticOpen, setIsDiagnosticOpen] = useState(true)
  const rootCauseMarkdown = normalizeDiagnosticMarkdown(diagnostic?.root_cause_analysis)
  const improvementMarkdown = normalizeDiagnosticMarkdown(diagnostic?.improvement_suggestions)
  const shouldShowImprovementMarkdown = Boolean(
    improvementMarkdown && improvementMarkdown !== rootCauseMarkdown,
  )

  const { mutate: generateDiag, isPending: genDiagPending } = useMutation({
    mutationFn: () => doApi.generateDiagnostic(goal!.id, diagFeedback || undefined),
    onSuccess: () => {
      toast.success('诊断报告生成完成')
      qc.invalidateQueries({ queryKey: ['diagnostic', goal?.id] })
      setHasPendingCheckin(false)
    },
  })

  if (!period) {
    return (
      <div className="flex flex-col gap-4 max-w-3xl">
        <h1 className="text-2xl font-semibold">D - 执行追踪</h1>
        <p className="text-sm text-muted-foreground">按指标类型填报完成情况，并生成单项状态与偏差诊断。</p>
        <Card><CardContent className="py-10 text-center text-muted-foreground">暂无考核期或合约未确认，请先完成 P 阶段</CardContent></Card>
      </div>
    )
  }

  return (
    <div className="flex w-full max-w-4xl flex-col gap-6">
      <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">D - 执行追踪</h1>
          <p className="mt-1 text-sm text-muted-foreground">按指标类型填报完成情况，并生成单项状态与偏差诊断。</p>
        </div>
        {diagnostic && <TrafficLight status={diagnostic.traffic_light_status} />}
      </div>

      {diagnostic && (
        <Card>
          <CardContent className="pt-4 flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">加权达成率</span>
              <span className="font-semibold text-base">
                {formatAchievementRate(diagnostic.weighted_achievement_rate)}
              </span>
            </div>
            {diagnostic.weighted_achievement_rate != null && <Progress value={toAchievementProgress(diagnostic.weighted_achievement_rate)} />}
            <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
              <span>时间进度：{formatAchievementRate(diagnostic.time_progress)}</span>
              {diagnostic.progress_deviation != null && (
                <span className={diagnostic.progress_deviation < 0 ? 'text-destructive' : 'text-green-600'}>
                  进度偏差：{diagnostic.progress_deviation > 0 ? '+' : ''}{formatAchievementRate(diagnostic.progress_deviation)}
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
            <Card><CardContent className="py-6 text-center text-sm text-muted-foreground">暂无指标，请先完成 P 阶段确认合约</CardContent></Card>
          ) : (
            <div className="flex flex-col gap-2">
              {indicators.map((ind) => (
                <IndicatorCard
                  key={ind.id}
                  indicator={ind}
                  diagnostic={diagnostic}
                  onCheckinSubmit={() => setHasPendingCheckin(true)}
                />
              ))}
            </div>
          )}
        </div>

        {/* 右栏：诊断报告 */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">AI 偏差分析</h2>
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
                  <div className="flex items-center gap-1">
                    <TrafficLight status={diagnostic.traffic_light_status} />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      aria-label={getDiagnosticToggleLabel(isDiagnosticOpen)}
                      title={getDiagnosticToggleLabel(isDiagnosticOpen)}
                      onClick={() => setIsDiagnosticOpen((value) => !value)}
                    >
                      {isDiagnosticOpen ? <ChevronUp /> : <ChevronDown />}
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              {isDiagnosticOpen && (
                <CardContent className="flex flex-col gap-3 text-sm">
                  {rootCauseMarkdown && (
                    <div>
                      <p className="font-medium mb-1 text-muted-foreground">诊断内容</p>
                      <DiagnosticMarkdown content={rootCauseMarkdown} />
                    </div>
                  )}
                  {shouldShowImprovementMarkdown && (
                    <div>
                      <p className="font-medium mb-1 text-muted-foreground">改进建议</p>
                      <DiagnosticMarkdown content={improvementMarkdown} />
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          )}

          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium text-muted-foreground">我的辅导请求</h3>
            {coachingRequests.length === 0 ? (
              <Card>
                <CardContent className="py-6 text-center text-sm text-muted-foreground">暂无数据</CardContent>
              </Card>
            ) : (
              coachingRequests.map((req) => (
                <Card key={req.id}>
                  <CardContent className="flex items-center justify-between gap-3 py-3 text-sm">
                    <span className="min-w-0 flex-1 truncate text-muted-foreground">{req.request_reason?.slice(0, 30) ?? '辅导请求'}</span>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={req.status === 'completed' ? 'secondary' : req.status === 'accepted' ? 'default' : 'outline'}>
                        {getCoachingStatusLabel(req.status)}
                      </Badge>
                      <CoachingRequestDetailDialog request={req} />
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
