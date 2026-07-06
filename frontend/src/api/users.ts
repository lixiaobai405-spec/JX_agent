import client from './client'
import type { User, SubordinateItem } from '@/types'

export const usersApi = {
  list: (params?: { role?: string; department_id?: string }) =>
    client.get<{ data: User[] }>('/users/', { params }).then((r) => r.data.data),

  get: (id: string) => client.get<User>(`/users/${id}`).then((r) => r.data),

  create: (data: {
    username: string
    email: string
    full_name: string
    password: string
    role?: string
    manager_id?: string
    department_id?: string
    position_id?: string
    phone?: string
  }) => client.post<User>('/users/', data).then((r) => r.data),

  update: (id: string, data: Partial<User>) =>
    client.put<User>(`/users/${id}`, data).then((r) => r.data),

  subordinates: (id: string, direct_only = false) =>
    client.get<{ subordinates: SubordinateItem[] }>(`/users/${id}/subordinates`, {
      params: { direct_only },
    }).then((r) => r.data.subordinates),

  myTeam: () =>
    client.get<{ manager: User; members: User[] }>('/users/me/team').then((r) => r.data),
}
