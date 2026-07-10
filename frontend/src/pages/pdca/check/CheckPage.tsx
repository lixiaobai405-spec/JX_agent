import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { CheckCircle2, RefreshCw } from 'lucide-react'
import {
  useCurrentUser, useCurrentPeriod, useCurrentGoal, useIndicators,
  useSelfAssessment, usePendingEvaluationTasks, useFinalResult, useGoalEvaluations,
} from '@/hooks'
import { checkApi } from '@/api/check'
import { hasInvalidScores, parseScoreInput, toScorePayload } from '@/lib/scores'
import { C_GRADE_RULES, C_GRADE_RULE_TEXT } from '@/lib/pdcaFeedback'

const GRADE_MAP: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  S: { label: 'S - 优秀', variant: 'default' },
  A: { label: 'A - 良好', variant: 'default' },
  B: { label: 'B - 合格', variant: 'secondary' },
  C: { label: 'C - 待改进', variant: 'destructive' },
}

export function CheckPage() {
  const { data: user } = useCurrentUser()
  const { data: period } = useCurrentPeriod()
  const { data: goal } = useCurrentGoal(period?.id)
  const { data: indicators } = useIndicators(goal?.id)
  const { data: selfAssessment, isLoading: saLoading } = useSelfAssessment(goal?.id)
  const { data: pendingTasks } = usePendingEvaluationTasks()
  const { data: finalResult } = useFinalResult(goal?.id)
  const { data: goalEvaluations } = useGoalEvaluations(goal?.id)
  const qc = useQueryClient()

  const [items, setItems] = useState<Record<string, { score: string; comment: string }>>({})
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [evalScores, setEvalScores] = useState<Record<string, { score: string; comment: string }>>({})

  const isManager = user?.role === 'manager' || user?.role === 'hr_admin' || user?.role === 'system_admin'
  const scorableIndicators = indicators?.filter(ind => !ind.redline)

  const { mutate: saveDraft, isPending: savePending } = useMutation({
    mutationFn: () => {
      if (hasInvalidScores(items)) {
        throw new Error('评分必须在 0-100 之间')
      }
      const parsed = toScorePayload(items)
      if (selfAssessment?.id) return checkApi.updateSelfAssessment(selfAssessment.id, parsed)
      return checkApi.createSelfAssessment(goal!.id, parsed)
    },
    onSuccess: () => { toast.success('草稿已保存'); qc.invalidateQueries({ queryKey: ['self-assessment', goal?.id] }) },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '保存失败')
    },
  })

  const { mutate: submitSA, isPending: submitPending } = useMutation({
    mutationFn: async () => {
      if (hasInvalidScores(items)) {
        throw new Error('评分必须在 0-100 之间')
      }
      if (!selfAssessment?.id) {
        const created = await checkApi.createSelfAssessment(goal!.id, toScorePayload(items))
        return checkApi.submitSelfAssessment(created.id)
      }
      return checkApi.submitSelfAssessment(selfAssessment.id)
    },
    onSuccess: () => {
      toast.success('自评已提交')
      qc.invalidateQueries({ queryKey: ['self-assessment', goal?.id] })
      qc.invalidateQueries({ queryKey: ['eval-tasks'] })
      qc.invalidateQueries({ queryKey: ['eval-tasks', 'pending'] })
      setConfirmOpen(false)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '提交失败')
    },
  })

  const { mutate: generateTasks, isPending: genTaskPending } = useMutation({
    mutationFn: () => checkApi.generateEvaluationTasks(goal!.id),
    onSuccess: () => {
      toast.success('评估任务已生成')
      qc.invalidateQueries({ queryKey: ['eval-tasks'] })
      qc.invalidateQueries({ queryKey: ['eval-tasks', 'pending'] })
      qc.invalidateQueries({ queryKey: ['self-assessment', goal?.id] })
    },
  })

  const { mutate: submitEval } = useMutation({
    mutationFn: ({ taskId, indicatorId }: { taskId: string; indicatorId: string }) => {
      const ev = evalScores[indicatorId]
      if (!ev || !Number.isFinite(Number(ev.score)) || Number(ev.score) < 0 || Number(ev.score) > 100) {
        throw new Error('评分必须在 0-100 之间')
      }
      return checkApi.submitEvaluation({ task_id: taskId, indicator_id: indicatorId, score: Number(ev.score), comment: ev.comment })
    },
    onSuccess: () => {
      toast.success('评分已提交')
      qc.invalidateQueries({ queryKey: ['eval-tasks'] })
      qc.invalidateQueries({ queryKey: ['eval-tasks', 'pending'] })
      qc.invalidateQueries({ queryKey: ['evaluations', goal?.id] })
      qc.invalidateQueries({ queryKey: ['final-result', goal?.id] })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : '评分提交失败')
    },
  })

  const { mutate: generateResult, isPending: resultPending } = useMutation({
    mutationFn: () => checkApi.generateFinalResult(goal!.id),
    onSuccess: () => {
      toast.success('最终结果已生成')
      qc.invalidateQueries({ queryKey: ['final-result', goal?.id] })
      qc.invalidateQueries({ queryKey: ['evaluations', goal?.id] })
    },
  })

  const { mutate: confirmResult, isPending: confirmPending } = useMutation({
    mutationFn: () => checkApi.confirmFinalResult(finalResult!.id),
    onSuccess: () => {
      toast.success('结果已确认')
      qc.invalidateQueries({ queryKey: ['final-result', goal?.id] })
      qc.invalidateQueries({ queryKey: ['evaluations', goal?.id] })
      qc.invalidateQueries({ queryKey: ['periods'] })
      qc.invalidateQueries({ queryKey: ['periods', 'current'] })
    },
  })

  if (!period || !goal) {
    return (
      <div className="flex flex-col gap-4 max-w-2xl">
        <h1 className="text-2xl font-semibold">C - 考核评估</h1>
        <p className="text-sm text-muted-foreground">结合自评、上级评分和定级规则生成最终绩效结果。</p>
        <Card><CardContent className="py-10 text-center text-muted-foreground">请先完成 P 和 D 阶段</CardContent></Card>
      </div>
    )
  }

  if (!period.d_phase_completed) {
    return (
      <div className="flex flex-col gap-4 max-w-2xl">
        <h1 className="text-2xl font-semibold">C - 考核评估</h1>
        <p className="text-sm text-muted-foreground">结合自评、上级评分和定级规则生成最终绩效结果。</p>
        <Card><CardContent className="py-10 text-center text-muted-foreground">D 阶段尚未完成，请联系经理标记完成后再进行考核评估</CardContent></Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold">C - 考核评估</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {period.name} · 结合自评、上级评分和定级规则生成最终绩效结果。
        </p>
      </div>

      {finalResult && (
        <Card className="border-primary/40">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex flex-col gap-0.5">
              <p className="font-medium">考核结果</p>
              {finalResult.adjustment_reason && <p className="text-xs text-muted-foreground">调整原因：{finalResult.adjustment_reason}</p>}
            </div>
            <div className="flex items-center gap-3">
              <Badge {...(GRADE_MAP[finalResult.final_grade] ?? { variant: 'secondary' as const })}>
                {GRADE_MAP[finalResult.final_grade]?.label ?? finalResult.final_grade}
              </Badge>
              {finalResult.status === 'pending' && (
                <Button size="sm" onClick={() => confirmResult()} disabled={confirmPending}>
                  {confirmPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                  确认结果
                </Button>
              )}
              {finalResult.status === 'confirmed' && <CheckCircle2 className="size-5 text-primary" />}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="flex flex-col gap-2 py-4">
          <p className="text-sm font-medium">定级说明</p>
          <p className="text-xs text-muted-foreground">{C_GRADE_RULE_TEXT}</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {C_GRADE_RULES.map((rule) => (
              <div key={rule.grade} className="rounded-md border px-3 py-2">
                <p className="text-sm font-semibold">{rule.grade}</p>
                <p className="text-xs text-muted-foreground">{rule.label} · {rule.range}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 自评 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-base">
            自我评估
            {selfAssessment?.status === 'submitted' && <Badge variant="secondary">已提交</Badge>}
            {selfAssessment?.status === 'draft' && <Badge variant="outline">草稿</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {saLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : selfAssessment?.status === 'submitted' ? (
            <div className="flex flex-col divide-y">
              {scorableIndicators?.map((ind) => {
                const item = selfAssessment.items[ind.id]
                return (
                  <div key={ind.id} className="flex items-center justify-between py-2.5 text-sm">
                    <span>{ind.name}</span>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{item?.score ?? '—'} 分</Badge>
                      {item?.comment && <span className="text-xs text-muted-foreground max-w-32 truncate">{item.comment}</span>}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <>
              <div className="flex flex-col gap-3">
                {scorableIndicators?.map((ind) => (
                  <div key={ind.id} className="flex flex-col gap-1.5">
                    <Label className="flex items-center gap-2">
                      {ind.name}
                      <span className="text-xs text-muted-foreground">权重 {Math.round(ind.weight * 100)}%</span>
                    </Label>
                    <div className="flex gap-2">
                      <Input type="number" min={0} max={100} placeholder="分数 (0-100)" className="w-36 shrink-0"
                        value={items[ind.id]?.score ?? selfAssessment?.items[ind.id]?.score ?? ''}
                        onChange={(e) => setItems((prev) => ({
                          ...prev,
                          [ind.id]: {
                            ...prev[ind.id],
                            score: parseScoreInput(e.target.value),
                          },
                        }))}
                      />
                      <Input placeholder="评价说明..."
                        value={items[ind.id]?.comment ?? selfAssessment?.items[ind.id]?.comment ?? ''}
                        onChange={(e) => setItems((prev) => ({ ...prev, [ind.id]: { ...prev[ind.id], comment: e.target.value } }))}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => saveDraft()} disabled={savePending}>保存草稿</Button>
                <Button size="sm" onClick={() => setConfirmOpen(true)}>提交自评</Button>
              </div>
              <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
                <DialogContent>
                  <DialogHeader><DialogTitle>确认提交自评</DialogTitle></DialogHeader>
                  <p className="text-sm text-muted-foreground py-2">提交后无法修改，请确认评分无误。</p>
                  <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => setConfirmOpen(false)}>取消</Button>
                    <Button onClick={() => submitSA()} disabled={submitPending}>
                      {submitPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                      确认提交
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </>
          )}
        </CardContent>
      </Card>

      {/* 员工视角：等待评分 + 生成最终结果 */}
      {!isManager && selfAssessment?.status === 'submitted' && !finalResult && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">上级评分进度</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {scorableIndicators && scorableIndicators.length > 0 ? (
              <div className="flex flex-col divide-y">
                {scorableIndicators.map((ind) => {
                  const eval_ = goalEvaluations?.find(e => e.indicator_id === ind.id)
                  return (
                    <div key={ind.id} className="flex items-center justify-between py-2 text-sm">
                      <span>{ind.name}</span>
                      {eval_ ? (
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{eval_.score} 分</Badge>
                          {eval_.comment && <span className="text-xs text-muted-foreground max-w-32 truncate">{eval_.comment}</span>}
                        </div>
                      ) : (
                        <Badge variant="outline" className="text-muted-foreground">待评分</Badge>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : null}
            <div className="flex items-center gap-3">
              {(goalEvaluations?.length ?? 0) > 0 ? (
                <Button onClick={() => generateResult()} disabled={resultPending}>
                  {resultPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                  生成最终结果
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">等待上级完成评分后可生成最终结果</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 经理评估 */}
      {isManager && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between text-base">
              上级评估
              {!pendingTasks?.length && goal && (
                <Button variant="outline" size="sm" onClick={() => generateTasks()} disabled={genTaskPending}>生成评估任务</Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {pendingTasks?.length ? (
              <>
                {pendingTasks.map((task) => {
                  const ind = indicators?.find((i) => i.id === task.indicator_id)
                  return (
                    <div key={task.id} className="flex flex-col gap-2 rounded-md border p-3">
                      <p className="text-sm font-medium">{ind?.name ?? task.indicator_id}</p>
                      <div className="flex gap-2">
                        <Input type="number" min={0} max={100} placeholder="分数 (0-100)" className="w-36 shrink-0"
                          value={evalScores[task.indicator_id]?.score ?? ''}
                          onChange={(e) => setEvalScores((prev) => ({
                            ...prev,
                            [task.indicator_id]: {
                              ...prev[task.indicator_id],
                              score: parseScoreInput(e.target.value),
                            },
                          }))}
                        />
                        <Input placeholder="评价意见..."
                          value={evalScores[task.indicator_id]?.comment ?? ''}
                          onChange={(e) => setEvalScores((prev) => ({ ...prev, [task.indicator_id]: { ...prev[task.indicator_id], comment: e.target.value } }))}
                        />
                        <Button size="sm" onClick={() => submitEval({ taskId: task.id, indicatorId: task.indicator_id })}>提交</Button>
                      </div>
                    </div>
                  )
                })}
                {!finalResult && (
                  <Button className="self-start mt-2" onClick={() => generateResult()} disabled={resultPending}>
                    {resultPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    生成最终结果
                  </Button>
                )}
              </>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-muted-foreground">
                  {selfAssessment?.status === 'submitted' ? '点击上方生成评估任务' : '等待员工提交自评'}
                </p>
                {(goalEvaluations?.length ?? 0) > 0 && !finalResult && (
                  <Button className="self-start" onClick={() => generateResult()} disabled={resultPending}>
                    {resultPending && <RefreshCw data-icon="inline-start" className="animate-spin" />}
                    生成最终结果
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
