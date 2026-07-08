import axios from 'axios'
import { toast } from 'sonner'
import { authStorage } from '@/lib/authStorage'

const client = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = authStorage.getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = authStorage.getRefreshToken()
      if (refresh) {
        try {
          const { data } = await axios.post('/api/v1/auth/refresh', {
            refresh_token: refresh,
          })
          authStorage.setTokens(data.access_token, data.refresh_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return client(original)
        } catch {
          // refresh failed
        }
      }
      authStorage.clearTokens()
      window.location.href = '/login'
    }
    const msg = error.response?.data?.message ?? error.response?.data?.detail ?? error.message
    if (error.response?.status !== 401) {
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(error)
  }
)

export default client
