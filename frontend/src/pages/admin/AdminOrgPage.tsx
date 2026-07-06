import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Building2, BriefcaseBusiness, Plus, Trash2 } from 'lucide-react'
import { organizationsApi } from '@/api/organizations'
import { usersApi } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

type ApiError = {
  response?: {
    data?: {
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

function emptyToUndefined(value: string) {
  const trimmed = value.trim()
  return trimmed ? trimmed : undefined
}

function DepartmentPanel() {
  const qc = useQueryClient()
  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: organizationsApi.listDepartments,
  })
  const { data: users = [] } = useQuery({
    queryKey: ['users', 'org-managers'],
    queryFn: () => usersApi.list(),
  })
  const [form, setForm] = useState({
    name: '',
    code: '',
    parent_id: '',
    manager_id: '',
    description: '',
  })

  const createDepartment = useMutation({
    mutationFn: () => organizationsApi.createDepartment({
      name: form.name.trim(),
      code: form.code.trim(),
      parent_id: emptyToUndefined(form.parent_id),
      manager_id: emptyToUndefined(form.manager_id),
      description: emptyToUndefined(form.description),
    }),
    onSuccess: () => {
      toast.success('部门创建成功')
      setForm({ name: '', code: '', parent_id: '', manager_id: '', description: '' })
      qc.invalidateQueries({ queryKey: ['departments'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const deleteDepartment = useMutation({
    mutationFn: organizationsApi.deleteDepartment,
    onSuccess: () => {
      toast.success('部门已删除')
      qc.invalidateQueries({ queryKey: ['departments'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const canCreate = form.name.trim() && form.code.trim()

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Building2 className="size-4" />
            新建部门
          </CardTitle>
          <CardDescription>部门编码不能重复，父级部门和负责人可选。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>部门名称</Label>
            <Input value={form.name} onChange={(e) => setForm((v) => ({ ...v, name: e.target.value }))} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>部门编码</Label>
            <Input value={form.code} onChange={(e) => setForm((v) => ({ ...v, code: e.target.value }))} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>父级部门</Label>
            <select
              value={form.parent_id}
              onChange={(e) => setForm((v) => ({ ...v, parent_id: e.target.value }))}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">无</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>{dept.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>负责人</Label>
            <select
              value={form.manager_id}
              onChange={(e) => setForm((v) => ({ ...v, manager_id: e.target.value }))}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">无</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>{user.full_name} ({user.username})</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>说明</Label>
            <Input value={form.description} onChange={(e) => setForm((v) => ({ ...v, description: e.target.value }))} />
          </div>
          <Button onClick={() => createDepartment.mutate()} disabled={!canCreate || createDepartment.isPending}>
            <Plus data-icon="inline-start" />
            {createDepartment.isPending ? '创建中...' : '创建部门'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">部门列表</CardTitle>
          <CardDescription>删除部门前需确保没有子部门和成员。</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>编码</TableHead>
                <TableHead>层级</TableHead>
                <TableHead>负责人</TableHead>
                <TableHead>人数</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {departments.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">暂无部门</TableCell>
                </TableRow>
              ) : departments.map((dept) => (
                <TableRow key={dept.id}>
                  <TableCell className="font-medium">{dept.name}</TableCell>
                  <TableCell>{dept.code}</TableCell>
                  <TableCell>{dept.level}</TableCell>
                  <TableCell>{dept.manager_name ?? '—'}</TableCell>
                  <TableCell>{dept.member_count}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        if (window.confirm(`确认删除部门「${dept.name}」？`)) {
                          deleteDepartment.mutate(dept.id)
                        }
                      }}
                      disabled={deleteDepartment.isPending}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

function PositionPanel() {
  const qc = useQueryClient()
  const { data: positions = [] } = useQuery({
    queryKey: ['positions'],
    queryFn: organizationsApi.listPositions,
  })
  const { data: departments = [] } = useQuery({
    queryKey: ['departments'],
    queryFn: organizationsApi.listDepartments,
  })
  const [form, setForm] = useState({
    name: '',
    code: '',
    department_id: '',
    level: '',
    description: '',
  })

  const createPosition = useMutation({
    mutationFn: () => organizationsApi.createPosition({
      name: form.name.trim(),
      code: form.code.trim(),
      department_id: emptyToUndefined(form.department_id),
      level: emptyToUndefined(form.level),
      description: emptyToUndefined(form.description),
    }),
    onSuccess: () => {
      toast.success('岗位创建成功')
      setForm({ name: '', code: '', department_id: '', level: '', description: '' })
      qc.invalidateQueries({ queryKey: ['positions'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const deletePosition = useMutation({
    mutationFn: organizationsApi.deletePosition,
    onSuccess: () => {
      toast.success('岗位已删除')
      qc.invalidateQueries({ queryKey: ['positions'] })
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  })

  const canCreate = form.name.trim() && form.code.trim()

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BriefcaseBusiness className="size-4" />
            新建岗位
          </CardTitle>
          <CardDescription>岗位可绑定到部门，便于后续创建员工账号。</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>岗位名称</Label>
            <Input value={form.name} onChange={(e) => setForm((v) => ({ ...v, name: e.target.value }))} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>岗位编码</Label>
            <Input value={form.code} onChange={(e) => setForm((v) => ({ ...v, code: e.target.value }))} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>所属部门</Label>
            <select
              value={form.department_id}
              onChange={(e) => setForm((v) => ({ ...v, department_id: e.target.value }))}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
            >
              <option value="">未指定</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>{dept.name}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>职级</Label>
            <Input value={form.level} onChange={(e) => setForm((v) => ({ ...v, level: e.target.value }))} placeholder="如：P5 / M2" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>说明</Label>
            <Input value={form.description} onChange={(e) => setForm((v) => ({ ...v, description: e.target.value }))} />
          </div>
          <Button onClick={() => createPosition.mutate()} disabled={!canCreate || createPosition.isPending}>
            <Plus data-icon="inline-start" />
            {createPosition.isPending ? '创建中...' : '创建岗位'}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">岗位列表</CardTitle>
          <CardDescription>删除岗位前需确保没有成员关联。</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>编码</TableHead>
                <TableHead>部门</TableHead>
                <TableHead>职级</TableHead>
                <TableHead>人数</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {positions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">暂无岗位</TableCell>
                </TableRow>
              ) : positions.map((position) => (
                <TableRow key={position.id}>
                  <TableCell className="font-medium">{position.name}</TableCell>
                  <TableCell>{position.code}</TableCell>
                  <TableCell>{position.department_name ?? '—'}</TableCell>
                  <TableCell>{position.level ?? '—'}</TableCell>
                  <TableCell>{position.member_count}</TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => {
                        if (window.confirm(`确认删除岗位「${position.name}」？`)) {
                          deletePosition.mutate(position.id)
                        }
                      }}
                      disabled={deletePosition.isPending}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}

export function AdminOrgPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold">组织管理</h1>
        <p className="mt-1 text-sm text-muted-foreground">维护部门和岗位基础数据，用于用户账号和绩效周期配置。</p>
      </div>
      <Tabs defaultValue="departments">
        <TabsList>
          <TabsTrigger value="departments">部门</TabsTrigger>
          <TabsTrigger value="positions">岗位</TabsTrigger>
        </TabsList>
        <TabsContent value="departments" className="mt-4">
          <DepartmentPanel />
        </TabsContent>
        <TabsContent value="positions" className="mt-4">
          <PositionPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
