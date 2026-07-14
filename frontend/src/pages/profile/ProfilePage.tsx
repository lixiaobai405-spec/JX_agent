import { useParams, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  ArrowRight,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  KeyRound,
  LogOut,
  Monitor,
  RotateCw,
  TriangleAlert,
} from 'lucide-react'
import { useCurrentUser, useCurrentPeriod, useCurrentGoal, useLatestDiagnostic, useFinalResult, useSessions, useLogout } from '@/hooks'
import { usersApi } from '@/api/users'
import { authApi } from '@/api/auth'
import { periodsApi } from '@/api/do'
import { TrafficLight } from '@/components/shared/TrafficLight'
import { PhaseStatusBadge } from '@/components/shared/PhaseStatusBadge'
import { formatDateTimeLocal } from '@/lib/datetime'
import {
  formatAchievementRate,
  toAchievementProgress,
  WEIGHTED_ACHIEVEMENT_EXPLANATION,
} from '@/lib/performance'

function RoleBadge({ role }: { role: string }) {
  const MAP: Record<string, string> = {
    employee: '员工', manager: '经理', hr_admin: 'HR管理员', system_admin: '系统管理员',
  }
  return <Badge variant="outline">{MAP[role] ?? role}</Badge>
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="flex items-center gap-2 py-2">
      <span className="w-24 shrink-0 text-sm text-muted-foreground">{label}</span>
      <span className="text-sm">{value ?? '—'}</span>
    </div>
  )
}

function CurrentPerformanceTab() {
  const navigate = useNavigate()
  const { data: period, isLoading: periodLoading } = useCurrentPeriod()
  const { data: goal } = useCurrentGoal(period?.id)
  const { data: diagnostic } = useLatestDiagnostic(goal?.id)
  const { data: finalResult } = useFinalResult(goal?.id)

  if (periodLoading) return <Skeleton className="h-40 w-full" />

  if (!period) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-muted-foreground">
        <BarChart3 className="size-10 opacity-40" />
        <p className="text-sm">暂无考核期</p>
      </div>
    )
  }

  const phase = period.status === 'open'
    ? goal
      ? (finalResult ? 'C' : 'D')
      : 'P'
    : period.status

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-medium">{period.name}</p>
          <p className="text-xs text-muted-foreground">
            {period.start_date?.slice(0, 10)} ~ {period.end_date?.slice(0, 10)}
          </p>
        </div>
        <PhaseStatusBadge status={String(phase)} />
      </div>
      <Separator />
      {diagnostic && (
        <div className="rounded-md border p-4">
          <div className="flex items-center justify-between text-sm font-medium">
            <span>执行进度</span>
            <TrafficLight status={diagnostic.traffic_light_status} />
          </div>
          <div className="mt-3 flex items-center justify-between text-sm">
            <span className="flex items-center gap-1 text-muted-foreground">
              加权完成率
              <Tooltip>
                <TooltipTrigger
                  className="inline-flex text-muted-foreground hover:text-foreground"
                  aria-label="查看加权达成率计算说明"
                >
                  <CircleHelp className="size-3.5" />
                </TooltipTrigger>
                <TooltipContent className="max-w-72">
                  {WEIGHTED_ACHIEVEMENT_EXPLANATION}
                </TooltipContent>
              </Tooltip>
            </span>
            <span className="font-medium">
              {formatAchievementRate(diagnostic.weighted_achievement_rate)}
            </span>
          </div>
          {diagnostic.weighted_achievement_rate != null && (
            <Progress
              className="mt-2"
              value={toAchievementProgress(diagnostic.weighted_achievement_rate)}
            />
          )}
        </div>
      )}
      {finalResult && (
        <div className="flex items-center justify-between rounded-md border p-4">
          <span className="text-sm text-muted-foreground">最终等级</span>
          <Badge variant="default" className="px-3 text-lg">
            {finalResult.final_grade}
          </Badge>
        </div>
      )}
      <Button
        variant="outline"
        size="sm"
        className="self-start"
        onClick={() => {
          const routes: Record<string, string> = { P: '/pdca/plan', D: '/pdca/do', C: '/pdca/check', A: '/pdca/action' }
          navigate(routes[String(phase)] ?? '/pdca/plan')
        }}
      >
        查看详情
        <ArrowRight data-icon="inline-end" />
      </Button>
    </div>
  )
}

const HISTORY_PAGE_SIZE = 8
const PERIOD_STATUS_LABELS: Record<string, string> = {
  closed: '已关闭',
  archived: '已归档',
}

function HistoryTab({ targetUserId }: { targetUserId: string }) {
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: ['period-history', targetUserId, page, HISTORY_PAGE_SIZE],
    queryFn: () => periodsApi.history(targetUserId, page, HISTORY_PAGE_SIZE),
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 py-1">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center" role="alert">
        <p className="text-sm text-muted-foreground">历史记录加载失败</p>
        <Button variant="outline" size="sm" disabled={isFetching} onClick={() => refetch()}>
          <RotateCw className={isFetching ? 'animate-spin' : undefined} data-icon="inline-start" />
          重新加载
        </Button>
      </div>
    )
  }

  if (data && data.total > 0 && page > 1 && data.items.length === 0) {
    const lastValidPage = Math.max(1, Math.ceil(data.total / data.page_size))
    const returnPage = Math.min(page - 1, lastValidPage)

    return (
      <div className="flex flex-col items-center gap-3 py-6 text-center">
        <p className="text-sm text-muted-foreground">本页暂无历史记录</p>
        <Button
          variant="outline"
          size="sm"
          disabled={isFetching}
          onClick={() => setPage(returnPage)}
        >
          <ChevronLeft data-icon="inline-start" />
          返回第 {returnPage} 页
        </Button>
      </div>
    )
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-muted-foreground">
        <BarChart3 className="size-10 opacity-40" />
        <p className="text-sm">暂无历史考核记录</p>
      </div>
    )
  }

  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size))

  return (
    <div className="flex flex-col" aria-busy={isFetching}>
      <div className={isFetching ? 'divide-y opacity-60' : 'divide-y'}>
        {data.items.map((item) => (
          <div key={item.period_id} className="py-4 first:pt-0">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{item.name}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.start_date.slice(0, 10)} ~ {item.end_date.slice(0, 10)}
                </p>
              </div>
              <Badge variant="outline">
                {PERIOD_STATUS_LABELS[item.status] ?? item.status}
              </Badge>
            </div>

            {item.has_data_conflict && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-destructive">
                <TriangleAlert className="size-3.5 shrink-0" />
                检测到多份绩效目标，摘要暂不可用
              </div>
            )}

            <div className="mt-3 grid grid-cols-3 gap-2 bg-muted/40 px-3 py-2">
              <div>
                <p className="text-xs text-muted-foreground">加权率</p>
                <p className="mt-1 text-sm font-medium">
                  {formatAchievementRate(
                    item.has_data_conflict
                      ? null
                      : item.diagnostic_summary?.weighted_achievement_rate,
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">灯号</p>
                <div className="mt-1 flex h-5 items-center">
                  {!item.has_data_conflict && item.diagnostic_summary?.traffic_light_status
                    ? <TrafficLight status={item.diagnostic_summary.traffic_light_status} />
                    : <span className="text-sm">—</span>}
                </div>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">最终等级</p>
                <p className="mt-1 text-sm font-medium">
                  {item.has_data_conflict ? '—' : (item.final_result_summary?.final_grade ?? '—')}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-xs text-muted-foreground">
          第 {data.page} / {totalPages} 页，共 {data.total} 条
        </span>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <Button
            className="flex-1 sm:flex-none"
            variant="outline"
            size="sm"
            disabled={page <= 1 || isFetching}
            onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
          >
            <ChevronLeft data-icon="inline-start" />
            上一页
          </Button>
          <Button
            className="flex-1 sm:flex-none"
            variant="outline"
            size="sm"
            disabled={page >= totalPages || isFetching}
            onClick={() => setPage((currentPage) => currentPage + 1)}
          >
            下一页
            <ChevronRight data-icon="inline-end" />
          </Button>
        </div>
      </div>
    </div>
  )
}

function ChangePasswordDialog() {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await authApi.changePassword(current, next)
      toast.success('密码修改成功')
      setOpen(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <KeyRound data-icon="inline-start" />
        修改密码
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>修改密码</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 pt-2">
            <div className="flex flex-col gap-1.5">
              <Label>当前密码</Label>
              <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>新密码</Label>
              <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} />
            </div>
            <Button type="submit" disabled={loading}>确认修改</Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}

function SessionsDialog() {
  const [open, setOpen] = useState(false)
  const { data: sessions } = useSessions()

  return (
    <>
      <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <Monitor data-icon="inline-start" />
        设备管理
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>登录设备</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-2 pt-2">
            {sessions?.map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-md border p-3">
                <div className="text-sm">
                  <p className="font-medium">
                    {s.device_info?.browser ?? '未知浏览器'} · {s.device_info?.os ?? '未知系统'}
                  </p>
                  <p className="text-xs text-muted-foreground">{s.ip_address ?? '—'}</p>
                </div>
                {s.is_current && <Badge variant="secondary">当前</Badge>}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function ProfilePage() {
  const { userId } = useParams<{ userId?: string }>()
  const { data: currentUser } = useCurrentUser()
  const logout = useLogout()

  const targetUserId = userId ?? currentUser?.id
  const isOwnProfile = !userId

  const { data: user, isLoading } = useQuery({
    queryKey: ['user', targetUserId],
    queryFn: () => (userId ? usersApi.get(userId) : authApi.me()),
    enabled: !!targetUserId,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 max-w-2xl">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    )
  }

  if (!user) return null

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex flex-col gap-1">
              <CardTitle className="flex items-center gap-2 text-xl">
                {user.full_name}
                <RoleBadge role={user.role} />
                {user.position_name && (
                  <Badge variant="secondary">{user.position_name}</Badge>
                )}
              </CardTitle>
              <CardDescription className="flex items-center gap-3 flex-wrap mt-1">
                {user.department_name && <span>{user.department_name}</span>}
                {user.hire_date && <span>{user.hire_date.slice(0, 10)} 入职</span>}
                {user.manager_name && <span>上级：{user.manager_name}</span>}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
      </Card>

      <Tabs defaultValue="info">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="info">基本信息</TabsTrigger>
          <TabsTrigger value="current">当前绩效</TabsTrigger>
          <TabsTrigger value="history">历史记录</TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="mt-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-col divide-y">
                <InfoRow label="用户名" value={user.username} />
                <InfoRow label="邮箱" value={user.email} />
                <InfoRow label="手机" value={user.phone} />
                <InfoRow label="部门" value={user.department_name} />
                <InfoRow label="岗位" value={user.position_name} />
                <InfoRow label="上级" value={user.manager_name} />
                <InfoRow label="状态" value={user.status === 'inactive' ? '停用' : '在职'} />
                <InfoRow label="最后登录" value={formatDateTimeLocal(user.last_login_at)} />
              </div>
              {isOwnProfile && (
                <>
                  <Separator className="my-4" />
                  <div className="flex items-center gap-2 flex-wrap">
                    <ChangePasswordDialog />
                    <SessionsDialog />
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => logout.mutate()}
                    >
                      <LogOut data-icon="inline-start" />
                      退出登录
                    </Button>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="current" className="mt-4">
          <Card>
            <CardContent className="pt-4">
              <CurrentPerformanceTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <Card>
            <CardContent className="pt-4">
              {targetUserId && (
                <HistoryTab key={targetUserId} targetUserId={targetUserId} />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
