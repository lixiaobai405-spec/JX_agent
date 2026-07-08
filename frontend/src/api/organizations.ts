import client from './client'
import type { Department, Position } from '@/types'

export const organizationsApi = {
  listDepartments: () =>
    client.get<{ data: Department[] }>('/organizations/departments').then((r) => r.data.data),

  createDepartment: (data: {
    name: string
    code: string
    parent_id?: string
    manager_id?: string
    description?: string
  }) => client.post<Department>('/organizations/departments', data).then((r) => r.data),

  updateDepartment: (id: string, data: {
    name?: string
    parent_id?: string | null
    manager_id?: string | null
    description?: string | null
  }) => client.put<Department>(`/organizations/departments/${id}`, data).then((r) => r.data),

  deleteDepartment: (id: string) =>
    client.delete(`/organizations/departments/${id}`).then((r) => r.data),

  listPositions: () =>
    client.get<{ data: Position[] }>('/organizations/positions').then((r) => r.data.data),

  createPosition: (data: {
    name: string
    code: string
    department_id?: string
    level?: string
    description?: string
  }) => client.post<Position>('/organizations/positions', data).then((r) => r.data),

  deletePosition: (id: string) =>
    client.delete(`/organizations/positions/${id}`).then((r) => r.data),
}
