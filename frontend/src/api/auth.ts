import client from './client'
import type { LoginResponse, User, SessionInfo } from '@/types'

export const authApi = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return client.post<LoginResponse>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }).then((r) => r.data)
  },

  logout: () => client.post('/auth/logout'),

  me: () => client.get<User>('/auth/me').then((r) => r.data),

  changePassword: (old_password: string, new_password: string) =>
    client.post('/auth/password/change', { old_password, new_password }),

  sessions: () => client.get<{ sessions: SessionInfo[] }>('/auth/sessions').then((r) => r.data.sessions),

  revokeSession: (sessionId: string) => client.delete(`/auth/sessions/${sessionId}`),
}
