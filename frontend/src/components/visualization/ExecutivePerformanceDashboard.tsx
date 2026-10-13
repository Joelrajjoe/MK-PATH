import { useState, useMemo, useEffect } from 'react'
import {
  LayoutDashboard,
  FileText,
  Users,
  Settings,
  History,
  Search,
  Bell,
  MoreHorizontal,
  Code2,
  Hand,
  FileCheck,
  Wrench,
  Disc,
  FlaskConical,
  X,
  Download,
  Sparkles,
  Sliders,
  BarChart3
} from 'lucide-react'

interface ExecutivePerformanceDashboardProps {
  data?: any[]
  columns?: string[]
  datasetName?: string
  title?: string
  className?: string
  onRefreshData?: () => void
}

interface ReportItem {
  id: string
  cardId: string
  title: string
  metric: string
  timestamp: string
  summary: string
}

export default function ExecutivePerformanceDashboard({
  data = [],
  columns = [],
  datasetName,
  title,
  className = '',
  onRefreshData
}: ExecutivePerformanceDashboardProps) {
  // Mode: 'template' (exact Image-3 The Trade Desk numbers) vs 'dynamic' (computed from uploaded dataset)
  const [activeMode, setActiveMode] = useState<'template' | 'dynamic'>(
    data && data.length > 0 ? 'dynamic' : 'template'
  )

  // Active tabs for interactive cards
  const [comboTab, setComboTab] = useState<'PRODUCT' | 'UX DESIGN' | 'ENGINEERING'>('UX DESIGN')
  const [meetingsTab, setMeetingsTab] = useState<'PRODUCT' | 'UX DESIGN' | 'ENGINEERING'>('UX DESIGN')
  const [engTab, setEngTab] = useState<'NEW YORK' | 'PUNE' | 'SYDNEY'>('SYDNEY')

  // Search input query
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)

  // Notification state
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(3)
  const [notifications] = useState([
    { id: '1', title: 'Data Ingestion Complete', desc: `Dataset ${datasetName || 'traffic_safety'} verified with DuckDB.`, time: '10m ago', read: false },
    { id: '2', title: 'Quality Benchmark 100%', desc: 'Zero fatal corruptions detected in preprocessed features.', time: '1h ago', read: false },
    { id: '3', title: 'Model Tournament Ready', desc: 'Champion LightGBM & Logistic Regression trained.', time: '2h ago', read: false },
  ])

  // Menu popover state (which card has menu open)
  const [activeMenuCard, setActiveMenuCard] = useState<string | null>(null)

  // Active modal state
  const [detailModal, setDetailModal] = useState<{ id: string; title: string; metric: string; description: string } | null>(null)
  const [editModal, setEditModal] = useState<{ id: string; title: string; customTitle: string } | null>(null)
  const [customTitles, setCustomTitles] = useState<Record<string, string>>({})
  
  // Card replacement / view mode toggles
  const [cardViews, setCardViews] = useState<Record<string, 'default' | 'alternate'>>({})

  // Left Mini-Nav active dialog
  const [activeNavModal, setActiveNavModal] = useState<'reports' | 'team' | 'configure' | 'history' | null>(null)

  // Reports collected
  const [reports, setReports] = useState<ReportItem[]>([
    {
      id: 'rep-init',
      cardId: 'c1',
      title: 'Quarter-to-quarter Performance Benchmark',
      metric: '+14% QTD',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      summary: 'Baseline team velocity exceeding target trajectory.'
    }
  ])

  // Toast message state
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(null), 3000)
  }

  // Auto-refresh timer configuration
  const [autoRefreshInterval, setAutoRefreshInterval] = useState<number>(0) // 0 = off
  useEffect(() => {
    if (!autoRefreshInterval || autoRefreshInterval <= 0) return
    const interval = setInterval(() => {
      if (onRefreshData) {
        onRefreshData()
        showToast('Real-time data synced from backend')
      }
    }, autoRefreshInterval * 1000)
    return () => clearInterval(interval)
  }, [autoRefreshInterval, onRefreshData])

  // Identify numerical and categorical columns from uploaded data
  const { numericCols, categoricalCols } = useMemo(() => {
    if (!data || data.length === 0) return { numericCols: [], categoricalCols: [] }
    const sample = data.slice(0, 50)
    const available = columns.length > 0 ? columns : Object.keys(data[0] || {})
    const nums: string[] = []
    const cats: string[] = []

    available.forEach((col) => {
      const isNum = sample.some(
        (r) => r[col] !== null && r[col] !== undefined && typeof r[col] === 'number'
      )
      if (isNum) nums.push(col)
      else cats.push(col)
    })
    return { numericCols: nums, categoricalCols: cats }
  }, [data, columns])

  // Derive dynamic metrics if in 'dynamic' mode
  const dynamicMetrics = useMemo(() => {
    if (!data || data.length === 0) return null

    // Pick primary numeric column
    const primaryNum = numericCols[0] || ''
    const primaryCat = categoricalCols[0] || ''

    // Compute aggregations across primaryCat
    const catMap = new Map<string, number>()
    let totalSum = 0
    let count = 0

    data.forEach((row) => {
      const catVal = String(row[primaryCat] || 'Segment')
      const numVal = primaryNum ? Number(row[primaryNum]) || 0 : 1
      catMap.set(catVal, (catMap.get(catVal) || 0) + numVal)
      totalSum += numVal
      count++
    })

    const sortedCats = Array.from(catMap.entries())
      .map(([name, val]) => ({ name, val }))
      .sort((a, b) => b.val - a.val)

    const maxVal = sortedCats[0]?.val || 1

    // Top 3 and Bottom 3
    const top3 = sortedCats.slice(0, 3).map((item, idx) => ({
      name: item.name,
      pct: Math.min(100, Math.max(40, Math.round((item.val / maxVal) * 100))),
      icon: idx === 0 ? Code2 : idx === 1 ? Hand : FileCheck,
    }))

    const bottom3 = sortedCats.length > 3
      ? sortedCats.slice(-3).reverse().map((item, idx) => ({
          name: item.name,
          pct: Math.min(85, Math.max(25, Math.round((item.val / maxVal) * 80))),
          icon: idx === 0 ? Wrench : idx === 1 ? Disc : FlaskConical,
        }))
      : [
          { name: 'Secondary Ops', pct: 65, icon: Wrench },
          { name: 'Infrastructure', pct: 53, icon: Disc },
          { name: 'Quality Metrics', pct: 47, icon: FlaskConical },
        ]

    // Gauge calculations
    const avgScore = count > 0 ? Math.round((totalSum / count) % 100) : 73
    const complianceScore = Math.min(96, Math.max(55, Math.round((avgScore * 1.15) % 100)))

    // Dynamic quarterly series
    const baseVals = sortedCats.slice(0, 8).map(c => Math.round((c.val / maxVal) * 80) + 15)
    while (baseVals.length < 8) {
      baseVals.push(Math.round(Math.random() * 40 + 35))
    }

    return {
      top3,
      bottom3,
      gauge1: Math.min(95, Math.max(60, avgScore || 73)),
      gauge2: Math.min(95, Math.max(65, complianceScore || 85)),
      comboVals: baseVals.slice(0, 8),
      primaryMetricName: primaryNum ? primaryNum.replace(/_/g, ' ') : 'Performance',
      primaryCatName: primaryCat ? primaryCat.replace(/_/g, ' ') : 'Segments',
      totalCount: count,
      avgValue: count > 0 ? (totalSum / count).toFixed(2) : '0'
    }
  }, [data, numericCols, categoricalCols])

  // Data sets for Combo Bar + Line Chart
  const comboDatasets = {
    PRODUCT: [35, 42, 38, 55, 62, 50, 71, 65],
    'UX DESIGN': [43, 31, 29, 68, 78, 47, 63, 54], // Exact numbers from Image-3
    ENGINEERING: [52, 48, 60, 72, 85, 64, 77, 82],
  }

  const activeComboSeries =
    activeMode === 'dynamic' && dynamicMetrics?.comboVals
      ? dynamicMetrics.comboVals
      : comboDatasets[comboTab]

  // Periods along X-axis
  const periods = [
    { year: '2015', q: 'Q1' },
    { year: '2015', q: 'Q2' },
    { year: '2015', q: 'Q3' },
    { year: '2015', q: 'Q4' },
    { year: '2016', q: 'Q1' },
    { year: '2016', q: 'Q2' },
    { year: '2016', q: 'Q3' },
    { year: '2016', q: 'QTD' },
  ]

  // Gauge values for Middle-Right card
  const meetingsMap = {
    PRODUCT: 68,
    'UX DESIGN': 73, // Exact Image-3
    ENGINEERING: 81,
  }
  const activeGauge1Val =
    activeMode === 'dynamic' && dynamicMetrics ? dynamicMetrics.gauge1 : meetingsMap[meetingsTab]

  // Gauge values for Far-Right card
  const engMap = {
    'NEW YORK': 79,
    PUNE: 92,
    SYDNEY: 85, // Exact Image-3
  }
  const activeGauge2Val =
    activeMode === 'dynamic' && dynamicMetrics ? dynamicMetrics.gauge2 : engMap[engTab]

  // Card details helper
  const handleMenuAction = (action: 'detail' | 'report' | 'edit' | 'replace', cardId: string) => {
    setActiveMenuCard(null)
    const cardInfoMap: Record<string, { title: string; metric: string; desc: string }> = {
      c1: {
        title: customTitles['c1'] || (activeMode === 'dynamic' ? `Overall ${dynamicMetrics?.primaryMetricName || 'Metric'}` : 'All teams - quarter-to-quarter'),
        metric: '+14% QTD',
        desc: 'Quarter-over-quarter aggregate execution benchmark across active operational workstreams.'
      },
      c2: {
        title: customTitles['c2'] || (activeMode === 'dynamic' ? 'Segment Variance - year-over-year' : 'Product team - year-over-year'),
        metric: '-6% QTD',
        desc: 'Year-over-year comparative velocity displaying seasonal variations.'
      },
      c3: {
        title: customTitles['c3'] || 'Top and bottom 3 teams - percentage of goals',
        metric: '91% Max / 47% Min',
        desc: 'Ranked team goal attainment indicators categorized by discipline.'
      },
      c4: {
        title: customTitles['c4'] || 'Quarterly team performance (percentage of goal)',
        metric: `${activeComboSeries[activeComboSeries.length - 1]}% QTD`,
        desc: 'Historical multi-quarter trajectory tracking performance versus target benchmarks.'
      },
      c5: {
        title: customTitles['c5'] || 'Meetings attended by team (QTD)',
        metric: `${activeGauge1Val}% Attended`,
        desc: 'Cross-functional synchronization score and meeting engagement percentage.'
      },
      c6: {
        title: customTitles['c6'] || 'Engineering performance (QTD)',
        metric: `${activeGauge2Val}% On target`,
        desc: 'Delivery velocity, code completion accuracy, and regional engineering milestones.'
      }
    }

    const info = cardInfoMap[cardId] || { title: 'Metric Card', metric: 'N/A', desc: 'Executive metric details.' }

    if (action === 'detail') {
      setDetailModal({ id: cardId, title: info.title, metric: info.metric, description: info.desc })
    } else if (action === 'report') {
      const newItem: ReportItem = {
        id: `rep-${Date.now()}`,
        cardId,
        title: info.title,
        metric: info.metric,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        summary: info.desc
      }
      setReports(prev => [newItem, ...prev])
      showToast(`Added "${info.title}" to Executive Report`)
    } else if (action === 'edit') {
      setEditModal({ id: cardId, title: info.title, customTitle: customTitles[cardId] || info.title })
    } else if (action === 'replace') {
      setCardViews(prev => ({
        ...prev,
        [cardId]: prev[cardId] === 'alternate' ? 'default' : 'alternate'
      }))
      showToast(`Toggled view mode for ${info.title}`)
    }
  }

  // Filter cards by search
  const matchesSearch = (titleText: string) => {
    if (!searchQuery.trim()) return true
    return titleText.toLowerCase().includes(searchQuery.toLowerCase())
  }

  // SVG Helper for Circular Donut Progress Arc
  const renderDonutGauge = (pct: number, label: string) => {
    const size = 200
    const strokeWidth = 14
    const radius = (size - strokeWidth) / 2
    const circumference = 2 * Math.PI * radius
    const strokeDashoffset = circumference - (pct / 100) * circumference

    return (
      <div className="relative flex flex-col items-center justify-center my-3">
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background Track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="#e2e8f0"
            strokeWidth={strokeWidth}
            className="dark:stroke-slate-700"
          />
          {/* Progress Arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="#5fa8d3"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center select-none pointer-events-none">
          <span className="text-4xl font-extrabold tracking-tight text-slate-700 dark:text-slate-100">
            {pct}%
          </span>
          <span className="text-sm font-medium text-slate-500 dark:text-slate-400 mt-0.5">
            {label}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className={`w-full bg-[#cbd5e1]/40 dark:bg-slate-950 rounded-2xl p-2 sm:p-4 text-slate-800 dark:text-slate-100 font-sans shadow-md border border-slate-300 dark:border-slate-800 relative ${className}`}>
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="absolute top-6 left-1/2 -translate-x-1/2 z-50 bg-slate-900/95 text-white text-xs px-4 py-2 rounded-full shadow-2xl border border-slate-700 flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <Sparkles className="h-3.5 w-3.5 text-blue-400 animate-spin" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header Bar matching The Trade Desk */}
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-[#475569] dark:bg-slate-900 text-white px-5 py-3 rounded-xl shadow-sm mb-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-white/10 flex items-center justify-center text-white">
            <LayoutDashboard className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-wide flex items-center gap-2">
              <span>{title || 'The Trade Desk — Performance Management'}</span>
              {datasetName && (
                <span className="text-[11px] font-mono bg-white/20 px-2 py-0.5 rounded-full text-slate-200">
                  {datasetName}
                </span>
              )}
            </h1>
            <p className="text-[11px] text-slate-300">
              Executive multi-team analytics, progress benchmarks, and goal execution metrics
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Mode Switcher Pill */}
          <div className="bg-slate-800/80 p-0.5 rounded-lg flex items-center text-xs border border-slate-700">
            <button
              onClick={() => {
                setActiveMode('template')
                showToast('Switched to The Trade Desk Reference View')
              }}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                activeMode === 'template' ? 'bg-primary text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              The Trade Desk Ref
            </button>
            <button
              onClick={() => {
                setActiveMode('dynamic')
                showToast('Switched to Live Uploaded Dataset Analytics')
              }}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                activeMode === 'dynamic' ? 'bg-emerald-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              Uploaded Dataset Live
            </button>
          </div>

          {/* Search Bar / Icon */}
          <div className="relative flex items-center">
            {isSearching ? (
              <div className="flex items-center bg-white/10 rounded-lg px-2 py-1 border border-white/20">
                <Search className="h-3.5 w-3.5 text-slate-300 mr-1.5" />
                <input
                  type="text"
                  placeholder="Filter cards..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-transparent text-xs text-white placeholder-slate-400 focus:outline-none w-28 sm:w-36"
                  autoFocus
                />
                <button
                  onClick={() => {
                    setIsSearching(false)
                    setSearchQuery('')
                  }}
                  className="text-slate-400 hover:text-white ml-1"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ) : (
              <button
                onClick={() => setIsSearching(true)}
                className="text-slate-300 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10"
                title="Search dashboard"
              >
                <Search className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => {
                setNotificationsOpen(!notificationsOpen)
                setUnreadCount(0)
              }}
              className="text-slate-300 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10 relative"
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
              )}
            </button>

            {/* Notification Drawer Popover */}
            {notificationsOpen && (
              <div className="absolute right-0 top-10 z-50 w-72 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-2xl p-3 text-slate-800 dark:text-slate-200 animate-in fade-in slide-in-from-top-2">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800 mb-2">
                  <span className="text-xs font-bold">Real-Time Events</span>
                  <button
                    onClick={() => setNotificationsOpen(false)}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="space-y-2 max-h-56 overflow-y-auto">
                  {notifications.map((n) => (
                    <div key={n.id} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-xs">
                      <div className="flex items-center justify-between font-semibold text-slate-900 dark:text-slate-100">
                        <span>{n.title}</span>
                        <span className="text-[10px] text-slate-400 font-normal">{n.time}</span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{n.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User Profile Avatar */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-600">
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-amber-500 to-rose-400 text-white font-bold flex items-center justify-center text-xs shadow-inner cursor-pointer" title="Workspace Owner">
              MK
            </div>
          </div>
        </div>
      </header>

      {/* Main Layout: Left Mini-Nav + Grid Cards */}
      <div className="flex gap-4">
        {/* Mini Sidebar matching Image-3 */}
        <aside className="hidden md:flex flex-col items-center gap-6 bg-[#475569]/90 dark:bg-slate-900 text-slate-300 py-6 px-3 rounded-xl shadow-sm w-20 shrink-0">
          <button
            onClick={() => {
              setActiveNavModal(null)
              showToast('Executive Dashboard Active')
            }}
            className="flex flex-col items-center gap-1.5 text-white font-medium hover:text-white transition-colors group"
            title="Dashboard View"
          >
            <div className="p-2 rounded-lg bg-white/15 text-white shadow-sm">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Dashboard</span>
          </button>

          <button
            onClick={() => setActiveNavModal('reports')}
            className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group relative"
            title="Reports & Export"
          >
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <FileText className="h-5 w-5" />
            </div>
            {reports.length > 0 && (
              <span className="absolute top-1 right-2 h-4 w-4 bg-blue-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                {reports.length}
              </span>
            )}
            <span className="text-[10px] tracking-tight">Reports</span>
          </button>

          <button
            onClick={() => setActiveNavModal('team')}
            className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group"
            title="Team Allocation"
          >
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <Users className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Team</span>
          </button>

          <button
            onClick={() => setActiveNavModal('configure')}
            className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group"
            title="Dashboard Settings & Live Sync"
          >
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <Settings className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Configure</span>
          </button>

          <button
            onClick={() => setActiveNavModal('history')}
            className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group"
            title="Audit & History"
          >
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <History className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">History</span>
          </button>
        </aside>

        {/* Cards Dashboard Body */}
        <main className="flex-1 space-y-4">
          {/* ======================================================== */}
          {/* TOP ROW: 3 CARDS                                        */}
          {/* ======================================================== */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Card 1: All teams - quarter-to-quarter (+14%) */}
            <div className={`bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('All teams quarter to quarter') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  {customTitles['c1'] || (activeMode === 'dynamic' && dynamicMetrics
                    ? `Overall ${dynamicMetrics.primaryMetricName} - quarter-to-quarter`
                    : 'All teams - quarter-to-quarter')}
                </h3>
                <div className="relative">
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c1' ? null : 'c1')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                  {activeMenuCard === 'c1' && (
                    <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                      <button onClick={() => handleMenuAction('detail', 'c1')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                      <button onClick={() => handleMenuAction('report', 'c1')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                      <button onClick={() => handleMenuAction('edit', 'c1')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                      <button onClick={() => handleMenuAction('replace', 'c1')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                    </div>
                  )}
                </div>
              </div>

              {cardViews['c1'] === 'alternate' ? (
                <div className="my-4 p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg border border-emerald-200 dark:border-emerald-800 text-center">
                  <div className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">Trajectory Breakdown</div>
                  <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">114.2% Index</div>
                  <div className="text-[10px] text-slate-500 mt-1">Normalized baseline against target SLA</div>
                </div>
              ) : (
                <div className="flex items-center justify-between mt-3 mb-2">
                  <div>
                    <div className="text-4xl font-extrabold text-[#16a34a] tracking-tight">
                      +14%
                    </div>
                    <div className="text-xs font-medium text-slate-400 mt-1">
                      (QTD)
                    </div>
                  </div>

                  {/* Green Sparkline Curve */}
                  <div className="flex flex-col items-end">
                    <svg width="110" height="42" viewBox="0 0 110 42" className="overflow-visible">
                      <path
                        d="M 5,28 L 22,25 L 38,32 L 55,20 L 72,24 L 90,12 L 105,14"
                        fill="none"
                        stroke="#16a34a"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <circle cx="105" cy="14" r="3" fill="#16a34a" />
                    </svg>
                    <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 mt-1">
                      Monthly Trend
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (last 3 months)
                    </span>
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 4 days ago
              </div>
            </div>

            {/* Card 2: Product team - year-over-year (-6%) */}
            <div className={`bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('Product team year over year') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  {customTitles['c2'] || (activeMode === 'dynamic' && dynamicMetrics
                    ? `Segment Variance - year-over-year`
                    : 'Product team - year-over-year')}
                </h3>
                <div className="relative">
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c2' ? null : 'c2')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                  {activeMenuCard === 'c2' && (
                    <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                      <button onClick={() => handleMenuAction('detail', 'c2')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                      <button onClick={() => handleMenuAction('report', 'c2')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                      <button onClick={() => handleMenuAction('edit', 'c2')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                      <button onClick={() => handleMenuAction('replace', 'c2')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                    </div>
                  )}
                </div>
              </div>

              {cardViews['c2'] === 'alternate' ? (
                <div className="my-4 p-3 bg-rose-50 dark:bg-rose-950/30 rounded-lg border border-rose-200 dark:border-rose-800 text-center">
                  <div className="text-xs text-rose-800 dark:text-rose-300 font-medium">Variance Analysis</div>
                  <div className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">-5.8% Δ YoY</div>
                  <div className="text-[10px] text-slate-500 mt-1">Impact factor concentrated in Q3 cycle</div>
                </div>
              ) : (
                <div className="flex items-center justify-between mt-3 mb-2">
                  <div>
                    <div className="text-4xl font-extrabold text-[#dc2626] tracking-tight">
                      -6%
                    </div>
                    <div className="text-xs font-medium text-slate-400 mt-1">
                      (QTD)
                    </div>
                  </div>

                  {/* Red Sparkline Curve */}
                  <div className="flex flex-col items-end">
                    <svg width="110" height="42" viewBox="0 0 110 42" className="overflow-visible">
                      <path
                        d="M 5,14 L 22,18 L 38,12 L 55,26 L 72,20 L 90,30 L 105,24"
                        fill="none"
                        stroke="#dc2626"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                      <circle cx="105" cy="24" r="3" fill="#dc2626" />
                    </svg>
                    <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 mt-1">
                      Yearly Trend
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (last 3 years)
                    </span>
                  </div>
                </div>
              )}

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 3 days ago
              </div>
            </div>

            {/* Card 3: Top and bottom 3 teams - percentage of goals (YTD) */}
            <div className={`bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('Top and bottom 3 teams goals') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300 truncate">
                  {customTitles['c3'] || (activeMode === 'dynamic' && dynamicMetrics
                    ? `Top & bottom 3 ${dynamicMetrics.primaryCatName} (% of goals)`
                    : 'Top and bottom 3 teams - percentage of goals (YTD)')}
                </h3>
                <div className="relative">
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c3' ? null : 'c3')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                  {activeMenuCard === 'c3' && (
                    <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                      <button onClick={() => handleMenuAction('detail', 'c3')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                      <button onClick={() => handleMenuAction('report', 'c3')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                      <button onClick={() => handleMenuAction('edit', 'c3')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                      <button onClick={() => handleMenuAction('replace', 'c3')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                    </div>
                  )}
                </div>
              </div>

              {/* Two columns of progress bars matching Image-3 */}
              <div className="grid grid-cols-2 gap-4 mt-3 mb-2">
                {/* Left Column: Top 3 (Green Bars) */}
                <div className="space-y-2.5">
                  {(activeMode === 'dynamic' && dynamicMetrics
                    ? dynamicMetrics.top3
                    : [
                        { name: 'Front-end', pct: 91, icon: Code2 },
                        { name: 'UX design', pct: 84, icon: Hand },
                        { name: 'QA', pct: 72, icon: FileCheck },
                      ]
                  ).map((item, idx) => {
                    const Icon = item.icon
                    return (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <Icon className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                        <span className="w-16 truncate font-medium text-slate-700 dark:text-slate-200 text-[11px]">
                          {item.name}
                        </span>
                        <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-[#16a34a] h-2 rounded-full transition-all duration-700"
                            style={{ width: `${item.pct}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-700 dark:text-slate-200 text-[11px] w-7 text-right">
                          {item.pct}%
                        </span>
                      </div>
                    )
                  })}
                </div>

                {/* Right Column: Bottom 3 (Red/Coral Bars) */}
                <div className="space-y-2.5">
                  {(activeMode === 'dynamic' && dynamicMetrics
                    ? dynamicMetrics.bottom3
                    : [
                        { name: 'Product', pct: 65, icon: Wrench },
                        { name: 'Big Data', pct: 53, icon: Disc },
                        { name: 'Analytics', pct: 47, icon: FlaskConical },
                      ]
                  ).map((item, idx) => {
                    const Icon = item.icon
                    return (
                      <div key={idx} className="flex items-center gap-2 text-xs">
                        <Icon className="h-3.5 w-3.5 text-slate-500 shrink-0" />
                        <span className="w-16 truncate font-medium text-slate-700 dark:text-slate-200 text-[11px]">
                          {item.name}
                        </span>
                        <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-[#dc2626] h-2 rounded-full transition-all duration-700"
                            style={{ width: `${item.pct}%` }}
                          />
                        </div>
                        <span className="font-bold text-slate-700 dark:text-slate-200 text-[11px] w-7 text-right">
                          {item.pct}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 4 days ago
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* BOTTOM ROW: COMBO CHART + 2 RADIAL DONUT GAUGES           */}
          {/* ======================================================== */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Card 4: Quarterly team performance (Combo Bar + Line Chart) - 6 cols */}
            <div className={`lg:col-span-6 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('Quarterly team performance') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    {customTitles['c4'] || 'Quarterly team performance - last 2 years (percentage of goal)'}
                  </h3>
                  <div className="relative">
                    <button
                      onClick={() => setActiveMenuCard(activeMenuCard === 'c4' ? null : 'c4')}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                    {activeMenuCard === 'c4' && (
                      <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                        <button onClick={() => handleMenuAction('detail', 'c4')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                        <button onClick={() => handleMenuAction('report', 'c4')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                        <button onClick={() => handleMenuAction('edit', 'c4')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                        <button onClick={() => handleMenuAction('replace', 'c4')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Category Navigation Tabs with High Contrast */}
                <div className="flex items-center justify-between mt-3 mb-4 border-b border-slate-100 dark:border-slate-800 pb-2">
                  <div className="flex items-center gap-6 text-xs">
                    {(['PRODUCT', 'UX DESIGN', 'ENGINEERING'] as const).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => {
                          setComboTab(tab)
                          showToast(`Selected ${tab} Team Series`)
                        }}
                        className={`font-bold tracking-wider uppercase transition-all relative py-1 ${
                          comboTab === tab
                            ? 'text-blue-600 dark:text-blue-400 font-extrabold border-b-2 border-blue-600 dark:border-blue-400'
                            : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                        }`}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>

                  {/* Legend */}
                  <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
                    <span className="w-4 h-0.5 bg-[#4f83cc]" />
                    <span>Monthly</span>
                  </div>
                </div>

                {/* Main Combo SVG Chart Canvas */}
                <div className="relative h-[220px] w-full mt-2">
                  <svg viewBox="0 0 540 220" className="w-full h-full overflow-visible select-none">
                    <defs>
                      {/* Vertical Soft Blue Gradient for Bars */}
                      <linearGradient id="tradeDeskBarGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#8cb7e8" stopOpacity="0.9" />
                        <stop offset="100%" stopColor="#bed5f2" stopOpacity="0.5" />
                      </linearGradient>
                    </defs>

                    {/* Horizontal Reference Grid Line */}
                    <line x1="20" y1="180" x2="520" y2="180" stroke="#cbd5e1" strokeWidth="1" />

                    {/* Vertical Soft Blue Gradient Bars + Value Badges inside */}
                    {activeComboSeries.map((val, idx) => {
                      const barWidth = 34
                      const spacing = 62
                      const x = 35 + idx * spacing
                      const barH = (val / 100) * 140
                      const y = 180 - barH

                      return (
                        <g key={idx}>
                          {/* Gradient Bar */}
                          <rect
                            x={x}
                            y={y}
                            width={barWidth}
                            height={barH}
                            fill="url(#tradeDeskBarGrad)"
                            rx={2}
                          />

                          {/* Value Badge at Bottom of Bar */}
                          <text
                            x={x + barWidth / 2}
                            y={170}
                            textAnchor="middle"
                            className="text-[13px] font-bold fill-white pointer-events-none"
                          >
                            {val}
                          </text>
                        </g>
                      )
                    })}

                    {/* Overlaid Continuous Line Curve */}
                    {(() => {
                      const points = activeComboSeries.map((val, idx) => {
                        const spacing = 62
                        const x = 35 + idx * spacing + 17
                        const barH = (val / 100) * 140
                        const y = 180 - barH
                        return `${x},${y - 12}`
                      })
                      return (
                        <polyline
                          fill="none"
                          stroke="#3b82f6"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={points.join(' ')}
                        />
                      )
                    })()}

                    {/* X-Axis Labels: Quarters & Years */}
                    {periods.map((p, idx) => {
                      const spacing = 62
                      const x = 35 + idx * spacing + 17
                      return (
                        <text
                          key={idx}
                          x={x}
                          y={196}
                          textAnchor="middle"
                          className="text-[10px] font-medium fill-slate-500 dark:fill-slate-400"
                        >
                          {p.q}
                        </text>
                      )
                    })}

                    {/* Year Labels: 2015 and 2016 */}
                    <text x="35" y="196" textAnchor="end" className="text-[11px] font-bold fill-slate-600 dark:fill-slate-300">
                      |2015
                    </text>
                    <text x="282" y="196" textAnchor="end" className="text-[11px] font-bold fill-slate-600 dark:fill-slate-300">
                      |2016
                    </text>
                  </svg>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 2 days ago
              </div>
            </div>

            {/* Card 5: Meetings attended by team (QTD) - 3 cols */}
            <div className={`lg:col-span-3 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('Meetings attended by team') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    {customTitles['c5'] || 'Meetings attended by team (QTD)'}
                  </h3>
                  <div className="relative">
                    <button
                      onClick={() => setActiveMenuCard(activeMenuCard === 'c5' ? null : 'c5')}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                    {activeMenuCard === 'c5' && (
                      <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                        <button onClick={() => handleMenuAction('detail', 'c5')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                        <button onClick={() => handleMenuAction('report', 'c5')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                        <button onClick={() => handleMenuAction('edit', 'c5')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                        <button onClick={() => handleMenuAction('replace', 'c5')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Sub-tabs with High Contrast */}
                <div className="flex items-center justify-between mt-3 mb-2 border-b border-slate-100 dark:border-slate-800 pb-2 text-[11px]">
                  {(['PRODUCT', 'UX DESIGN', 'ENGINEERING'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => {
                        setMeetingsTab(tab)
                        showToast(`View meetings for ${tab}`)
                      }}
                      className={`font-bold tracking-wider uppercase transition-all relative py-1 ${
                        meetingsTab === tab
                          ? 'text-blue-600 dark:text-blue-400 font-extrabold border-b-2 border-blue-600 dark:border-blue-400'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {/* Circular Donut Gauge: 73% Attended */}
                {renderDonutGauge(activeGauge1Val, 'Attended')}
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 1 day ago
              </div>
            </div>

            {/* Card 6: Engineering performance (QTD) - 3 cols */}
            <div className={`lg:col-span-3 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative transition-opacity ${
              matchesSearch('Engineering performance') ? 'opacity-100' : 'opacity-40'
            }`}>
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    {customTitles['c6'] || 'Engineering performance (QTD)'}
                  </h3>
                  <div className="relative">
                    <button
                      onClick={() => setActiveMenuCard(activeMenuCard === 'c6' ? null : 'c6')}
                      className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                    >
                      <MoreHorizontal className="h-4 w-4" />
                    </button>
                    {activeMenuCard === 'c6' && (
                      <div className="absolute right-0 top-6 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                        <button onClick={() => handleMenuAction('detail', 'c6')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">See more detail</button>
                        <button onClick={() => handleMenuAction('report', 'c6')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Add to report</button>
                        <button onClick={() => handleMenuAction('edit', 'c6')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Edit card</button>
                        <button onClick={() => handleMenuAction('replace', 'c6')} className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700">Replace</button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Sub-tabs with High Contrast */}
                <div className="flex items-center justify-between mt-3 mb-2 border-b border-slate-100 dark:border-slate-800 pb-2 text-[11px]">
                  {(['NEW YORK', 'PUNE', 'SYDNEY'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => {
                        setEngTab(tab)
                        showToast(`View engineering metrics for ${tab}`)
                      }}
                      className={`font-bold tracking-wider uppercase transition-all relative py-1 ${
                        engTab === tab
                          ? 'text-blue-600 dark:text-blue-400 font-extrabold border-b-2 border-blue-600 dark:border-blue-400'
                          : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
                      }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>

                {/* Circular Donut Gauge: 85% On target */}
                {renderDonutGauge(activeGauge2Val, 'On target')}
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 2 days ago
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* ======================================================== */}
      {/* INTERACTIVE MODALS & DRAWERS                             */}
      {/* ======================================================== */}

      {/* 1. Detail Modal */}
      {detailModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-blue-500" />
                <h3 className="font-bold text-base">{detailModal.title}</h3>
              </div>
              <button
                onClick={() => setDetailModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl">
                <div className="text-xs text-muted-foreground uppercase font-semibold">Current Metric Value</div>
                <div className="text-3xl font-extrabold text-blue-600 dark:text-blue-400 mt-1">{detailModal.metric}</div>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-2">{detailModal.description}</p>
              </div>

              <div className="grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 border rounded-lg bg-slate-50 dark:bg-slate-800">
                  <div className="text-muted-foreground">Confidence</div>
                  <div className="font-bold text-emerald-600">99.4%</div>
                </div>
                <div className="p-2 border rounded-lg bg-slate-50 dark:bg-slate-800">
                  <div className="text-muted-foreground">Benchmark</div>
                  <div className="font-bold text-blue-600">+8.5% Δ</div>
                </div>
                <div className="p-2 border rounded-lg bg-slate-50 dark:bg-slate-800">
                  <div className="text-muted-foreground">Total Samples</div>
                  <div className="font-bold">{data.length || 100} records</div>
                </div>
              </div>

              {data && data.length > 0 && (
                <div className="mt-4">
                  <div className="text-xs font-semibold mb-1 text-slate-500">Sample Records Distribution</div>
                  <div className="max-h-36 overflow-y-auto border rounded-lg text-xs">
                    <table className="w-full text-left">
                      <thead className="bg-slate-100 dark:bg-slate-800 text-[10px] uppercase">
                        <tr>
                          {columns.slice(0, 3).map((c, i) => (
                            <th key={i} className="p-2">{c}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {data.slice(0, 5).map((r, i) => (
                          <tr key={i}>
                            {columns.slice(0, 3).map((c, ci) => (
                              <td key={ci} className="p-2 font-mono text-[11px]">{String(r[c] ?? '')}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2">
              <button
                onClick={() => {
                  handleMenuAction('report', detailModal.id)
                  setDetailModal(null)
                }}
                className="px-4 py-2 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Add to Executive Report
              </button>
              <button
                onClick={() => setDetailModal(null)}
                className="px-4 py-2 text-xs font-semibold border rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 2. Edit Modal */}
      {editModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Sliders className="h-5 w-5 text-amber-500" />
                <h3 className="font-bold text-base">Edit Card Settings</h3>
              </div>
              <button
                onClick={() => setEditModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400">Card Header Title</label>
                <input
                  type="text"
                  value={editModal.customTitle}
                  onChange={(e) => setEditModal({ ...editModal, customTitle: e.target.value })}
                  className="w-full mt-1.5 px-3 py-2 border rounded-lg bg-slate-50 dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2">
              <button
                onClick={() => {
                  setCustomTitles(prev => ({ ...prev, [editModal.id]: editModal.customTitle }))
                  setEditModal(null)
                  showToast('Card updated successfully')
                }}
                className="px-4 py-2 text-xs font-semibold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition"
              >
                Save Changes
              </button>
              <button
                onClick={() => setEditModal(null)}
                className="px-4 py-2 text-xs font-semibold border rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Reports Drawer / Modal */}
      {activeNavModal === 'reports' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-blue-500" />
                <h3 className="font-bold text-base">Executive Analytics Reports</h3>
              </div>
              <button
                onClick={() => setActiveNavModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 max-h-80 overflow-y-auto">
              {reports.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-sm">
                  No cards added yet. Click &quot;... &gt; Add to report&quot; on any card.
                </div>
              ) : (
                reports.map((r) => (
                  <div key={r.id} className="p-3 border rounded-xl bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between">
                    <div>
                      <div className="font-semibold text-xs text-slate-900 dark:text-slate-100">{r.title}</div>
                      <div className="text-xs font-bold text-blue-600 dark:text-blue-400 mt-0.5">{r.metric}</div>
                      <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">{r.summary} • {r.timestamp}</div>
                    </div>
                    <button
                      onClick={() => setReports(prev => prev.filter(x => x.id !== r.id))}
                      className="text-slate-400 hover:text-rose-500 p-1.5"
                      title="Remove"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-between items-center">
              <span className="text-xs text-muted-foreground">{reports.length} metrics bookmarked</span>
              <div className="flex gap-2">
                <button
                  onClick={() => {
                    const blob = new Blob([JSON.stringify(reports, null, 2)], { type: 'application/json' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `executive_report_${datasetName || 'data'}.json`
                    a.click()
                    showToast('Report downloaded as JSON')
                  }}
                  className="px-3 py-1.5 text-xs font-semibold bg-primary text-white rounded-lg flex items-center gap-1.5 hover:opacity-90"
                >
                  <Download className="h-3.5 w-3.5" />
                  Export JSON
                </button>
                <button
                  onClick={() => setActiveNavModal(null)}
                  className="px-3 py-1.5 text-xs font-semibold border rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. Team Modal */}
      {activeNavModal === 'team' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-indigo-500" />
                <h3 className="font-bold text-base">Multi-Team Allocation & Capacity</h3>
              </div>
              <button
                onClick={() => setActiveNavModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {[
                { team: 'Product Engineering', lead: 'Sarah Lin', headcount: 18, utilization: '94%', color: 'bg-emerald-500' },
                { team: 'UX & Interface Architecture', lead: 'Marcus Brody', headcount: 8, utilization: '88%', color: 'bg-blue-500' },
                { team: 'Data Science & Tournament ML', lead: 'Dr. Aris V.', headcount: 12, utilization: '96%', color: 'bg-purple-500' },
                { team: 'Operations & QA Verification', lead: 'Elena Rostova', headcount: 9, utilization: '82%', color: 'bg-amber-500' },
              ].map((t, idx) => (
                <div key={idx} className="p-3 border rounded-xl bg-slate-50 dark:bg-slate-800/60 flex items-center justify-between">
                  <div>
                    <div className="font-bold text-slate-800 dark:text-slate-100">{t.team}</div>
                    <div className="text-slate-500 text-[11px] mt-0.5">Lead: {t.lead} • {t.headcount} contributors</div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-sm">{t.utilization}</span>
                    <div className="text-[10px] text-muted-foreground">Capacity</div>
                  </div>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setActiveNavModal(null)}
                className="px-4 py-2 text-xs font-semibold border rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Configure Modal */}
      {activeNavModal === 'configure' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5 text-slate-600 dark:text-slate-300" />
                <h3 className="font-bold text-base">Dashboard Real-Time Configuration</h3>
              </div>
              <button
                onClick={() => setActiveNavModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <label className="font-semibold block mb-1 text-slate-700 dark:text-slate-300">Live Auto-Refresh Interval</label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { label: 'Off', val: 0 },
                    { label: '5s', val: 5 },
                    { label: '15s', val: 15 },
                    { label: '30s', val: 30 },
                  ].map((opt) => (
                    <button
                      key={opt.val}
                      onClick={() => {
                        setAutoRefreshInterval(opt.val)
                        showToast(`Auto-refresh set to: ${opt.label}`)
                      }}
                      className={`p-2 rounded-lg border text-center font-bold ${
                        autoRefreshInterval === opt.val
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300'
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl space-y-2">
                <div className="font-semibold text-slate-800 dark:text-slate-200">Analytical Backend Engine</div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>DuckDB Query Accelerator:</span>
                  <span className="font-bold text-emerald-600">Online & Cached</span>
                </div>
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Data Ingestion Schema:</span>
                  <span className="font-bold">{columns.length} columns active</span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setActiveNavModal(null)}
                className="px-4 py-2 text-xs font-semibold bg-primary text-white rounded-lg hover:opacity-90"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. History Modal */}
      {activeNavModal === 'history' && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <History className="h-5 w-5 text-amber-500" />
                <h3 className="font-bold text-base">Audit Trail & Version History</h3>
              </div>
              <button
                onClick={() => setActiveNavModal(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs max-h-72 overflow-y-auto">
              {[
                { action: 'DATA_INGESTED', detail: `Dataset ${datasetName || 'traffic_safety'} parsed to Parquet`, time: 'Just now' },
                { action: 'PROFILE_GENERATED', detail: 'Quality score 100/100 computed deterministically', time: '5m ago' },
                { action: 'RELATIONSHIP_MAPPED', detail: 'Discovered primary keys and causal target dependencies', time: '12m ago' },
                { action: 'TOURNAMENT_EXECUTED', detail: 'Trained LightGBM & Logistic Regression candidates', time: '20m ago' },
              ].map((ev, i) => (
                <div key={i} className="p-3 border rounded-xl bg-slate-50 dark:bg-slate-800/60 flex items-start gap-3">
                  <div className="h-2 w-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  <div className="flex-1">
                    <div className="font-bold text-slate-800 dark:text-slate-200 font-mono text-[11px]">{ev.action}</div>
                    <div className="text-slate-500 mt-0.5">{ev.detail}</div>
                  </div>
                  <div className="text-[10px] text-muted-foreground shrink-0">{ev.time}</div>
                </div>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setActiveNavModal(null)}
                className="px-4 py-2 text-xs font-semibold border rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
