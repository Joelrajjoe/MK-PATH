import { Outlet, NavLink } from 'react-router-dom'
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
  Settings,
  User,
  Moon
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Projects', path: '/projects', icon: FolderOpen },
  { name: 'Data', path: '/data-global', icon: Database }, // Global or project context? The spec says "Sidebar navigation: 1. Overview 2. Projects 3. Data..."
  { name: 'Knowledge', path: '/knowledge-global', icon: BrainCircuit },
  { name: 'Agents', path: '/agents-global', icon: Bot },
  { name: 'Verification', path: '/verification-global', icon: CheckCircle },
  { name: 'Models', path: '/models-global', icon: Network },
  { name: 'Artifacts', path: '/artifacts-global', icon: Package },
  { name: 'Audit', path: '/audit-global', icon: Activity },
  { name: 'Settings', path: '/settings', icon: Settings },
]

export default function Shell() {
  return (
    <div className="flex h-screen w-full flex-col bg-background text-foreground md:flex-row">
      {/* Sidebar */}
      <aside className="hidden w-64 flex-col border-r bg-card md:flex">
        <div className="flex h-14 items-center border-b px-4 lg:h-[60px]">
          <span className="flex items-center gap-2 font-semibold">
            <Network className="h-6 w-6 text-primary" />
            <span className="text-lg tracking-tight">MK-Path</span>
          </span>
        </div>
        <div className="flex-1 overflow-auto py-2">
          <nav className="grid items-start px-2 text-sm font-medium">
            {navItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-muted-foreground transition-all hover:text-primary",
                    isActive ? "bg-muted text-primary" : ""
                  )
                }
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b bg-card px-4 lg:h-[60px]">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-muted-foreground">Global Context</span>
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500">System Healthy</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="rounded-full p-2 hover:bg-muted">
              <Moon className="h-5 w-5 text-muted-foreground" />
            </button>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
              <User className="h-4 w-4" />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
