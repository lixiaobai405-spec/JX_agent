import { NavLink } from 'react-router-dom'
import {
  User,
  Target,
  Activity,
  CheckCircle,
  Lightbulb,
  Users,
  Building2,
  Calendar,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useCurrentUser } from '@/hooks'

const MANAGER_ROLES = ['manager', 'hr_admin', 'system_admin']
const ADMIN_ROLES = ['hr_admin', 'system_admin']

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  end?: boolean
}

function NavGroup({
  title,
  items,
  onNavigate,
}: {
  title?: string
  items: NavItem[]
  onNavigate?: () => void
}) {
  return (
    <div className="flex flex-col gap-0.5">
      {title && (
        <p className="px-3 py-1 text-xs font-medium text-sidebar-foreground/40 uppercase tracking-wide">
          {title}
        </p>
      )}
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors',
              isActive
                ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground'
            )
          }
        >
          {item.icon}
          {item.label}
        </NavLink>
      ))}
    </div>
  )
}

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { data: user } = useCurrentUser()

  const pdcaItems: NavItem[] = [
    { to: '/pdca/plan', label: 'P - 目标设定', icon: <Target className="size-4" /> },
    { to: '/pdca/do', label: 'D - 执行追踪', icon: <Activity className="size-4" /> },
    { to: '/pdca/check', label: 'C - 考核评估', icon: <CheckCircle className="size-4" /> },
    { to: '/pdca/action', label: 'A - 复盘发展', icon: <Lightbulb className="size-4" /> },
  ]

  const isManager = user && MANAGER_ROLES.includes(user.role)
  const isAdmin = user && ADMIN_ROLES.includes(user.role)

  return (
    <aside aria-label="主导航" className="flex h-full w-60 shrink-0 flex-col border-r bg-sidebar">
      {/* Logo */}
      <div className="flex h-[60px] items-center justify-center border-b border-sidebar-border px-4">
        <img src="/logo.png" alt="logo" className="h-8 object-contain" />
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-4 overflow-y-auto p-3">
        <NavGroup
          onNavigate={onNavigate}
          items={[
            { to: '/profile', label: '个人主页', icon: <User className="size-4" />, end: true },
          ]}
        />

        <NavGroup
          title="PDCA 绩效"
          items={pdcaItems}
          onNavigate={onNavigate}
        />

        {isManager && (
          <NavGroup
            title="管理视图"
            onNavigate={onNavigate}
            items={[
              { to: '/management', label: '团队总览', icon: <Users className="size-4" /> },
            ]}
          />
        )}

        {isAdmin && (
          <NavGroup
            title="管理员"
            onNavigate={onNavigate}
            items={[
              { to: '/admin/org', label: '组织管理', icon: <Building2 className="size-4" /> },
              { to: '/admin/periods', label: '考核期管理', icon: <Calendar className="size-4" /> },
            ]}
          />
        )}
      </nav>

      {/* User info at bottom */}
      {user && (
        <div className="mt-auto border-t p-3">
          <div className="flex items-center gap-2.5 rounded-md px-2 py-2">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-xs font-medium text-sidebar-primary-foreground">
              {user.full_name?.slice(0, 1) ?? user.username.slice(0, 1)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-sidebar-foreground">{user.full_name}</p>
              <p className="truncate text-xs text-sidebar-foreground/50">{user.department_name ?? '—'}</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
