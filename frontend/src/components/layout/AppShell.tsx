import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Sidebar } from './Sidebar'

export function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  useEffect(() => {
    const desktopMedia = window.matchMedia('(min-width: 768px)')
    const closeMobileNav = () => {
      if (desktopMedia.matches) setMobileNavOpen(false)
    }

    desktopMedia.addEventListener('change', closeMobileNav)
    return () => desktopMedia.removeEventListener('change', closeMobileNav)
  }, [])

  return (
    <div className="flex h-dvh overflow-hidden">
      <div className="hidden h-full md:block">
        <Sidebar />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-sidebar-border bg-sidebar px-4 md:hidden">
          <Dialog open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
            <DialogTrigger
              render={
                <Button
                  className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  variant="ghost"
                  size="icon"
                  aria-label="打开主导航"
                />
              }
            >
              <Menu />
            </DialogTrigger>
            <DialogContent
              className="top-0 left-0 h-dvh w-60 max-w-none translate-x-0 translate-y-0 gap-0 rounded-none p-0 sm:max-w-none md:hidden"
              showCloseButton={false}
            >
              <DialogTitle className="sr-only">主导航</DialogTitle>
              <DialogClose
                render={
                  <Button
                    className="absolute top-3 right-3 z-10 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    variant="ghost"
                    size="icon"
                    aria-label="关闭主导航"
                  />
                }
              >
                <X />
              </DialogClose>
              <Sidebar onNavigate={() => setMobileNavOpen(false)} />
            </DialogContent>
          </Dialog>
          <img src="/logo.png" alt="美太咨询" className="h-7 object-contain" />
        </header>

        <main className="min-w-0 flex-1 overflow-y-auto bg-background p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
