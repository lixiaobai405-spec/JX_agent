import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { AlertCircle, CalendarPlus, ChevronDown, ChevronRight, MessageSquare, ClipboardCheck, CheckCircle2, Pencil, XCircle } from 'lucide-react'
import {
  useCurrentUser, useSubordinates,
  useTeamCoachingRequests, useAllUsers, useTeamOpenPeriods,
  useMemberGoal, useIndicators, useLatestDiagnostic, useIndicatorCheckins,
  useSelfAssessment, useEvaluationTasks, useGoalEvaluations, useTeamPlans,
} from '@/hooks'
import { periodsApi, doApi } from '@/api/do'
import { checkApi } from '@/api/check'
import { actionApi } from '@/api/action'
import { usersApi } from '@/api/users'
import { organizationsApi } from '@/api/organizations'
import { isScoreInRange, parseScoreInput } from '@/lib/scores'
import { formatCheckinValue } from '@/lib/checkins'
import { formatAchievementRate, toAchievementProgress } from '@/lib/performance'
import { getDiagnosticIndicatorStatus } from '@/lib/pdcaFeedback'
import { toDateInputValue, toPeriodEndIso, toPeriodStartIso } from '@/lib/periodDates'
import { TrafficLight } from '@/components/shared/TrafficLight'
import type { Period, CoachingRequest, DiagnosticReport, Indicator, Goal } from '@/types'

type ApiError = {
  response?: {
    data?: {
      error_code?: string
      message?: string
      detail?: string
    }
  }
  message?: string
}

function getErrorMessage(error: unknown) {
  const err = error as ApiError
  return err.response?.data?.message ?? err.response?.data?.detail ?? err.message ?? '操作失败'
}

function getErrorCode(error: unknown) {
  return (error as ApiError).response?.data?.error_code
}

function emptyToUndefined(value?: string) {
  const trimmed = value?.trim()
  return trimmed ? trimmed : undefined
}

// ─── Complete D Phase Button ──────────────────────────────────────────────

function CompleteDPhaseButton({ periodId }: { periodId: string }) {
  const qc = useQueryClient()
  const { mutate, isPending } = useMutation({
    mutationFn: () => periodsApi.completeDPhase(periodId),
    onSuccess: () => {
      toast.success('D 阶段已标记完成')
      qc.invalidateQueries({ queryKey: ['periods'] })
    },
    onError: (error) => toast.error('操作失败：' + getErrorMessage(error)),
  })
  return (
    <Button size="sm" variant="outline" onClick={() => mutate()} disabled={isPending}>
      {isPending ? '处理中...' : '完成 D 阶段'}
    </Button>
  )
}

// ─── Period Creation Dialog ────────────────────────────────────────────────

const periodSchema = z.object({
  name: z.string().min(1, '请填写考核期名称'),
  start_date: z.string().min(1, '请选择开始日期'),
  end_date: z.string().min(1, '请选择结束日期'),
}).refine((d) => d.end_date > d.start_date, { message: '结束日期必须晚于开始日期', path: ['end_date'] })

type PeriodForm = z.infer<typeof periodSchema>

function CreatePeriodDialog({ userId, userName, open, onOpenChange }: {
  userId: string; userName: string; open: boolean; onOpenChange: (v: boolean) => void
}) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PeriodForm>({
    resolver: zodResolver(periodSchema),
  })

  const { mutate, isPending } = useMutation({
    mutationFn: async (data: PeriodForm) => {
      const period = await periodsApi.create({
        user_id: userId,
        name: data.name,
        start_date: toPeriodStartIso(data.start_date),
        end_date: toPeriodEndIso(data.end_date),
      })
      await periodsApi.updateStatus(period.id, 'open')
      return period
    },
    onSuccess: () => {
      toast.success('考核期已创建并开放')
      qc.invalidateQueries({ queryKey: ['periods'] })
      qc.invalidateQueries({ queryKey: ['periods', 'open'] })
      qc.invalidateQueries({ queryKey: ['periods', 'draft'] })
      reset()
      onOpenChange(false)
    },
    onError: (error) => {
      const code = getErrorCode(error)
      if (code === 'PERIOD_002') {
        toast.error('该用户已有开放的考核期')
      } else {
        toast.error('创建失败：' + getErrorMessage(error))
      }
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>为 {userName} 创建考核期</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((d) => mutate(d))} className="flex flex-col gap-4 pt-2">
          <div className="flex flex-col gap-1.5">
            <Label>考核期名称</Label>
            <Input {...register('name')} placeholder="如：2026年7月绩效周期" />
            {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label>开始日期</Label>
              <Input type="date" {...register('start_date')} />
              {errors.start_date && <p className="text-xs text-destructive">{errors.start_date.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>结束日期</Label>
              <Input type="date" {...register('end_date')} />
              {errors.end_date && <p className="text-xs text-destructive">{errors.end_date.message}</p>}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>取消</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '创建中...' : '创建并开放'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function EditPeriodDialog({ period, userName, open, onOpenChange }: {
  period: Period
  userName: string
  open: boolean
  onOpenChange: (value: boolean) => void
}) {
  const qc = useQueryClient()
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PeriodForm>({
    resolver: zodResolver(periodSchema),
  })

  useEffect(() => {
    if (!open) return
    reset({
      name: period.name,
      start_date: toDateInputValue(period.start_date),
      end_date: toDateInputValue(period.end_date),
    })
  }, [open, period, reset])

  const { mutate, isPending } = useMutation({
    mutationFn: (data: PeriodForm) => periodsApi.update(period.id, {
      name: data.name,
      start_date: toPeriodStartIso(data.start_date),
      end_date: toPeriodEndIso(data.end_date),
    }),
    onSuccess: () => {
      toast.success('考核期已更新')
      qc.invalidateQueries({ queryKey: ['periods'] })
      qc.invalidateQueries({ queryKey: ['periods', 'open'] })
      qc.invalidateQueries({ queryKey: ['periods', 'draft'] })
      qc.invalidateQueries({ queryKey: ['periods', 'current'] })
      onOpenChange(false)
    },
  })

  const canEdit = period.status === 'draft' || period.status === 'open'

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!isPending) onOpenChange(nextOpen) }}>
      <DialogContent>
        <DialogHeader><DialogTitle>编辑 {userName} 的考核期</DialogTitle></DialogHeader>
        {!canEdit ? (
          <p className="text-sm text-muted-foreground">只有草稿或进行中的考核期可以编辑。</p>
        ) : (
          <form onSubmit={handleSubmit((data) => mutate(data))} className="flex flex-col gap-4 pt-2">
            <div className="flex flex-col gap-1.5">
              <Label>考核期名称</Label>
              <Input {...register('name')} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <Label>开始日期</Label>
                <Input type="date" {...register('start_date')} />
                {errors.start_date && <p className="text-xs text-destructive">{errors.start_date.message}</p>}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>结束日期</Label>
                <Input type="date" {...register('end_date')} />
                {errors.end_date && <p className="text-xs text-destructive">{errors.end_date.message}</p>}
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2 pt-1">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>取消</Button>
              <Button type="submit" disabled={isPending}>
                {isPending ? '保存中...' : '保存修改'}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ─── User Creation Dialog ──────────────────────────────────────────────────

const userSchema = z.object({
  username: z.string().min(1, '请填写用户名'),
  full_name: z.string().min(1, '请填写姓名'),
  email: z.string().email('请填写有效邮箱'),
  password: z.string().min(6, '密码至少6位'),
  role: z.string().min(1),
  department_id: z.string().optional(),
  position_id: z.string().optional(),
  manager_id: z.string().optional(),
  phone: z.string().optional(),
})

type UserForm = z.infer<typeof userSchema>

function CreateUserDialog({ open, onOpenChange }: {
  open: boolean; onOpenChange: (v: boolean) => void
}) {
  const qc = useQueryClient()
  const { data: allUsers } = useAllUsers({})
  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: organizationsApi.listDepartments,
  })
  const { data: positions = [] } = useQuery({
    queryKey: ['positions'],
    queryFn: organizationsApi.listPositions,
  })
  const { register, handleSubmit, reset, formState: { errors } } = useForm<UserForm>({
    resolver: zodResolver(userSchema),
    defaultValues: {
      role: 'employee',
      department_id: '',
      position_id: '',
      manager_id: '',
      phone: '',
    },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (data: UserForm) => usersApi.create({
      username: data.username,
      full_name: data.full_name,
      email: data.email,
      password: data.password,
      role: data.role,
      department_id: emptyToUndefined(data.department_id),
      position_id: emptyToUndefined(data.position_id),
      manager_id: emptyToUndefined(data.manager_id),
      phone: emptyToUndefined(data.phone),
    }),
    onSuccess: () => {
      toast.success('用户创建成功')
      qc.invalidateQueries({ queryKey: ['users'] })
      reset()
      onOpenChange(false)
    },
    onError: (error) => {
      toast.error('创建失败：' + getErrorMessage(error))
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>创建新用户</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((d: UserForm) => mutate(d))} className="flex flex-col gap-4 pt-2">
          <div className="flex flex-col gap-1.5">
            <Label>用户名</Label>
            <Input {...register('username')} placeholder="登录用户名" />
            {errors.username && <p className="text-xs text-destructive">{errors.username.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>姓名</Label>
            <Input {...register('full_name')} placeholder="真实姓名" />
            {errors.full_name && <p className="text-xs text-destructive">{errors.full_name.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>邮箱</Label>
            <Input type="email" {...register('email')} placeholder="user@example.com" />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>密码</Label>
            <Input type="password" {...register('password')} placeholder="至少6位" />
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>角色</Label>
            <select {...register('role')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="employee">员工</option>
              <option value="manager">经理</option>
              <option value="hr_admin">HR管理员</option>
              <option value="system_admin">系统管理员</option>
            </select>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <Label>所属部门（可选）</Label>
              <select {...register('department_id')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="">未指定</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>{dept.name}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>岗位（可选）</Label>
              <select {...register('position_id')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                <option value="">未指定</option>
                {positions.map((position) => (
                  <option key={position.id} value={position.id}>{position.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>直属上级（可选）</Label>
            <select {...register('manager_id')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="">无</option>
              {(allUsers ?? []).map((u) => (
                <option key={u.id} value={u.id}>{u.full_name} ({u.username})</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>手机号（可选）</Label>
            <Input {...register('phone')} placeholder="手机号" />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>取消</Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? '创建中...' : '创建用户'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Indicator mini-row (inside expanded section) ─────────────────────────

function IndicatorMiniRow({ indicator, diagnostic }: { indicator: Indicator; diagnostic?: DiagnosticReport | null }) {
  const { data: checkins } = useIndicatorCheckins(indicator.id)
  const actualValue = checkins?.[0]?.actual_value
  const actual = typeof actualValue?.value === 'number' ? actualValue.value : null
  const actualDisplay = actualValue ? formatCheckinValue(actualValue, indicator.unit) : null
  const pct = actual != null && indicator.target_value && !indicator.redline && indicator.indicator_type !== 'qualitative'
    ? (indicator.direction === 'positive'
        ? actual / indicator.target_value
        : indicator.target_value / actual) * 100
    : null
  const status = getDiagnosticIndicatorStatus(diagnostic, indicator)
  const targetDisplay = indicator.target_display ?? (
    indicator.target_value != null ? `${indicator.target_value}${indicator.unit ?? ''}` : '—'
  )

  return (
    <div className="grid gap-1 border-b py-2 text-sm last:border-0 sm:grid-cols-[minmax(0,1fr)_auto_auto_auto] sm:items-center sm:gap-x-4">
      <span className="flex min-w-0 flex-wrap items-center gap-1.5">
        <span className="break-words">{indicator.name}</span>
        {indicator.redline && <Badge variant="destructive" className="text-xs py-0">否决</Badge>}
        <TrafficLight status={status} />
      </span>
      <span className="text-muted-foreground sm:text-right">目标 {targetDisplay}</span>
      <span className="font-medium sm:text-right">{actualDisplay ? `实际 ${actualDisplay}` : '未打卡'}</span>
      <span className="sm:text-right">达成率 {formatAchievementRate(pct)}</span>
    </div>
  )
}

// ─── Coaching request item with inline respond ────────────────────────────

const urgencyLabel: Record<string, string> = { low: '低', normal: '一般', high: '紧急' }
const statusLabel: Record<string, string> = { pending: '待处理', accepted: '已接受', completed: '已完成', rejected: '已拒绝' }
const statusVariant: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  pending: 'destructive', accepted: 'default', completed: 'secondary', rejected: 'outline',
}

function CoachingRequestItem({ req }: { req: CoachingRequest }) {
  const [responding, setResponding] = useState(false)
  const [notes, setNotes] = useState('')
  const qc = useQueryClient()

  const { mutate: respond, isPending, variables: responseStatus } = useMutation({
    mutationFn: (status: 'accepted' | 'rejected') =>
      doApi.updateCoachingStatus(req.id, status, notes || undefined),
    onSuccess: () => {
      toast.success('已响应辅导请求')
      qc.invalidateQueries({ queryKey: ['coaching'] })
      setResponding(false)
    },
  })

  return (
    <div className="rounded-md border p-3 flex flex-col gap-2 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <MessageSquare className="size-3.5 text-muted-foreground shrink-0" />
            <span className="font-medium">{req.request_reason || '（未填写原因）'}</span>
          </div>
          <div className="flex gap-2 text-xs text-muted-foreground pl-5">
            <span>紧急程度：{urgencyLabel[req.urgency_level] ?? req.urgency_level}</span>
            <span>{new Date(req.created_at).toLocaleDateString('zh-CN')}</span>
          </div>
          {req.notes && (
            <p className="text-xs text-muted-foreground pl-5 mt-0.5">回复：{req.notes}</p>
          )}
        </div>
        <Badge variant={statusVariant[req.status] ?? 'outline'} className="shrink-0 text-xs">
          {statusLabel[req.status] ?? req.status}
        </Badge>
      </div>

      {req.status === 'pending' && (
        responding ? (
          <div className="flex flex-col gap-2 pl-5">
            <Textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="回复内容（可选）..."
              className="text-xs"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => respond('accepted')} disabled={isPending}>
                {isPending && responseStatus === 'accepted' ? '处理中...' : '接受'}
              </Button>
              <Button size="sm" variant="outline" onClick={() => respond('rejected')} disabled={isPending}>
                {isPending && responseStatus === 'rejected' ? '处理中...' : '拒绝'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setResponding(false)} disabled={isPending}>取消</Button>
            </div>
          </div>
        ) : (
          <div className="pl-5">
            <Button size="sm" variant="outline" onClick={() => setResponding(true)}>响应请求</Button>
          </div>
        )
      )}
    </div>
  )
}

// ─── C-phase evaluation scoring section ───────────────────────────────────

function EvalScoringSection({ goal, indicators: allIndicators }: { goal: Goal; indicators: Indicator[] }) {
  const indicators = allIndicators.filter(ind => !ind.redline)
  const qc = useQueryClient()
  const { data: selfAssessment } = useSelfAssessment(goal.id)
  const { data: allTasks } = useEvaluationTasks()
  const { data: evaluations } = useGoalEvaluations(goal.id)

  // Tasks that belong to this goal
  const goalTasks = (allTasks ?? []).filter(t => t.goal_id === goal.id)
  // Map indicator_id → task_id (pending tasks only)
  const taskByIndicator = Object.fromEntries(
    goalTasks.filter(t => t.status === 'pending').map(t => [t.indicator_id, t.id])
  )
  // Map indicator_id → submitted evaluation
  const evalByIndicator = Object.fromEntries(
    (evaluations ?? []).map(e => [e.indicator_id, e])
  )

  const tasksGenerated = goalTasks.length > 0
  const allScored = tasksGenerated && indicators.every(ind => !!evalByIndicator[ind.id])

  // Local score inputs: indicator_id → { score, comment }
  const [inputs, setInputs] = useState<Record<string, { score: string; comment: string }>>({})
  const setInput = (indId: string, field: 'score' | 'comment', val: string) =>
    setInputs(prev => ({ ...prev, [indId]: { ...prev[indId], [field]: val } }))

  const { mutate: generateTasks, isPending: generating } = useMutation({
    mutationFn: () => checkApi.generateEvaluationTasks(goal.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['eval-tasks'] })
    },
  })

  const { mutate: submitAll, isPending: submitting } = useMutation({
    mutationFn: async () => {
      const toSubmit = indicators.filter(ind => taskByIndicator[ind.id] && !evalByIndicator[ind.id])
      for (const ind of toSubmit) {
        const inp = inputs[ind.id]
        if (!isScoreInRange(inp?.score ?? '')) throw new Error(`请为指标「${ind.name}」填写 0-100 之间的分数`)
        const score = Number(inp.score)
        await checkApi.submitEvaluation({
          task_id: taskByIndicator[ind.id],
          indicator_id: ind.id,
          score,
          comment: inp?.comment || undefined,
        })
      }
    },
    onSuccess: () => {
      toast.success('评分提交成功')
      qc.invalidateQueries({ queryKey: ['eval-tasks'] })
      qc.invalidateQueries({ queryKey: ['evaluations', goal.id] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const selfSubmitted = selfAssessment?.status === 'submitted'

  // Auto-generate tasks when self-assessment is submitted
  useEffect(() => {
    if (selfSubmitted && !tasksGenerated && !generating) {
      generateTasks()
    }
  }, [selfSubmitted, tasksGenerated, generating, generateTasks, goal.id])

  if (!selfSubmitted) {
    return (
      <div className="text-sm text-muted-foreground flex items-center gap-2">
        <ClipboardCheck className="size-4" />
        员工尚未提交自评，评分功能暂不可用
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">C 阶段评分</p>
        {allScored && (
          <Badge variant="secondary" className="text-xs">全部已评</Badge>
        )}
      </div>

      <div className="overflow-x-auto rounded-md border">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left px-3 py-2 font-medium text-muted-foreground">指标</th>
              <th className="text-center px-3 py-2 font-medium text-muted-foreground w-20">权重</th>
              <th className="text-center px-3 py-2 font-medium text-muted-foreground w-24">员工自评</th>
              <th className="px-3 py-2 font-medium text-muted-foreground">经理评分</th>
            </tr>
          </thead>
          <tbody>
            {indicators.map(ind => {
              const selfItem = selfAssessment?.items?.[ind.id] as { score: number; comment: string } | undefined
              const existingEval = evalByIndicator[ind.id]
              const hasPendingTask = !!taskByIndicator[ind.id]

              return (
                <tr key={ind.id} className="border-t">
                  <td className="px-3 py-2">
                    <span>{ind.name}</span>
                    {ind.redline && <Badge variant="destructive" className="ml-1.5 text-xs py-0">否决</Badge>}
                    {selfItem?.comment && (
                      <p className="text-xs text-muted-foreground mt-0.5">员工备注：{selfItem.comment}</p>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center text-muted-foreground">
                    {formatAchievementRate(ind.weight * 100)}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {selfItem != null ? (
                      <span className="font-medium">{selfItem.score}</span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {existingEval ? (
                      <div className="flex flex-col gap-0.5">
                        <span className="font-medium text-green-700">{existingEval.score} 分</span>
                        {existingEval.comment && <span className="text-xs text-muted-foreground">{existingEval.comment}</span>}
                      </div>
                    ) : hasPendingTask ? (
                      <div className="flex gap-2 items-center">
                        <Input
                          type="number"
                          min={0}
                          max={100}
                          className="h-7 w-36 shrink-0 text-sm"
                          placeholder="分数 (0-100)"
                          value={inputs[ind.id]?.score ?? ''}
                          onChange={e => setInput(ind.id, 'score', parseScoreInput(e.target.value))}
                        />
                        <Input
                          className="h-7 text-sm"
                          placeholder="评语（可选）"
                          value={inputs[ind.id]?.comment ?? ''}
                          onChange={e => setInput(ind.id, 'comment', e.target.value)}
                        />
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        {tasksGenerated ? '已完成' : '待生成任务'}
                      </span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {tasksGenerated && !allScored && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => submitAll()} disabled={submitting}>
            {submitting ? '提交中...' : '提交所有评分'}
          </Button>
        </div>
      )}
    </div>
  )
}

// ─── IDP Review Section ───────────────────────────────────────────────────

function IDPReviewSection({ memberId, period }: { memberId: string; period: Period }) {
  const qc = useQueryClient()
  const { data: teamPlans } = useTeamPlans()
  const pendingPlan = teamPlans?.find(
    (p) => p.user_id === memberId && p.status === 'reviewed'
  )
  const approvedPlan = teamPlans?.find(
    (p) => p.user_id === memberId && p.status === 'approved'
  )

  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectComment, setRejectComment] = useState('')
  const [closingPeriod, setClosingPeriod] = useState(false)

  const { mutate: approve, isPending: approvePending } = useMutation({
    mutationFn: () => actionApi.approvePlan(pendingPlan!.id, true),
    onSuccess: () => {
      toast.success('IDP 已通过审批')
      qc.invalidateQueries({ queryKey: ['team-plans'] })
    },
  })

  const { mutate: reject, isPending: rejectPending } = useMutation({
    mutationFn: () => actionApi.approvePlan(pendingPlan!.id, false, rejectComment),
    onSuccess: () => {
      toast.success('已打回，员工可修改后重新提交')
      qc.invalidateQueries({ queryKey: ['team-plans'] })
      setRejectOpen(false)
      setRejectComment('')
    },
  })

  const { mutate: closePeriod, isPending: closePending } = useMutation({
    mutationFn: () => periodsApi.updateStatus(period.id, 'closed'),
    onSuccess: () => {
      toast.success('考核期已结束')
      qc.invalidateQueries({ queryKey: ['periods', 'open'] })
      setClosingPeriod(false)
    },
  })

  if (!pendingPlan && !approvedPlan) return null

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">A 阶段 · IDP 审阅</p>

      {pendingPlan && (
        <div className="rounded-md border p-3 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Badge variant="secondary">待审批</Badge>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">发展目标</p>
              <p>{(pendingPlan.goals as { text: string }).text}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-0.5">行动计划</p>
              <p>{(pendingPlan.actions as { text: string }).text}</p>
            </div>
          </div>
          {pendingPlan.ai_suggestions && (
            <div className="text-xs text-muted-foreground bg-muted/50 rounded px-2.5 py-1.5">
              AI 评估：{(pendingPlan.ai_suggestions as { review: string }).review}
            </div>
          )}
          <div className="flex gap-2">
            <Button size="sm" onClick={() => approve()} disabled={approvePending || rejectPending}>
              <CheckCircle2 className="size-3.5 mr-1" />
              {approvePending ? '审批中...' : '同意'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setRejectOpen(true)} disabled={approvePending || rejectPending}>
              <XCircle className="size-3.5 mr-1" />
              打回修改
            </Button>
          </div>
        </div>
      )}

      {approvedPlan && !pendingPlan && (
        <div className="flex items-center justify-between rounded-md border p-3">
          <div className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="size-4 text-primary" />
            <span>IDP 已通过审批</span>
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setClosingPeriod(true)}
          >
            结束考核期
          </Button>
        </div>
      )}

      {/* Reject dialog */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>打回 IDP — 请填写反馈意见</DialogTitle></DialogHeader>
          <Textarea
            rows={3}
            value={rejectComment}
            onChange={(e) => setRejectComment(e.target.value)}
            placeholder="说明需要修改的方向或不足之处..."
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRejectOpen(false)} disabled={rejectPending}>取消</Button>
            <Button onClick={() => reject()} disabled={rejectPending || !rejectComment.trim()}>
              {rejectPending ? '提交中...' : '确认打回'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Close period confirm dialog */}
      <Dialog open={closingPeriod} onOpenChange={setClosingPeriod}>
        <DialogContent>
          <DialogHeader><DialogTitle>确认结束考核期</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground py-2">
            结束后该考核期将关闭，员工可在下一考核期继续。此操作不可撤销。
          </p>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setClosingPeriod(false)} disabled={closePending}>取消</Button>
            <Button variant="destructive" onClick={() => closePeriod()} disabled={closePending}>
              {closePending ? '处理中...' : '确认结束'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ─── Expanded detail for a member ─────────────────────────────────────────

function MemberExpandedDetail({
  memberId, period, allCoaching, isAdmin, canManage, onCreatePeriod, onEditPeriod,
}: {
  memberId: string
  period: Period | undefined
  allCoaching: CoachingRequest[]
  isAdmin: boolean
  canManage: boolean
  onCreatePeriod: () => void
  onEditPeriod: () => void
}) {
  const { data: goal, isLoading: goalLoading } = useMemberGoal(period?.id, memberId)
  const { data: indicators, isLoading: indLoading } = useIndicators(goal?.id)
  const { data: diagnostic } = useLatestDiagnostic(goal?.id)

  // Coaching requests filtered to the current period's goal
  const memberCoaching = allCoaching.filter(r => r.requester_id === memberId && r.goal_id === (goal?.id ?? null))

  if (!period) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm text-muted-foreground">
        <span>暂无草稿或进行中的考核期</span>
        {isAdmin && (
          <Button variant="outline" size="sm" onClick={onCreatePeriod}>
            <CalendarPlus className="size-3.5 mr-1" />
            创建考核期
          </Button>
        )}
      </div>
    )
  }

  if (goalLoading || indLoading) {
    return <div className="px-4 py-3 flex flex-col gap-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-6 w-full" />)}</div>
  }

  if (!goal) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm text-muted-foreground">
        <span>{period.status === 'draft' ? '考核期仍为草稿，尚未确认绩效目标' : '考核期已开放，尚未创建绩效目标（P 阶段未完成）'}</span>
        {canManage && (
          <Button variant="outline" size="sm" onClick={onEditPeriod}>
            <Pencil className="size-3.5 mr-1" />
            编辑考核期
          </Button>
        )}
      </div>
    )
  }

  return (
    <div className="px-4 py-3 flex flex-col gap-4">
      {/* Indicators */}
      {indicators && indicators.length > 0 ? (
        <div className="rounded-md border px-3 py-1">
          {indicators.map(ind => <IndicatorMiniRow key={ind.id} indicator={ind} diagnostic={diagnostic} />)}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">暂无指标数据</p>
      )}

      {/* Diagnostic summary */}
      {diagnostic && (
        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span>
            加权达成率：
            <span className="font-semibold text-foreground ml-1">
              {formatAchievementRate(diagnostic.weighted_achievement_rate)}
            </span>
          </span>
          {diagnostic.weighted_achievement_rate != null && (
            <Progress value={toAchievementProgress(diagnostic.weighted_achievement_rate)} className="h-2 w-32" />
          )}
          {diagnostic.progress_deviation != null && (
            <span className={diagnostic.progress_deviation < 0 ? 'text-destructive' : 'text-green-600'}>
              进度偏差：{diagnostic.progress_deviation > 0 ? '+' : ''}{formatAchievementRate(diagnostic.progress_deviation)}
            </span>
          )}
        </div>
      )}

      {/* C-phase evaluation scoring */}
      {indicators && indicators.length > 0 && (
        <EvalScoringSection goal={goal} indicators={indicators} />
      )}

      {/* A-phase IDP review */}
      <IDPReviewSection memberId={memberId} period={period!} />

      {/* Coaching requests */}
      {memberCoaching.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">辅导请求</p>
          {memberCoaching.map(req => <CoachingRequestItem key={req.id} req={req} />)}
        </div>
      )}

      {/* Admin actions */}
      {(isAdmin || canManage) && (
        <div className="flex flex-wrap gap-2">
          {period && !period.d_phase_completed && (
            <CompleteDPhaseButton periodId={period.id} />
          )}
          {canManage && (period.status === 'draft' || period.status === 'open') && (
            <Button size="sm" variant="ghost" onClick={onEditPeriod}>
              <Pencil className="size-3.5 mr-1" />
              编辑考核期
            </Button>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Single member card row ────────────────────────────────────────────────

function MemberCard({
  member, period, pendingCoaching, allCoaching, isAdmin, canManage, onCreatePeriod, onEditPeriod,
}: {
  member: { id: string; full_name: string; username: string; position_name?: string; department_name?: string; is_direct?: boolean; level?: number; role?: string }
  period: Period | undefined
  pendingCoaching: CoachingRequest[]
  allCoaching: CoachingRequest[]
  isAdmin: boolean
  canManage: boolean
  onCreatePeriod: () => void
  onEditPeriod: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()

  return (
    <div className="rounded-lg border bg-card">
      {/* Row header */}
      <div className="flex flex-col sm:flex-row sm:items-stretch">
        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-4 py-3 text-left transition-colors hover:bg-muted/40"
          onClick={() => setExpanded(v => !v)}
          aria-expanded={expanded}
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="break-words text-sm font-medium">{member.full_name}</span>
              {member.is_direct && <Badge variant="secondary" className="text-xs">直属</Badge>}
              {member.position_name && <span className="text-xs text-muted-foreground">{member.position_name}</span>}
              {member.department_name && <span className="text-xs text-muted-foreground">· {member.department_name}</span>}
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-2">
              {period
                ? <Badge variant="outline" className="max-w-full text-xs">{period.status === 'draft' ? '草稿' : '考核中'} · <span className="truncate">{period.name}</span></Badge>
                : <Badge variant="outline" className="text-xs text-muted-foreground">无考核期</Badge>
              }
              {pendingCoaching.length > 0 && (
                <Badge variant="destructive" className="text-xs">辅导 {pendingCoaching.length}</Badge>
              )}
              {isAdmin && member.role && (
                <Badge variant="outline" className="text-xs">{member.role}</Badge>
              )}
              {!isAdmin && member.level != null && (
                <Badge variant="outline" className="text-xs">L{member.level + 1}</Badge>
              )}
            </div>
          </div>
          {expanded ? <ChevronDown className="size-4 shrink-0 text-muted-foreground" /> : <ChevronRight className="size-4 shrink-0 text-muted-foreground" />}
        </button>
        <div className="flex shrink-0 items-center justify-end gap-1 px-3 pb-3 sm:py-3">
          {period && canManage && (period.status === 'draft' || period.status === 'open') && (
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`编辑 ${member.full_name} 的考核期`}
              title="编辑考核期"
              onClick={onEditPeriod}
            >
              <Pencil />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => navigate(`/management/team/${member.id}`)}
          >
            详情
          </Button>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t">
          <MemberExpandedDetail
            memberId={member.id}
            period={period}
            allCoaching={allCoaching}
            isAdmin={isAdmin}
            canManage={canManage}
            onCreatePeriod={onCreatePeriod}
            onEditPeriod={onEditPeriod}
          />
        </div>
      )}
    </div>
  )
}

// ─── Main page ─────────────────────────────────────────────────────────────

export function ManagementPage() {
  const { data: currentUser } = useCurrentUser()
  const isAdmin = currentUser?.role === 'hr_admin' || currentUser?.role === 'system_admin'

  const { data: subordinates, isLoading: subLoading } = useSubordinates(
    !isAdmin ? currentUser?.id : undefined
  )
  const { data: allUsers, isLoading: usersLoading } = useAllUsers(
    isAdmin ? {} : undefined
  )
  const isLoading = isAdmin ? usersLoading : subLoading

  const { data: openTeamPeriods } = useTeamOpenPeriods()
  const { data: draftTeamPeriods } = useQuery({
    queryKey: ['periods', 'draft'],
    queryFn: () => periodsApi.listByStatus('draft'),
  })
  const { data: pendingEvalSummary } = useQuery({
    queryKey: ['eval-tasks', 'pending-count'],
    queryFn: checkApi.pendingEvaluationTaskCount,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  })
  const { data: coachingRequests } = useTeamCoachingRequests()

  const [search, setSearch] = useState('')
  const [directOnly, setDirectOnly] = useState(false)
  const [createTarget, setCreateTarget] = useState<{ id: string; name: string } | null>(null)
  const [editTarget, setEditTarget] = useState<{ period: Period; userName: string } | null>(null)
  const [createUserOpen, setCreateUserOpen] = useState(false)
  const teamPeriods = [...(openTeamPeriods ?? []), ...(draftTeamPeriods ?? [])]

  const members: Array<{ id: string; full_name: string; username: string; position_name?: string; department_name?: string; is_direct?: boolean; level?: number; role?: string }> = isAdmin
    ? (allUsers ?? []).map((u) => ({
        id: u.id,
        full_name: u.full_name ?? u.username,
        username: u.username,
        position_name: u.position_name ?? undefined,
        department_name: u.department_name ?? undefined,
        role: u.role,
      }))
    : (subordinates ?? []).map((s) => ({
        id: s.id,
        full_name: s.full_name,
        username: s.username,
        position_name: s.position_name ?? undefined,
        department_name: s.department_name ?? undefined,
        is_direct: s.is_direct,
        level: s.level,
      }))

  const filtered = members.filter(
    (m) =>
      (!directOnly || m.is_direct) &&
      (m.full_name.includes(search) || m.username.includes(search))
  )

  const pendingEvalCount = pendingEvalSummary?.count ?? 0
  const pendingCoachingCount = (coachingRequests ?? []).filter((r) => r.status === 'pending').length
  const hasTodos = pendingEvalCount + pendingCoachingCount > 0

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">{isAdmin ? '用户管理' : '团队总览'}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {isAdmin ? '查看所有用户并为其创建考核期' : '管理下属成员的绩效状态'}
        </p>
      </div>

      {hasTodos && (
        <Alert>
          <AlertCircle className="size-4" />
          <AlertDescription className="flex flex-wrap gap-3">
            {pendingEvalCount > 0 && (
              <span>{pendingEvalCount} 人等待我评分</span>
            )}
            {pendingCoachingCount > 0 && (
              <span>{pendingCoachingCount} 条辅导请求待处理</span>
            )}
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Input placeholder="搜索成员..." value={search} onChange={(e) => setSearch(e.target.value)} className="w-full sm:w-56" />
        {!isAdmin && (
          <Button variant={directOnly ? 'default' : 'outline'} size="sm" onClick={() => setDirectOnly((v) => !v)}>
            {directOnly ? '直属' : '全部下属'}
          </Button>
        )}
        {currentUser?.role === 'system_admin' && (
          <Button size="sm" onClick={() => setCreateUserOpen(true)}>
            <CalendarPlus data-icon="inline-start" />
            创建用户
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}</div>
      ) : filtered.length === 0 ? (
        <p className="text-center text-muted-foreground py-8">
          {search ? '未找到匹配成员' : (isAdmin ? '暂无用户数据' : '暂无下属成员')}
        </p>
      ) : (
        <div className="flex flex-col gap-2">
          {filtered.map((member) => {
            const period = teamPeriods?.find(p => p.user_id === member.id)
            const memberCoaching = (coachingRequests ?? []).filter(
              r => r.requester_id === member.id && r.status === 'pending'
            )
            const memberAllCoaching = (coachingRequests ?? []).filter(
              r => r.requester_id === member.id
            )
            return (
              <MemberCard
                key={member.id}
                member={member}
                period={period}
                pendingCoaching={memberCoaching}
                allCoaching={memberAllCoaching}
                isAdmin={isAdmin}
                canManage={isAdmin || currentUser?.role === 'manager'}
                onCreatePeriod={() => setCreateTarget({ id: member.id, name: member.full_name })}
                onEditPeriod={() => period && setEditTarget({ period, userName: member.full_name })}
              />
            )
          })}
        </div>
      )}

      {createTarget && (
        <CreatePeriodDialog
          userId={createTarget.id}
          userName={createTarget.name}
          open={!!createTarget}
          onOpenChange={(v) => { if (!v) setCreateTarget(null) }}
        />
      )}
      {editTarget && (
        <EditPeriodDialog
          period={editTarget.period}
          userName={editTarget.userName}
          open={!!editTarget}
          onOpenChange={(nextOpen) => { if (!nextOpen) setEditTarget(null) }}
        />
      )}
      <CreateUserDialog open={createUserOpen} onOpenChange={setCreateUserOpen} />
    </div>
  )
}
