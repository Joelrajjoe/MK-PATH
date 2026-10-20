import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  FolderOpen,
  Database,
  BrainCircuit,
  Bot,
  CheckCircle,
  Network,
  Package,
  Activity,
  ShieldCheck,
  Wrench,
  Menu,
  X,
  Download,
  WifiOff,
  LineChart,
  MoreHorizontal
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { subscribeInstall, subscribeOnline, promptInstallApp } from '@/pwa'

export default function Shell() {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [canInstall, setCanInstall] = useState(false)
  const [isOnline, setIsOnline] = useState(true)

  useEffect(() => {
    const unsubInstall = subscribeInstall(setCanInstall)
    const unsubOnline = subscribeOnline(setIsOnline)
    return () => {
      unsubInstall()
      unsubOnline()
    }
  }, [])

  // Auto-close mobile drawer when location changes
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  // Extract active project ID from pathname if inside a project workspace
  const pathParts = location.pathname.split('/')
  const activeProjectId = pathParts[1] === 'projects' && pathParts[2] && pathParts[2] !== 'new' ? pathParts[2] : null

  const getPath = (tabKey: string) => {
    if (tabKey === 'dashboard') return '/dashboard'
    if (tabKey === 'projects') return '/projects'
    if (activeProjectId) {
      return `/projects/${activeProjectId}/${tabKey}`
    }
    return `/projects`
  }

  const navItems = [
    { name: 'Overview', key: 'dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Projects', key: 'projects', path: '/projects', icon: FolderOpen },
    { name: 'Executive BI', key: 'exec_dashboard', path: activeProjectId ? `/projects/${activeProjectId}/dashboard` : '/dashboard', icon: LineChart },
    { name: 'Data', key: 'data', path: getPath('data'), icon: Database },
    { name: 'Knowledge', key: 'knowledge', path: getPath('knowledge'), icon: BrainCircuit },
    { name: 'Agents', key: 'agents', path: getPath('agents'), icon: Bot },
    { name: 'Analysis', key: 'analysis', path: getPath('analysis'), icon: Activity },
    { name: 'Verification', key: 'verification', path: getPath('verification'), icon: CheckCircle },
    { name: 'Models', key: 'models', path: getPath('models'), icon: Network },
    { name: 'Healing', key: 'healing', path: getPath('healing'), icon: Wrench },
    { name: 'Artifacts', key: 'artifacts', path: getPath('artifacts'), icon: Package },
    { name: 'Audit', key: 'audit', path: getPath('audit'), icon: ShieldCheck },
  ]

  const handleInstallClick = async () => {
    await promptInstallApp()
  }

  return (
    <div className="flex h-screen w-full flex-col bg-background text-foreground md:flex-row overflow-hidden">
      {/* Offline Status Alert Banner */}
      {!isOnline && (
        <div className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-amber-500/90 text-amber-950 px-4 py-1.5 text-xs font-semibold shadow-md backdrop-blur">
          <WifiOff className="h-3.5 w-3.5" />
          <span>Offline Mode — Cached data and local storage active. Reconnecting...</span>
        </div>
      )}

      {/* Desktop Sidebar */}
      <aside className="hidden w-64 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center justify-between border-b px-4 lg:h-[60px]">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-bold text-primary">
            <Network className="h-6 w-6 text-primary" />
            <span className="text-lg tracking-tight font-black">MK-PATH</span>
          </NavLink>
          {canInstall && (
            <button
              onClick={handleInstallClick}
              title="Install MK-Path App (PWA)"
              className="flex items-center gap-1 rounded-md bg-primary/10 border border-primary/20 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/20 transition-all"
            >
              <Download className="h-3 w-3" />
              <span>Install</span>
            </button>
          )}
        </div>
        <div className="flex-1 overflow-auto py-2">
          <nav className="grid items-start px-2 text-sm font-medium space-y-1">
            {navItems.map((item) => {
              const targetPath = item.path
              let isActive = false
              if (item.key === 'dashboard') {
                isActive = location.pathname === '/dashboard'
              } else if (item.key === 'projects') {
                isActive = location.pathname === '/projects' || location.pathname === '/projects/new'
              } else if (item.key === 'exec_dashboard') {
                isActive = location.pathname.includes('/dashboard') && location.pathname !== '/dashboard'
              } else if (activeProjectId) {
                isActive = location.pathname.includes(`/${item.key}`)
              }

              return (
                <NavLink
                  key={item.name}
                  to={targetPath}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary hover:bg-muted/50",
                    isActive ? "bg-primary/10 text-primary font-semibold" : ""
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </NavLink>
              )
            })}
          </nav>
        </div>
        <div className="border-t p-3 text-xs text-muted-foreground flex items-center justify-between">
          <span>PWA v1.0 • Engine Active</span>
          <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
        </div>
      </aside>

      {/* Mobile Slide-out Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
            onClick={() => setMobileMenuOpen(false)}
          />
          {/* Drawer content */}
          <div className="relative flex w-4/5 max-w-xs flex-1 flex-col bg-card border-r shadow-2xl p-4 z-50">
            <div className="flex items-center justify-between border-b pb-3">
              <NavLink to="/dashboard" onClick={() => setMobileMenuOpen(false)} className="flex items-center gap-2 font-bold text-primary">
                <Network className="h-6 w-6 text-primary" />
                <span className="text-lg tracking-tight font-black">MK-PATH</span>
              </NavLink>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="rounded-lg p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {canInstall && (
              <div className="mt-3 p-2.5 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-between">
                <div className="text-xs">
                  <p className="font-semibold text-primary">Install MK-Path</p>
                  <p className="text-muted-foreground text-[10px]">Add to your home screen</p>
                </div>
                <button
                  onClick={handleInstallClick}
                  className="rounded-md bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground shadow-sm hover:bg-primary/90"
                >
                  Install
                </button>
              </div>
            )}

            <nav className="flex-1 overflow-y-auto mt-4 space-y-1">
              {navItems.map((item) => {
                let isActive = false
                if (item.key === 'dashboard') {
                  isActive = location.pathname === '/dashboard'
                } else if (item.key === 'projects') {
                  isActive = location.pathname === '/projects' || location.pathname === '/projects/new'
                } else if (item.key === 'exec_dashboard') {
                  isActive = location.pathname.includes('/dashboard') && location.pathname !== '/dashboard'
                } else if (activeProjectId) {
                  isActive = location.pathname.includes(`/${item.key}`)
                }

                return (
                  <NavLink
                    key={item.name}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-all hover:bg-muted/50 hover:text-primary",
                      isActive ? "bg-primary/15 text-primary font-bold" : ""
                    )}
                  >
                    <item.icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </NavLink>
                )
              })}
            </nav>

            <div className="border-t pt-3 text-xs text-muted-foreground flex items-center justify-between">
              <span>Mobile PWA Active</span>
              <span className="flex items-center gap-1.5 text-emerald-500 font-medium">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Online
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Main Container */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b bg-card px-3 sm:px-6 lg:h-[60px] z-20">
          <div className="flex items-center gap-2 sm:gap-4 overflow-hidden">
            {/* Mobile Hamburger Button */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground md:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>

            {/* Mobile Brand Label */}
            <NavLink to="/dashboard" className="flex items-center gap-1.5 font-bold text-primary md:hidden">
              <Network className="h-5 w-5 text-primary" />
              <span className="text-base tracking-tight font-black">MK-PATH</span>
            </NavLink>

            <span className="hidden sm:inline-block text-xs sm:text-sm font-semibold tracking-wide text-muted-foreground truncate max-w-[180px] lg:max-w-md">
              {activeProjectId ? `Project Workspace: ${activeProjectId}` : 'Multi-Agent Knowledge Platform'}
            </span>
            <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] sm:text-xs font-semibold text-emerald-500 border border-emerald-500/20 shrink-0">
              Real Engine Active
            </span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Install PWA Button on Topbar for Mobile/Desktop */}
            {canInstall && (
              <button
                onClick={handleInstallClick}
                className="flex items-center gap-1.5 rounded-full bg-primary/10 border border-primary/20 px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/20 transition-all shadow-sm"
              >
                <Download className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Install App</span>
                <span className="sm:hidden">Install</span>
              </button>
            )}

            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold text-xs shadow-sm">
              MK
            </div>
          </div>
        </header>

        {/* Main Content Area (with extra bottom padding on mobile for the bottom nav bar) */}
        <main className="flex-1 overflow-auto p-3 sm:p-5 md:p-6 pb-20 md:pb-6 bg-muted/10">
          <Outlet />
        </main>

        {/* Mobile Bottom Navigation Bar (Thumb-optimized for phones) */}
        <nav className="fixed bottom-0 left-0 right-0 z-40 flex h-14 items-center justify-around border-t bg-card/95 backdrop-blur px-2 md:hidden pb-[env(safe-area-inset-bottom)]">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-0.5 py-1 px-3 text-[10px] font-medium transition-colors",
                isActive ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            <LayoutDashboard className="h-4 w-4" />
            <span>Overview</span>
          </NavLink>

          <NavLink
            to="/projects"
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-0.5 py-1 px-3 text-[10px] font-medium transition-colors",
                isActive && !location.pathname.includes('/dashboard') ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            <FolderOpen className="h-4 w-4" />
            <span>Projects</span>
          </NavLink>

          <NavLink
            to={activeProjectId ? `/projects/${activeProjectId}/dashboard` : '/dashboard'}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-0.5 py-1 px-3 text-[10px] font-medium transition-colors",
                isActive || location.pathname.endsWith('/dashboard') ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            <LineChart className="h-4 w-4" />
            <span>BI Dash</span>
          </NavLink>

          <NavLink
            to={getPath('data')}
            className={({ isActive }) =>
              cn(
                "flex flex-col items-center justify-center gap-0.5 py-1 px-3 text-[10px] font-medium transition-colors",
                isActive ? "text-primary font-bold" : "text-muted-foreground hover:text-foreground"
              )
            }
          >
            <Database className="h-4 w-4" />
            <span>Data</span>
          </NavLink>

          <button
            onClick={() => setMobileMenuOpen(true)}
            className="flex flex-col items-center justify-center gap-0.5 py-1 px-3 text-[10px] font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <MoreHorizontal className="h-4 w-4" />
            <span>More</span>
          </button>
        </nav>
      </div>
    </div>
  )
}
