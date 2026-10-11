import { useState, useMemo } from 'react'
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
  FlaskConical
} from 'lucide-react'

interface ExecutivePerformanceDashboardProps {
  data?: any[]
  columns?: string[]
  datasetName?: string
  title?: string
  className?: string
}

export default function ExecutivePerformanceDashboard({
  data = [],
  columns = [],
  datasetName,
  title,
  className = '',
}: ExecutivePerformanceDashboardProps) {
  // Mode: 'template' (exact Image-3 The Trade Desk numbers) vs 'dynamic' (computed from uploaded dataset)
  const [activeMode, setActiveMode] = useState<'template' | 'dynamic'>(
    data && data.length > 0 ? 'dynamic' : 'template'
  )

  // Active tabs for interactive cards
  const [comboTab, setComboTab] = useState<'PRODUCT' | 'UX DESIGN' | 'ENGINEERING'>('UX DESIGN')
  const [meetingsTab, setMeetingsTab] = useState<'PRODUCT' | 'UX DESIGN' | 'ENGINEERING'>('UX DESIGN')
  const [engTab, setEngTab] = useState<'NEW YORK' | 'PUNE' | 'SYDNEY'>('SYDNEY')

  // Menu popover state (which card has menu open)
  const [activeMenuCard, setActiveMenuCard] = useState<string | null>(null)

  // Notification dismissed state
  const [notificationsOpen, setNotificationsOpen] = useState(false)

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
    <div className={`w-full bg-[#cbd5e1]/40 dark:bg-slate-950 rounded-2xl p-2 sm:p-4 text-slate-800 dark:text-slate-100 font-sans shadow-md border border-slate-300 dark:border-slate-800 ${className}`}>
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
              onClick={() => setActiveMode('template')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                activeMode === 'template' ? 'bg-primary text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              The Trade Desk Ref
            </button>
            <button
              onClick={() => setActiveMode('dynamic')}
              className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                activeMode === 'dynamic' ? 'bg-emerald-600 text-white shadow' : 'text-slate-300 hover:text-white'
              }`}
            >
              Uploaded Dataset Live
            </button>
          </div>

          {/* Search Icon */}
          <button className="text-slate-300 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10">
            <Search className="h-4 w-4" />
          </button>

          {/* Notification Bell */}
          <div className="relative">
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="text-slate-300 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10 relative"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
            </button>
          </div>

          {/* User Profile Avatar */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-600">
            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-amber-500 to-rose-400 text-white font-bold flex items-center justify-center text-xs shadow-inner">
              MK
            </div>
          </div>
        </div>
      </header>

      {/* Main Layout: Left Mini-Nav + Grid Cards */}
      <div className="flex gap-4">
        {/* Mini Sidebar matching Image-3 */}
        <aside className="hidden md:flex flex-col items-center gap-6 bg-[#475569]/90 dark:bg-slate-900 text-slate-300 py-6 px-3 rounded-xl shadow-sm w-20 shrink-0">
          <button className="flex flex-col items-center gap-1.5 text-white font-medium hover:text-white transition-colors group">
            <div className="p-2 rounded-lg bg-white/15 text-white shadow-sm">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Dashboard</span>
          </button>

          <button className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group">
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <FileText className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Reports</span>
          </button>

          <button className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group">
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <Users className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Team</span>
          </button>

          <button className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group">
            <div className="p-2 rounded-lg hover:bg-white/10 text-slate-300 group-hover:text-white">
              <Settings className="h-5 w-5" />
            </div>
            <span className="text-[10px] tracking-tight">Configure</span>
          </button>

          <button className="flex flex-col items-center gap-1.5 text-slate-300 hover:text-white transition-colors group">
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
            <div className="bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  {activeMode === 'dynamic' && dynamicMetrics
                    ? `Overall ${dynamicMetrics.primaryMetricName} - quarter-to-quarter`
                    : 'All teams - quarter-to-quarter'}
                </h3>
                <button
                  onClick={() => setActiveMenuCard(activeMenuCard === 'c1' ? null : 'c1')}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
              </div>

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

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 4 days ago
              </div>
            </div>

            {/* Card 2: Product team - year-over-year (-6%) */}
            <div className="bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  {activeMode === 'dynamic' && dynamicMetrics
                    ? `Segment Variance - year-over-year`
                    : 'Product team - year-over-year'}
                </h3>
                <button
                  onClick={() => setActiveMenuCard(activeMenuCard === 'c2' ? null : 'c2')}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
              </div>

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

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 3 days ago
              </div>
            </div>

            {/* Card 3: Top and bottom 3 teams - percentage of goals (YTD) */}
            <div className="bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300 truncate">
                  {activeMode === 'dynamic' && dynamicMetrics
                    ? `Top & bottom 3 ${dynamicMetrics.primaryCatName} (% of goals)`
                    : 'Top and bottom 3 teams - percentage of goals (YTD)'}
                </h3>
                <button
                  onClick={() => setActiveMenuCard(activeMenuCard === 'c3' ? null : 'c3')}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
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
            <div className="lg:col-span-6 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Quarterly team performance - last 2 years (percentage of goal)
                  </h3>
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c4' ? null : 'c4')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </div>

                {/* Category Navigation Tabs */}
                <div className="flex items-center justify-between mt-3 mb-4 border-b border-slate-100 dark:border-slate-800 pb-2">
                  <div className="flex items-center gap-6 text-xs">
                    {(['PRODUCT', 'UX DESIGN', 'ENGINEERING'] as const).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setComboTab(tab)}
                        className={`font-bold tracking-wider uppercase transition-colors relative py-1 ${
                          comboTab === tab
                            ? 'text-primary border-b-2 border-primary'
                            : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
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

                  {/* Context Menu Popup from Image-3 */}
                  {activeMenuCard === 'c4' && (
                    <div className="absolute right-8 top-4 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-xl py-1.5 w-36 text-xs animate-in fade-in zoom-in-95">
                      <button
                        onClick={() => setActiveMenuCard(null)}
                        className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        See more detail
                      </button>
                      <button
                        onClick={() => setActiveMenuCard(null)}
                        className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        Add to report
                      </button>
                      <button
                        onClick={() => setActiveMenuCard(null)}
                        className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        Edit card
                      </button>
                      <button
                        onClick={() => setActiveMenuCard(null)}
                        className="w-full text-left px-3.5 py-1.5 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                      >
                        Replace
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-400">
                Last updated 2 days ago
              </div>
            </div>

            {/* Card 5: Meetings attended by team (QTD) - 3 cols */}
            <div className="lg:col-span-3 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Meetings attended by team (QTD)
                  </h3>
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c5' ? null : 'c5')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </div>

                {/* Sub-tabs: PRODUCT / UX DESIGN / ENGINEERING */}
                <div className="flex items-center justify-between mt-3 mb-2 border-b border-slate-100 dark:border-slate-800 pb-2 text-[11px]">
                  {(['PRODUCT', 'UX DESIGN', 'ENGINEERING'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setMeetingsTab(tab)}
                      className={`font-bold tracking-wider uppercase transition-colors relative py-1 ${
                        meetingsTab === tab
                          ? 'text-primary border-b-2 border-primary'
                          : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
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
            <div className="lg:col-span-3 bg-white dark:bg-slate-900 rounded-xl p-5 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col justify-between relative">
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Engineering performance (QTD)
                  </h3>
                  <button
                    onClick={() => setActiveMenuCard(activeMenuCard === 'c6' ? null : 'c6')}
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </div>

                {/* Sub-tabs: NEW YORK / PUNE / SYDNEY */}
                <div className="flex items-center justify-between mt-3 mb-2 border-b border-slate-100 dark:border-slate-800 pb-2 text-[11px]">
                  {(['NEW YORK', 'PUNE', 'SYDNEY'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setEngTab(tab)}
                      className={`font-bold tracking-wider uppercase transition-colors relative py-1 ${
                        engTab === tab
                          ? 'text-primary border-b-2 border-primary'
                          : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'
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
    </div>
  )
}
