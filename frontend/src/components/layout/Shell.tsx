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
  Wrench
} from 'lucide-react'
import { cn } from '@/lib/utils'

export default function Shell() {
  const location = useLocation()
  
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

  return (
    <div className="flex h-screen w-full flex-col bg-background text-foreground md:flex-row">
      {/* Sidebar */}
      <aside className="hidden w-64 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center border-b px-4 lg:h-[60px]">
          <NavLink to="/dashboard" className="flex items-center gap-2 font-bold text-primary">
            <Network className="h-6 w-6 text-primary" />
            <span className="text-lg tracking-tight font-black">MK-PATH</span>
          </NavLink>
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
      </aside>

      {/* Main Container */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b bg-card px-6 lg:h-[60px]">
          <div className="flex items-center gap-4">
            <span className="text-sm font-semibold tracking-wide text-muted-foreground">
              {activeProjectId ? `Project Workspace: ${activeProjectId}` : 'Multi-Agent Knowledge Platform'}
            </span>
            <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 border border-emerald-500/20">
              Real Engine Active
            </span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold text-xs">
              MK
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6 bg-muted/10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
