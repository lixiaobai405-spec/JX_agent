import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/auth/LoginPage'
import { ProfilePage } from '@/pages/profile/ProfilePage'
import { ManagementPage } from '@/pages/management/ManagementPage'
import { PlanPage } from '@/pages/pdca/plan/PlanPage'
import { DoPage } from '@/pages/pdca/do/DoPage'
import { CheckPage } from '@/pages/pdca/check/CheckPage'
import { ActionPage } from '@/pages/pdca/action/ActionPage'
import { AdminOrgPage } from '@/pages/admin/AdminOrgPage'
import { AdminPeriodsPage } from '@/pages/admin/AdminPeriodsPage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('access_token')
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: <RequireAuth><AppShell /></RequireAuth>,
    children: [
      { index: true, element: <Navigate to="/profile" replace /> },
      { path: 'profile', element: <ProfilePage /> },
      { path: 'management', element: <ManagementPage /> },
      { path: 'management/team/:userId', element: <ProfilePage /> },
      { path: 'pdca/plan', element: <PlanPage /> },
      { path: 'pdca/do', element: <DoPage /> },
      { path: 'pdca/check', element: <CheckPage /> },
      { path: 'pdca/action', element: <ActionPage /> },
      { path: 'admin/org', element: <AdminOrgPage /> },
      { path: 'admin/periods', element: <AdminPeriodsPage /> },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
