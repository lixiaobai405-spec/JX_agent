import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import ReactMarkdown from 'react-markdown'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sparkles, RefreshCw, CheckCircle2, ThumbsUp, ThumbsDown, Clock } from 'lucide-react'
import {
  useCurrentUser, useCurrentPeriod, useCurrentGoal, useFinalResult,
  useMyPlans, useReviewReportByUser, useInheritanceSuggestions, usePeriods, useTeamPlans,
} from '@/hooks'
import { actionApi } from '@/api/action'
import { AILoadingSkeleton } from '@/components/shared/AILoadingSkeleton'
import { getPlanText, getSuggestionSummary } from '@/lib/pdcaFeedback'

const SUGGESTION_TYPE_MAP: Record<string, string> = {
  new_goal: '新目标', new_indicator: '新指标', adjust_weight: '调整权重', raise_target: '提高目标',
}

type PlanAiSuggestions = {
  polished_goals?: string
  polished_actions?: string
  overall_review?: string
}

export function ActionPage() {
  const { data: user } = useCurrentUser()
  const { data: period } = useCurrentPeriod()
  const { data: periods } = usePeriods()
  const { data: goal } = useCurrentGoal(period?.id)
  const { data: finalResult } = useFinalResult(goal?.id)
  const qc = useQueryClient()

  // Persistent loading — survives navigation/refresh
  const { data: report, isLoading: reportLoading } = useReviewReportByUser(user?.id, period?.id)
  const { data: plans } = useMyPlans()
  const { data: teamPlans } = useTeamPlans()
  const plan = plans?.find((p) => p.review_report_id === report?.id)
  const isManager = user?.role === 'manager' || user?.role === 'hr_admin' || user?.role === 'system_admin'
  const nextPeriod = periods
    ?.filter((item) =>
      item.user_id === user?.id &&
      period &&
      new Date(item.start_date).getTime() > new Date(period.start_date).getTime()
    )
    .sort((a, b) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())[0]
  const { data: suggestions } = useInheritanceSuggestions(
    plan?.status === 'approved' && nextPeriod ? user?.id : undefined,
    plan?.status === 'approved' && nextPeriod ? nextPeriod.id : undefined,
  )
  const pendingTeamPlans = isManager ? teamPlans?.filter((item) => item.status === 'reviewed') : []

  const [feedback, setFeedback] = useState('')
  const [planGoals, setPlanGoals] = useState<string | null>(null)
  const [planActions, setPlanActions] = useState<string | null>(null)
  const [planFeedback, setPlanFeedback] = useState('')
  const [polishedGoals, setPolishedGoals] = useState<string | null>(null)
  const [polishedActions, setPolishedActions] = useState<string | null>(null)
  const [rejectSuggestionId, setRejectSuggestionId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectPlanId, setRejectPlanId] = useState<string | null>(null)
  const [rejectPlanReason, setRejectPlanReason] = useState('')

  const planAiSuggestions = plan?.ai_suggestions as PlanAiSuggestions | null | undefined
  const planGoalText = planGoals ?? getPlanText(plan?.goals)
  const planActionText = planActions ?? getPlanText(plan?.actions)
  const polishedGoalText = polishedGoals ?? planAiSuggestions?.polished_goals ?? ''
  const polishedActionText = polishedActions ?? planAiSuggestions?.polished_actions ?? ''

  const planPayload = () => ({
    goals: { text: planGoalText },
    actions: { text: planActionText },
  })

  const { mutate: generateReport, isPending: reportPending } = useMutation({
    mutationFn: () => actionApi.generateReviewReport(finalResult!.id),
    onSuccess: () => {
      toast.success('复盘报告生成完成')
      qc.invalidateQueries({ queryKey: ['review-report-user', user?.id, period?.id] })
    },
  })

  const { mutate: submitFeedback, isPending: feedbackPending } = useMutation({
    mutationFn: () => actionApi.submitReviewFeedback(report!.id, feedback),
    onSuccess: () => {
      toast.success('反馈已提交')
      qc.invalidateQueries({ queryKey: ['review-report-user', user?.id, period?.id] })
    },
  })

  const { mutate: savePlanDraft, isPending: savePlanPending } = useMutation({
    mutationFn: () => plan
      ? actionApi.updateDevelopmentPlan(plan.id, planPayload())
      : actionApi.createDevelopmentPlan({
          review_report_id: report!.id,
          ...planPayload(),
        }),
    onSuccess: () => {
      toast.success('IDP 草稿已保存')
      qc.invalidateQueries({ queryKey: ['my-plans'] })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'IDP 草稿保存失败')
    },
  })

  const { mutate: aiReviewPlan, isPending: aiPending } = useMutation({
    mutationFn: async () => {
      const savedPlan = plan
        ? await actionApi.updateDevelopmentPlan(plan.id, planPayload())
        : await actionApi.createDevelopmentPlan({
            review_report_id: report!.id,
            ...planPayload(),
          })
      return actionApi.aiReviewPlan(savedPlan.id, planFeedback || undefined)
    },
    onSuccess: (updatedPlan) => {
      const suggestions = updatedPlan.ai_suggestions as PlanAiSuggestions | null
      setPolishedGoals(suggestions?.polished_goals || '')
      setPolishedActions(suggestions?.polished_actions || '')
      toast.success('AI 审核完成')
      qc.invalidateQueries({ queryKey: ['my-plans'] })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'AI 润色触发失败，请稍后重试')
    },
  })

  const { mutate: acceptPolish, isPending: acceptPending } = useMutation({
    mutationFn: () => actionApi.updateDevelopmentPlan(plan!.id, {
      goals: { text: polishedGoalText },
      actions: { text: polishedActionText },
    }),
    onSuccess: () => {
      toast.success('已采纳 AI 润色建议')
      setPolishedGoals('')
      setPolishedActions('')
      qc.invalidateQueries({ queryKey: ['my-plans'] })
    },
  })

  const { mutate: submitPlan, isPending: submitPending } = useMutation({
    mutationFn: async () => {
      const savedPlan = plan
        ? await actionApi.updateDevelopmentPlan(plan.id, planPayload())
        : await actionApi.createDevelopmentPlan({
            review_report_id: report!.id,
            ...planPayload(),
          })
      return actionApi.submitPlan(savedPlan.id)
    },
    onSuccess: () => {
      toast.success('IDP 已提交给经理审批')
      qc.invalidateQueries({ queryKey: ['my-plans'] })
      qc.invalidateQueries({ queryKey: ['team-plans'] })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'IDP 提交失败')
    },
  })

  const { mutate: genSuggestions, isPending: suggPending } = useMutation({
    mutationFn: () => actionApi.generateInheritanceSuggestions(user!.id, period!.id, nextPeriod!.id),
    onSuccess: () => {
      toast.success('继承建议已生成')
      qc.invalidateQueries({ queryKey: ['inheritance-suggestions', user?.id, nextPeriod?.id] })
    },
  })

  const { mutate: approveTeamPlan } = useMutation({
    mutationFn: (id: string) => actionApi.approvePlan(id, true),
    onSuccess: () => {
      toast.success('IDP 已通过审批')
      qc.invalidateQueries({ queryKey: ['team-plans'] })
      qc.invalidateQueries({ queryKey: ['my-plans'] })
    },
  })

  const { mutate: rejectTeamPlan, isPending: rejectPlanPending } = useMutation({
    mutationFn: ({ id, comment }: { id: string; comment: string }) => actionApi.approvePlan(id, false, comment),
    onSuccess: () => {
      toast.success('已退回修改')
      qc.invalidateQueries({ queryKey: ['team-plans'] })
      qc.invalidateQueries({ queryKey: ['my-plans'] })
      setRejectPlanId(null)
      setRejectPlanReason('')
    },
  })

  const { mutate: acceptSugg } = useMutation({
    mutationFn: (id: string) => actionApi.acceptSuggestion(id),
    onSuccess: () => {
      toast.success('已采纳')
      qc.invalidateQueries({ queryKey: ['inheritance-suggestions', user?.id, nextPeriod?.id] })
    },
  })

  const { mutate: rejectSugg } = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => actionApi.rejectSuggestion(id, reason),
    onSuccess: () => {
      toast.success('已拒绝')
      qc.invalidateQueries({ queryKey: ['inheritance-suggestions', user?.id, nextPeriod?.id] })
      setRejectSuggestionId(null)
      setRejectReason('')
    },
  })

  if (!finalResult) {
    return (
      <div className="flex flex-col gap-4 max-w-2xl">
        <h1 className="text-2xl font-semibold">A - 复盘发展</h1>
        <p className="text-sm text-muted-foreground">沉淀复盘结论，制定 IDP，并把改进项转化为下期继承建议。</p>
        <Card><CardContent className="py-10 text-center text-muted-foreground">请先完成 C 阶段并确认最终结果</CardContent></Card>
      </div>
    )
  }

  // Structured field accessors
  const sa = report?.strengths_analysis as { strengths: { indicator: string; score: number; comment: string }[]; summary: string } | null
  const ia = report?.improvement_areas as { areas: { indicator: string; score: number; suggestion: string }[] } | null

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">A - 复盘发展</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {period?.name} · 沉淀复盘结论，制定 IDP，并把改进项转化为下期继承建议。
        </p>
      </div>

      {isManager && (pendingTeamPlans?.length ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">待审批发展计划</CardTitle>
            <CardDescription>处理团队成员提交的 IDP</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {pendingTeamPlans!.map((item) => (
              <div key={item.id} className="flex items-start justify-between gap-3 rounded-md border p-3">
                <div className="min-w-0 flex-1 text-sm">
                  <p className="font-medium truncate">{(item.goals as { text?: string }).text ?? '发展目标'}</p>
                  <p className="mt-1 text-muted-foreground line-clamp-2">{(item.actions as { text?: string }).text ?? '行动计划'}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setRejectPlanId(item.id)
                      setRejectPlanReason('')
                    }}
                  >
                    退回
                  </Button>
                  <Button size="sm" onClick={() => approveTeamPlan(item.id)}>通过</Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* ① 复盘报告 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">① 复盘报告</CardTitle>
          <CardDescription>AI 根据本期绩效结果生成深度分析</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {reportLoading ? (
            <AILoadingSkeleton lines={6} />
          ) : !report ? (
            <Button className="self-start" onClick={() => generateReport()} disabled={reportPending}>
              {reportPending
                ? <><RefreshCw data-icon="inline-start" className="animate-spin" />生成中...</>
                : <><Sparkles data-icon="inline-start" />生成复盘报告</>}
            </Button>
          ) : (
            <div className="flex flex-col gap-4">
              {sa?.summary && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">总体评价</p>
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown>{sa.summary}</ReactMarkdown>
                  </div>
                </div>
              )}
              {sa?.strengths && sa.strengths.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">优势分析</p>
                  <ul className="flex flex-col gap-1.5">
                    {sa.strengths.map((s, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <Badge variant="secondary" className="shrink-0 mt-0.5">{s.indicator}</Badge>
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          <ReactMarkdown>{s.comment}</ReactMarkdown>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {ia?.areas && ia.areas.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">待改进领域</p>
                  <ul className="flex flex-col gap-1.5">
                    {ia.areas.map((a, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <Badge variant="outline" className="shrink-0 mt-0.5">{a.indicator}</Badge>
                        <div className="prose prose-sm max-w-none dark:prose-invert">
                          <ReactMarkdown>{a.suggestion}</ReactMarkdown>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!report.reviewed_by_user && (
                <>
                  <Separator />
                  <div className="flex flex-col gap-1.5">
                    <Label>我的感想与反馈</Label>
                    <Textarea rows={3} value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="对本期复盘报告的看法和补充..." />
                    <Button size="sm" className="self-start" onClick={() => submitFeedback()} disabled={feedbackPending || !feedback.trim()}>提交反馈</Button>
                  </div>
                </>
              )}
              {report.reviewed_by_user && <Badge variant="secondary" className="self-start">已提交反馈</Badge>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ② IDP */}
      {report && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">② 个人发展计划（IDP）</CardTitle>
            <CardDescription>基于复盘报告制定下一步成长计划</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {plan?.status === 'approved' ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="size-5 text-primary" />
                  <p className="text-sm font-medium">IDP 已通过审批</p>
                </div>
                <div className="flex flex-col gap-1">
                  <p className="text-xs text-muted-foreground font-medium">发展目标</p>
                  <p className="whitespace-pre-wrap text-sm">{getPlanText(plan.goals)}</p>
                </div>
                <div className="flex flex-col gap-1">
                  <p className="text-xs text-muted-foreground font-medium">行动计划</p>
                  <p className="whitespace-pre-wrap text-sm">{getPlanText(plan.actions)}</p>
                </div>
              </div>
            ) : plan?.status === 'reviewed' ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="size-4" />
                  <span>IDP 已提交，等待经理审批</span>
                  <Badge variant="secondary">待审批</Badge>
                </div>
                <div className="flex flex-col gap-1">
                  <p className="text-xs text-muted-foreground font-medium">发展目标</p>
                  <p className="whitespace-pre-wrap text-sm">{getPlanText(plan.goals)}</p>
                </div>
                <div className="flex flex-col gap-1">
                  <p className="text-xs text-muted-foreground font-medium">行动计划</p>
                  <p className="whitespace-pre-wrap text-sm">{getPlanText(plan.actions)}</p>
                </div>
              </div>
            ) : plan ? (
              <div className="flex flex-col gap-3">
                {plan.carry_forward_reason && (
                  <Card className="border-destructive/40 bg-destructive/5">
                    <CardContent className="pt-3 text-sm">
                      <p className="font-medium text-destructive mb-1">经理反馈（请修改后重新提交）</p>
                      <p className="text-muted-foreground">{plan.carry_forward_reason}</p>
                    </CardContent>
                  </Card>
                )}
                <div className="flex flex-col gap-1.5">
                  <Label>发展目标</Label>
                  <Textarea
                    rows={3}
                    value={planGoalText}
                    onChange={(e) => setPlanGoals(e.target.value)}
                    placeholder="描述具体发展目标，建议参考复盘报告的建议..."
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>行动计划</Label>
                  <Textarea
                    rows={3}
                    value={planActionText}
                    onChange={(e) => setPlanActions(e.target.value)}
                    placeholder="列出具体行动步骤、时间节点和所需资源..."
                  />
                </div>
                {plan.smart_evaluation && (
                  <Card className="border-primary/30">
                    <CardContent className="pt-3 flex flex-col gap-3">
                      <p className="font-medium text-sm">AI SMART 评估</p>
                      <div className="grid gap-2 text-sm">
                        {Object.entries(plan.smart_evaluation as Record<string, { status: string; comment: string }>).map(([key, val]) => (
                          <div key={key} className="flex items-start gap-2">
                            <span className="text-base shrink-0">{val.status}</span>
                            <div className="flex-1">
                              <span className="font-medium">{key === 'specific' ? '具体性' : key === 'measurable' ? '可衡量' : key === 'achievable' ? '可实现' : key === 'relevant' ? '相关性' : '时限性'}</span>
                              <span className="text-muted-foreground ml-2">{val.comment}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
                {polishedGoalText && polishedActionText ? (
                  <Card className="border-green-500/30 bg-green-50/50 dark:bg-green-950/20">
                    <CardContent className="pt-3 flex flex-col gap-3">
                      <p className="font-medium text-sm">AI 润色建议（可编辑）</p>
                      <div className="flex flex-col gap-1.5">
                        <Label>润色后的目标</Label>
                        <Textarea rows={4} value={polishedGoalText} onChange={(e) => setPolishedGoals(e.target.value)} className="bg-background" />
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <Label>润色后的行动计划</Label>
                        <Textarea rows={4} value={polishedActionText} onChange={(e) => setPolishedActions(e.target.value)} className="bg-background" />
                      </div>
                      <Button size="sm" className="self-start" onClick={() => acceptPolish()} disabled={acceptPending}>
                        {acceptPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                        采纳润色建议
                      </Button>
                    </CardContent>
                  </Card>
                ) : null}
                {plan.ai_suggestions && (plan.ai_suggestions as PlanAiSuggestions).overall_review && (
                  <Card className="border-primary/30">
                    <CardContent className="pt-3">
                      <p className="font-medium text-sm mb-2">综合评价</p>
                      <div className="prose prose-sm max-w-none dark:prose-invert">
                        <ReactMarkdown>{(plan.ai_suggestions as PlanAiSuggestions).overall_review ?? ''}</ReactMarkdown>
                      </div>
                    </CardContent>
                  </Card>
                )}
                <div className="flex flex-col gap-1.5">
                  <Label>AI 审核反馈（可选）</Label>
                  <Textarea rows={2} value={planFeedback} onChange={(e) => setPlanFeedback(e.target.value)} placeholder="如：请重点评估时间安排的合理性..." />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => savePlanDraft()}
                    disabled={savePlanPending || !planGoalText.trim()}
                  >
                    {savePlanPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    保存 IDP 草稿
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => aiReviewPlan()}
                    disabled={aiPending || !planGoalText.trim()}
                  >
                    {aiPending
                      ? <><RefreshCw data-icon="inline-start" className="animate-spin" />审核中...</>
                      : <><Sparkles data-icon="inline-start" />AI SMART 润色</>}
                  </Button>
                  <Button size="sm" onClick={() => submitPlan()} disabled={submitPending || !planGoalText.trim()}>
                    {submitPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    {plan.carry_forward_reason ? '重新提交给经理审批' : '提交给经理审批'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label>发展目标</Label>
                  <Textarea rows={3} value={planGoalText} onChange={(e) => setPlanGoals(e.target.value)} placeholder="描述具体发展目标，建议参考复盘报告的建议..." />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>行动计划</Label>
                  <Textarea rows={3} value={planActionText} onChange={(e) => setPlanActions(e.target.value)} placeholder="列出具体行动步骤、时间节点和所需资源..." />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>AI 审核反馈（可选）</Label>
                  <Textarea rows={2} value={planFeedback} onChange={(e) => setPlanFeedback(e.target.value)} placeholder="如：请重点评估时间安排的合理性..." />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => savePlanDraft()}
                    disabled={savePlanPending || !planGoalText.trim()}
                  >
                    {savePlanPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    保存 IDP 草稿
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => aiReviewPlan()}
                    disabled={aiPending || !planGoalText.trim()}
                  >
                    {aiPending
                      ? <><RefreshCw data-icon="inline-start" className="animate-spin" />审核中...</>
                      : <><Sparkles data-icon="inline-start" />保存并 AI SMART 润色</>}
                  </Button>
                  <Button size="sm" onClick={() => submitPlan()} disabled={submitPending || !planGoalText.trim()}>
                    {submitPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    提交给经理审批
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ③ 继承建议 */}
      {plan?.status === 'approved' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">③ 下期继承建议</CardTitle>
            <CardDescription>AI 根据本期情况推荐下期延续的目标和指标</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {!suggestions?.length ? (
              <div className="flex flex-col gap-2">
                {!nextPeriod && <p className="text-sm text-muted-foreground">暂无下期周期，请先创建下期考核期后再生成继承建议</p>}
                <Button variant="outline" className="self-start" onClick={() => genSuggestions()} disabled={suggPending || !nextPeriod}>
                  {suggPending
                    ? <><RefreshCw data-icon="inline-start" className="animate-spin" />生成中...</>
                    : <><Sparkles data-icon="inline-start" />生成继承建议</>}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {suggestions.map((sugg) => (
                  <div key={sugg.id} className="flex items-start justify-between rounded-md border p-3">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{SUGGESTION_TYPE_MAP[sugg.suggestion_type] ?? sugg.suggestion_type}</Badge>
                        <span className="text-sm">
                          {getSuggestionSummary(sugg.suggestions)}
                        </span>
                      </div>
                    </div>
                    {sugg.status === 'pending' ? (
                      <div className="flex gap-1 shrink-0">
                        <Button size="sm" variant="ghost" onClick={() => acceptSugg(sugg.id)}><ThumbsUp className="size-4" /></Button>
                        <Button size="sm" variant="ghost" onClick={() => setRejectSuggestionId(sugg.id)}><ThumbsDown className="size-4" /></Button>
                      </div>
                    ) : (
                      <Badge variant={sugg.status === 'accepted' ? 'default' : 'outline'}>
                        {sugg.status === 'accepted' ? '已采纳' : '已拒绝'}
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* IDP 打回原因 Dialog */}
      <Dialog open={!!rejectPlanId} onOpenChange={(o) => !o && setRejectPlanId(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>打回 IDP</DialogTitle></DialogHeader>
          <Textarea
            rows={3}
            value={rejectPlanReason}
            onChange={(e) => setRejectPlanReason(e.target.value)}
            placeholder="请写明需要员工补充或修改的内容..."
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRejectPlanId(null)}>取消</Button>
            <Button
              onClick={() => rejectPlanId && rejectTeamPlan({ id: rejectPlanId, comment: rejectPlanReason })}
              disabled={rejectPlanPending || !rejectPlanReason.trim()}
            >
              {rejectPlanPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
              确认打回
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 继承建议拒绝原因 Dialog */}
      <Dialog open={!!rejectSuggestionId} onOpenChange={(o) => !o && setRejectSuggestionId(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>拒绝原因</DialogTitle></DialogHeader>
          <Textarea rows={3} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="说明不采纳的原因..." />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRejectSuggestionId(null)}>取消</Button>
            <Button onClick={() => rejectSuggestionId && rejectSugg({ id: rejectSuggestionId, reason: rejectReason })} disabled={!rejectReason.trim()}>确认拒绝</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
