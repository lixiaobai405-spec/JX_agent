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
import { LogOut, Monitor, KeyRound, ArrowRight, BarChart3 } from 'lucide-react'
import { useCurrentUser, useCurrentPeriod, useCurrentGoal, useLatestDiagnostic, useFinalResult, useSessions, useLogout } from '@/hooks'
import { usersApi } from '@/api/users'
import { authApi } from '@/api/auth'
import { TrafficLight } from '@/components/shared/TrafficLight'
import { PhaseStatusBadge } from '@/components/shared/PhaseStatusBadge'
import { formatDateTimeLocal } from '@/lib/datetime'

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
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between text-base">
              执行进度
              <TrafficLight status={diagnostic.traffic_light_status} />
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">加权完成率</span>
              <span className="font-medium">
                {diagnostic.weighted_achievement_rate != null
                  ? `${Math.round(diagnostic.weighted_achievement_rate * 100)}%`
                  : '—'}
              </span>
            </div>
            {diagnostic.weighted_achievement_rate != null && (
              <Progress value={diagnostic.weighted_achievement_rate * 100} />
            )}
          </CardContent>
        </Card>
      )}
      {finalResult && (
        <Card>
          <CardContent className="flex items-center justify-between pt-4">
            <span className="text-sm text-muted-foreground">最终等级</span>
            <Badge variant="default" className="text-lg px-3">
              {finalResult.final_grade}
            </Badge>
          </CardContent>
        </Card>
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

function HistoryTab() {
  return (
    <div className="py-4 text-sm text-muted-foreground">
      历史考核期记录（功能开发中）
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
              <HistoryTab />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
