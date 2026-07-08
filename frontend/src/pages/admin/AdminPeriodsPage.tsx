import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { CalendarPlus, Play, Archive, RotateCcw, Square } from 'lucide-react'
import { periodsApi } from '@/api/do'
import { usersApi } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { normalizeList } from '@/lib/api-normalizers'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { Period, PeriodStatus } from '@/types'

type ApiError = {
  response?: {
    data?: {
      message?: string
      detail?: string
    }
  }
  message?: string
}

const statusText: Record<PeriodStatus, string> = {
  draft: '草稿',
  open: '进行中',
  closed: '已关闭',
  archived: '已归档',
}

function getErrorMessage(error: unknown) {
  const err = error as ApiError
  return err.response?.data?.message ?? err.response?.data?.detail ?? err.message ?? '操作失败'
}

type PeriodAction = {
  status: PeriodStatus
  label: string
  icon: React.ReactNode
  confirm?: string
}

function getStatusActions(period: Period): PeriodAction[] {
  if (period.status === 'draft') return [{ status: 'open', label: '开放', icon: <Play className="size-3.5" /> }]
  if (period.status === 'open') return [{ status: 'closed', label: '关闭', icon: <Square className="size-3.5" /> }]
  if (period.status === 'closed') {
    return [
      { status: 'open', label: '重新开放', icon: <Play className="size-3.5" /> },
      { status: 'archived', label: '归档', icon: <Archive className="size-3.5" />, confirm: `确认归档「${period.name}」？` },
    ]
  }
  if (period.status === 'archived') {
    return [{ status: 'closed', label: '恢复', icon: <RotateCcw className="size-3.5" />, confirm: `确认恢复「${period.name}」为已关闭？` }]
  }
  return []
}

function PeriodTable({
  periods,
  userNameById,
  updateStatus,
  emptyText,
}: {
  periods: Period[] | null | undefined
  userNameById: Record<string, string>
  updateStatus: (period: Period, action: PeriodAction) => void
  emptyText: string
}) {
  const safePeriods = normalizeList<Period>(periods)

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>名称</TableHead>
          <TableHead>员工</TableHead>
          <TableHead>时间</TableHead>
          <TableHead>状态</TableHead>
          <TableHead className="text-right">操作</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {safePeriods.length === 0 ? (
          <TableRow>
            <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">{emptyText}</TableCell>
          </TableRow>
        ) : safePeriods.map((period) => {
          const actions = getStatusActions(period)
          return (
            <TableRow key={period.id}>
              <TableCell className="font-medium">{period.name}</TableCell>
              <TableCell>{userNameById[period.user_id] ?? period.user_id}</TableCell>
              <TableCell>{period.start_date.slice(0, 10)} ~ {period.end_date.slice(0, 10)}</TableCell>
              <TableCell>
                <Badge variant={period.status === 'open' ? 'default' : 'outline'}>
                  {statusText[period.status]}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                {actions.length ? (
                  <div className="flex justify-end gap-2">
                    {actions.map((action) => (
                      <Button
                        key={action.status}
                        size="sm"
                        variant="outline"
                        onClick={() => updateStatus(period, action)}
                      >
                        {action.icon}
                        {action.label}
                      </Button>
                    ))}
                  </div>
                ) : (
                  <span className="text-sm text-muted-foreground">—</span>
                )}
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

export function AdminPeriodsPage() {
  const qc = useQueryClient()
  const { data: periods = [] } = useQuery({
    queryKey: ['periods', 'current'],
    queryFn: periodsApi.list,
  })
  const { data: archivedPeriods = [] } = useQuery({
    queryKey: ['periods', 'archived'],
    queryFn: () => periodsApi.listByStatus('archived'),
  })
  const { data: users = [] } = useQuery({
    queryKey: ['users', 'period-targets'],
    queryFn: () => usersApi.list(),
  })
  const [form, setForm] = useState({
    user_id: '',
    name: '',
    start_date: '',
    end_date: '',
  })

  const createPeriod = useMutation({
    mutationFn: () => periodsApi.create({
      user_id: form.user_id,
      name: form.name.trim(),
      start_date: new Date(form.start_date).toISOString(),
      end_date: new Date(`${form.end_date}T23:59:59`).toISOString(),
    }),
    onSuccess: () => {
      toast.success('考核期创建成功')
      setForm({ user_id: '', name: '', start_date: '', end_date: '' })
      qc.invalidateQueries({ queryKey: ['periods'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: PeriodStatus }) => periodsApi.updateStatus(id, status),
    onSuccess: () => {
      toast.success('考核期状态已更新')
      qc.invalidateQueries({ queryKey: ['periods'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const canCreate = form.user_id && form.name.trim() && form.start_date && form.end_date && form.end_date > form.start_date
  const userNameById = Object.fromEntries(users.map((user) => [user.id, user.full_name || user.username]))
  const handleStatusAction = (period: Period, action: PeriodAction) => {
    if (action.confirm && !window.confirm(action.confirm)) return
    updateStatus.mutate({ id: period.id, status: action.status })
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">考核期管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">为员工创建绩效周期，并推进草稿、开放、关闭和归档状态。</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CalendarPlus className="size-4" />
              新建考核期
            </CardTitle>
            <CardDescription>创建后默认为草稿，可在列表中开放。</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label>员工</Label>
              <select
                value={form.user_id}
                onChange={(e) => setForm((v) => ({ ...v, user_id: e.target.value }))}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">请选择员工</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>{user.full_name} ({user.username})</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>名称</Label>
              <Input value={form.name} onChange={(e) => setForm((v) => ({ ...v, name: e.target.value }))} placeholder="如：2026年7月绩效周期" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label>开始日期</Label>
                <Input type="date" value={form.start_date} onChange={(e) => setForm((v) => ({ ...v, start_date: e.target.value }))} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>结束日期</Label>
                <Input type="date" value={form.end_date} onChange={(e) => setForm((v) => ({ ...v, end_date: e.target.value }))} />
              </div>
            </div>
            <Button onClick={() => createPeriod.mutate()} disabled={!canCreate || createPeriod.isPending}>
              <CalendarPlus data-icon="inline-start" />
              {createPeriod.isPending ? '创建中...' : '创建考核期'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">考核期列表</CardTitle>
            <CardDescription>同一员工同一时间只能有一个开放考核期。</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="current" className="w-full">
              <TabsList>
                <TabsTrigger value="current">当前周期</TabsTrigger>
                <TabsTrigger value="archived">归档管理</TabsTrigger>
              </TabsList>
              <TabsContent value="current">
                <PeriodTable
                  periods={periods}
                  userNameById={userNameById}
                  updateStatus={handleStatusAction}
                  emptyText="暂无考核期"
                />
              </TabsContent>
              <TabsContent value="archived">
                <PeriodTable
                  periods={archivedPeriods}
                  userNameById={userNameById}
                  updateStatus={handleStatusAction}
                  emptyText="暂无归档考核期"
                />
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
