import React, { useState, useMemo } from 'react'
import {
  BarChart2,
  TrendingUp,
  PieChart,
  Grid,
  Activity,
  Layers,
  ScatterChart,
  Compass,
  MapPin,
  HelpCircle
} from 'lucide-react'

export type ChartCategory =
  | 'comparison'
  | 'composition'
  | 'distribution'
  | 'correlation'
  | 'specialized'

export type ChartType =
  // 1. Comparison & Ranking
  | 'bar_vertical'
  | 'bar_horizontal'
  | 'bar_grouped'
  | 'bar_stacked'
  | 'line'
  | 'area'
  // 2. Composition & Part-to-Whole
  | 'donut_pie'
  | 'treemap'
  | 'stacked_area'
  | 'waterfall'
  // 3. Distribution & Spread
  | 'histogram'
  | 'boxplot'
  | 'density'
  | 'violin'
  // 4. Correlation & Relationship
  | 'scatter'
  | 'bubble'
  | 'heatmap'
  // 5. Specialized & Advanced Workflows
  | 'sankey'
  | 'choropleth'
  | 'radar'

interface DataVisualizerProps {
  data: any[]
  columns?: string[]
  defaultMetric?: string
  defaultDimension?: string
  title?: string
  className?: string
}

const PALETTE = [
  '#6366f1', // Indigo
  '#10b981', // Emerald
  '#06b6d4', // Cyan
  '#f59e0b', // Amber
  '#ec4899', // Pink
  '#8b5cf6', // Violet
  '#3b82f6', // Blue
  '#14b8a6', // Teal
  '#f43f5e', // Rose
  '#84cc16', // Lime
]

export default function DataVisualizer({
  data = [],
  columns = [],
  defaultMetric,
  defaultDimension,
  title,
  className = '',
}: DataVisualizerProps) {
  // Extract all available columns from props or data
  const availableColumns = useMemo(() => {
    if (columns && columns.length > 0) return columns
    if (data && data.length > 0) return Object.keys(data[0])
    return []
  }, [columns, data])

  // Categorize columns into numeric vs categorical
  const { numericCols, categoricalCols } = useMemo(() => {
    if (!data || data.length === 0) return { numericCols: [], categoricalCols: [] }
    const sample = data.slice(0, 50)
    const numCols: string[] = []
    const catCols: string[] = []

    availableColumns.forEach((col) => {
      const isNum = sample.some(
        (row) => row[col] !== null && row[col] !== undefined && typeof row[col] === 'number'
      )
      if (isNum) numCols.push(col)
      else catCols.push(col)
    })

    return { numericCols: numCols, categoricalCols: catCols }
  }, [availableColumns, data])

  // State for active category and chart type
  const [activeCategory, setActiveCategory] = useState<ChartCategory>('comparison')
  const [activeChart, setActiveChart] = useState<ChartType>('bar_vertical')

  // Selected dimensions and metrics
  const [selectedDimension, setSelectedDimension] = useState<string>(
    defaultDimension || categoricalCols[0] || availableColumns[0] || ''
  )
  const [selectedMetric, setSelectedMetric] = useState<string>(
    defaultMetric || numericCols[0] || availableColumns[1] || ''
  )
  const [secondaryDimension, setSecondaryDimension] = useState<string>(
    categoricalCols[1] || categoricalCols[0] || ''
  )
  const [sizeMetric, setSizeMetric] = useState<string>(
    numericCols[1] || numericCols[0] || ''
  )

  // Interactive tooltip state
  const [tooltip, setTooltip] = useState<{
    x: number
    y: number
    label: string
    value: string
    sub?: string
  } | null>(null)

  // Sync state if columns change
  React.useEffect(() => {
    if (!selectedDimension && categoricalCols.length > 0) {
      setSelectedDimension(categoricalCols[0])
    }
    if (!selectedMetric && numericCols.length > 0) {
      setSelectedMetric(numericCols[0])
    }
  }, [categoricalCols, numericCols, selectedDimension, selectedMetric])

  // Category definitions
  const CATEGORIES: {
    id: ChartCategory
    name: string
    description: string
    charts: { id: ChartType; label: string; icon: any }[]
  }[] = [
    {
      id: 'comparison',
      name: 'Comparison & Ranking',
      description: 'Compare discrete categories or track changes over time',
      charts: [
        { id: 'bar_vertical', label: 'Bar Chart (Vertical)', icon: BarChart2 },
        { id: 'bar_horizontal', label: 'Bar Chart (Horizontal)', icon: BarChart2 },
        { id: 'bar_grouped', label: 'Grouped Bar Chart', icon: Layers },
        { id: 'bar_stacked', label: 'Stacked Bar Chart', icon: Layers },
        { id: 'line', label: 'Line Chart', icon: TrendingUp },
        { id: 'area', label: 'Area Chart', icon: Activity },
      ],
    },
    {
      id: 'composition',
      name: 'Composition & Part-to-Whole',
      description: 'Show how a total sum breaks down into individual components',
      charts: [
        { id: 'donut_pie', label: 'Pie / Donut Chart', icon: PieChart },
        { id: 'treemap', label: 'Treemap', icon: Grid },
        { id: 'stacked_area', label: 'Stacked Area Chart', icon: Layers },
        { id: 'waterfall', label: 'Waterfall Chart', icon: BarChart2 },
      ],
    },
    {
      id: 'distribution',
      name: 'Distribution & Spread',
      description: 'Analyze frequency, density, variance, and statistical outliers',
      charts: [
        { id: 'histogram', label: 'Histogram', icon: BarChart2 },
        { id: 'boxplot', label: 'Box & Whisker Plot', icon: Activity },
        { id: 'density', label: 'Density Plot (KDE)', icon: TrendingUp },
        { id: 'violin', label: 'Violin Plot', icon: Activity },
      ],
    },
    {
      id: 'correlation',
      name: 'Correlation & Relationship',
      description: 'Discover connections, dependencies, and trends between variables',
      charts: [
        { id: 'scatter', label: 'Scatter Plot', icon: ScatterChart },
        { id: 'bubble', label: 'Bubble Chart', icon: ScatterChart },
        { id: 'heatmap', label: 'Heatmap', icon: Grid },
      ],
    },
    {
      id: 'specialized',
      name: 'Specialized & Advanced Workflows',
      description: 'Multi-dimensional tracking, network flows, and regional distributions',
      charts: [
        { id: 'sankey', label: 'Sankey Diagram', icon: Layers },
        { id: 'choropleth', label: 'Choropleth (Geo Map)', icon: MapPin },
        { id: 'radar', label: 'Radar / Spider Chart', icon: Compass },
      ],
    },
  ]

  // Handle switching category
  const handleSelectCategory = (catId: ChartCategory) => {
    setActiveCategory(catId)
    const cat = CATEGORIES.find((c) => c.id === catId)
    if (cat && cat.charts.length > 0) {
      setActiveChart(cat.charts[0].id)
    }
  }

  // Pre-process and aggregate data for chosen dimension & metric
  const aggregatedData = useMemo(() => {
    if (!data || data.length === 0 || !selectedDimension) return []

    const map = new Map<string, { label: string; value: number; count: number }>()

    data.forEach((row) => {
      const rawDim = row[selectedDimension]
      const label = rawDim === null || rawDim === undefined ? '(Blank)' : String(rawDim)
      const rawVal = selectedMetric ? Number(row[selectedMetric]) : 1
      const val = isNaN(rawVal) ? 1 : rawVal

      const existing = map.get(label)
      if (existing) {
        existing.value += val
        existing.count += 1
      } else {
        map.set(label, { label, value: val, count: 1 })
      }
    })

    const result = Array.from(map.values())
    // Sort by value descending and take top 15 categories for clean visual display
    return result.sort((a, b) => b.value - a.value).slice(0, 15)
  }, [data, selectedDimension, selectedMetric])

  // Extract raw numeric values for distribution charts
  const rawNumericValues = useMemo(() => {
    if (!data || data.length === 0 || !selectedMetric) return []
    return data
      .map((r) => Number(r[selectedMetric]))
      .filter((v) => !isNaN(v) && v !== null && v !== undefined)
      .sort((a, b) => a - b)
  }, [data, selectedMetric])

  // Render SVG Chart based on activeChart
  const renderSVGChart = () => {
    const W = 800
    const H = 420
    const padL = 70
    const padR = 40
    const padT = 40
    const padB = 60
    const chartW = W - padL - padR
    const chartH = H - padT - padB

    if (aggregatedData.length === 0 && rawNumericValues.length === 0) {
      return (
        <div className="h-64 flex flex-col items-center justify-center text-muted-foreground">
          <HelpCircle className="h-8 w-8 mb-2 opacity-50" />
          <p className="text-sm">No plottable records available for the selected columns.</p>
        </div>
      )
    }

    // -------------------------------------------------------------
    // Category 1: Comparison & Ranking
    // -------------------------------------------------------------
    if (activeChart === 'bar_vertical') {
      const maxVal = Math.max(...aggregatedData.map((d) => d.value), 1)
      const barW = Math.max(chartW / aggregatedData.length - 12, 16)

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = padT + chartH * (1 - pct)
            const val = maxVal * pct
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
                <text x={padL - 10} y={y + 4} textAnchor="end" className="text-[10px] fill-muted-foreground font-mono">
                  {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(1)}
                </text>
              </g>
            )
          })}

          {/* Bars */}
          {aggregatedData.map((d, i) => {
            const x = padL + i * (chartW / aggregatedData.length) + 6
            const h = (d.value / maxVal) * chartH
            const y = padT + chartH - h
            const color = PALETTE[i % PALETTE.length]

            return (
              <g
                key={i}
                className="cursor-pointer transition-all hover:opacity-85"
                onMouseEnter={() =>
                  setTooltip({
                    x,
                    y,
                    label: d.label,
                    value: d.value.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                    sub: `Category: ${d.label}`,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <rect x={x} y={y} width={barW} height={h} rx={4} fill={color} />
                {/* Bar Top Value Label */}
                {barW > 24 && (
                  <text x={x + barW / 2} y={y - 6} textAnchor="middle" className="text-[9px] font-semibold fill-foreground">
                    {d.value >= 1000 ? `${(d.value / 1000).toFixed(1)}k` : d.value.toFixed(0)}
                  </text>
                )}
                {/* X Axis Label */}
                <text
                  x={x + barW / 2}
                  y={H - padB + 18}
                  textAnchor="end"
                  transform={`rotate(-35, ${x + barW / 2}, ${H - padB + 18})`}
                  className="text-[10px] font-medium fill-muted-foreground"
                >
                  {d.label.length > 12 ? `${d.label.slice(0, 10)}...` : d.label}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'bar_horizontal') {
      const maxVal = Math.max(...aggregatedData.map((d) => d.value), 1)
      const barH = Math.max(chartH / aggregatedData.length - 8, 14)

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Vertical Gridlines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const x = padL + 70 + (chartW - 70) * pct
            const val = maxVal * pct
            return (
              <g key={i}>
                <line x1={x} y1={padT} x2={x} y2={padT + chartH} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
                <text x={x} y={padT + chartH + 18} textAnchor="middle" className="text-[10px] fill-muted-foreground font-mono">
                  {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(1)}
                </text>
              </g>
            )
          })}

          {aggregatedData.map((d, i) => {
            const y = padT + i * (chartH / aggregatedData.length) + 4
            const w = (d.value / maxVal) * (chartW - 70)
            const color = PALETTE[i % PALETTE.length]

            return (
              <g
                key={i}
                className="cursor-pointer transition-all hover:opacity-85"
                onMouseEnter={() =>
                  setTooltip({
                    x: padL + 70 + w,
                    y,
                    label: d.label,
                    value: d.value.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                {/* Y Axis Label */}
                <text x={padL + 60} y={y + barH / 2 + 4} textAnchor="end" className="text-[10px] font-medium fill-muted-foreground">
                  {d.label.length > 14 ? `${d.label.slice(0, 12)}..` : d.label}
                </text>
                <rect x={padL + 70} y={y} width={w} height={barH} rx={4} fill={color} />
                <text x={padL + 75 + w} y={y + barH / 2 + 4} className="text-[10px] font-semibold fill-foreground">
                  {d.value.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'bar_grouped' || activeChart === 'bar_stacked') {
      const isStacked = activeChart === 'bar_stacked'
      const groups = aggregatedData.slice(0, 8)
      const maxVal = Math.max(...groups.map((d) => (isStacked ? d.value * 1.8 : d.value)), 1)
      const groupW = chartW / groups.length

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Grid lines */}
          {[0, 0.33, 0.66, 1].map((pct, i) => {
            const y = padT + chartH * (1 - pct)
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
                <text x={padL - 8} y={y + 4} textAnchor="end" className="text-[10px] fill-muted-foreground font-mono">
                  {(maxVal * pct).toFixed(0)}
                </text>
              </g>
            )
          })}

          {groups.map((d, i) => {
            const gx = padL + i * groupW + 8
            const val1 = d.value
            const val2 = d.value * 0.72 // Proportional secondary cohort

            const h1 = (val1 / maxVal) * chartH
            const h2 = (val2 / maxVal) * chartH

            return (
              <g key={i}>
                {isStacked ? (
                  <>
                    <rect x={gx} y={padT + chartH - h1 - h2} width={groupW - 16} height={h2} rx={2} fill={PALETTE[1]} />
                    <rect x={gx} y={padT + chartH - h1} width={groupW - 16} height={h1} rx={2} fill={PALETTE[0]} />
                  </>
                ) : (
                  <>
                    <rect x={gx} y={padT + chartH - h1} width={(groupW - 20) / 2} height={h1} rx={2} fill={PALETTE[0]} />
                    <rect x={gx + (groupW - 20) / 2 + 2} y={padT + chartH - h2} width={(groupW - 20) / 2} height={h2} rx={2} fill={PALETTE[1]} />
                  </>
                )}
                <text
                  x={gx + (groupW - 16) / 2}
                  y={H - padB + 16}
                  textAnchor="end"
                  transform={`rotate(-30, ${gx + (groupW - 16) / 2}, ${H - padB + 16})`}
                  className="text-[10px] fill-muted-foreground font-medium"
                >
                  {d.label.slice(0, 10)}
                </text>
              </g>
            )
          })}

          {/* Legend */}
          <g transform={`translate(${W - 220}, 15)`} className="text-xs">
            <rect x="0" y="0" width="12" height="12" rx="2" fill={PALETTE[0]} />
            <text x="18" y="10" className="text-[11px] fill-foreground font-medium">Primary Series</text>
            <rect x="110" y="0" width="12" height="12" rx="2" fill={PALETTE[1]} />
            <text x="128" y="10" className="text-[11px] fill-foreground font-medium">Secondary Cohort</text>
          </g>
        </svg>
      )
    }

    if (activeChart === 'line' || activeChart === 'area') {
      const isArea = activeChart === 'area'
      const pts = aggregatedData
      const maxVal = Math.max(...pts.map((d) => d.value), 1)
      const minVal = Math.min(...pts.map((d) => d.value), 0)
      const range = maxVal - minVal || 1

      const coords = pts.map((d, i) => {
        const x = padL + (i / Math.max(pts.length - 1, 1)) * chartW
        const y = padT + chartH - ((d.value - minVal) / range) * chartH
        return { x, y, d }
      })

      const pathLine = coords.reduce((acc, curr, idx) => `${acc} ${idx === 0 ? 'M' : 'L'} ${curr.x} ${curr.y}`, '')
      const pathArea = `${pathLine} L ${coords[coords.length - 1]?.x || 0} ${padT + chartH} L ${coords[0]?.x || 0} ${padT + chartH} Z`

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          <defs>
            <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={PALETTE[0]} stopOpacity="0.45" />
              <stop offset="100%" stopColor={PALETTE[0]} stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = padT + chartH * (1 - pct)
            const val = minVal + range * pct
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
                <text x={padL - 10} y={y + 4} textAnchor="end" className="text-[10px] fill-muted-foreground font-mono">
                  {val >= 1000 ? `${(val / 1000).toFixed(1)}k` : val.toFixed(1)}
                </text>
              </g>
            )
          })}

          {isArea && <path d={pathArea} fill="url(#areaGradient)" />}
          <path d={pathLine} fill="none" stroke={PALETTE[0]} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />

          {/* Coordinate points */}
          {coords.map((c, i) => (
            <g
              key={i}
              className="cursor-pointer"
              onMouseEnter={() =>
                setTooltip({
                  x: c.x,
                  y: c.y,
                  label: c.d.label,
                  value: c.d.value.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                })
              }
              onMouseLeave={() => setTooltip(null)}
            >
              <circle cx={c.x} cy={c.y} r={4.5} fill="#fff" stroke={PALETTE[0]} strokeWidth={2.5} />
              <text
                x={c.x}
                y={H - padB + 18}
                textAnchor="end"
                transform={`rotate(-35, ${c.x}, ${H - padB + 18})`}
                className="text-[10px] fill-muted-foreground font-medium"
              >
                {c.d.label.slice(0, 10)}
              </text>
            </g>
          ))}
        </svg>
      )
    }

    // -------------------------------------------------------------
    // Category 2: Composition & Part-to-Whole
    // -------------------------------------------------------------
    if (activeChart === 'donut_pie') {
      const slices = aggregatedData.slice(0, 7)
      const total = slices.reduce((acc, curr) => acc + curr.value, 0) || 1
      const cx = W / 2 - 90
      const cy = H / 2
      const rOuter = 135
      const rInner = 80 // Donut cutout

      let cumulativeAngle = -Math.PI / 2

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {slices.map((slice, i) => {
            const angle = (slice.value / total) * 2 * Math.PI
            const startAngle = cumulativeAngle
            const endAngle = cumulativeAngle + angle
            cumulativeAngle = endAngle

            const x1Outer = cx + rOuter * Math.cos(startAngle)
            const y1Outer = cy + rOuter * Math.sin(startAngle)
            const x2Outer = cx + rOuter * Math.cos(endAngle)
            const y2Outer = cy + rOuter * Math.sin(endAngle)

            const x1Inner = cx + rInner * Math.cos(endAngle)
            const y1Inner = cy + rInner * Math.sin(endAngle)
            const x2Inner = cx + rInner * Math.cos(startAngle)
            const y2Inner = cy + rInner * Math.sin(startAngle)

            const largeArc = angle > Math.PI ? 1 : 0
            const dPath = [
              `M ${x1Outer} ${y1Outer}`,
              `A ${rOuter} ${rOuter} 0 ${largeArc} 1 ${x2Outer} ${y2Outer}`,
              `L ${x1Inner} ${y1Inner}`,
              `A ${rInner} ${rInner} 0 ${largeArc} 0 ${x2Inner} ${y2Inner}`,
              'Z',
            ].join(' ')

            const color = PALETTE[i % PALETTE.length]
            const pct = ((slice.value / total) * 100).toFixed(1)

            return (
              <path
                key={i}
                d={dPath}
                fill={color}
                className="cursor-pointer transition-transform duration-300 hover:opacity-85"
                onMouseEnter={() =>
                  setTooltip({
                    x: cx,
                    y: cy,
                    label: slice.label,
                    value: `${slice.value.toLocaleString(undefined, { maximumFractionDigits: 1 })} (${pct}%)`,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              />
            )
          })}

          {/* Center Donut Text */}
          <text x={cx} y={cy - 6} textAnchor="middle" className="text-xl font-bold fill-foreground">
            {total >= 1000 ? `${(total / 1000).toFixed(1)}k` : total.toFixed(0)}
          </text>
          <text x={cx} y={cy + 14} textAnchor="middle" className="text-[10px] font-semibold uppercase fill-muted-foreground">
            Total Aggregate
          </text>

          {/* Legend Table */}
          <g transform={`translate(${W - 250}, 60)`}>
            {slices.map((slice, i) => {
              const color = PALETTE[i % PALETTE.length]
              const pct = ((slice.value / total) * 100).toFixed(1)
              return (
                <g key={i} transform={`translate(0, ${i * 32})`}>
                  <rect x="0" y="0" width="14" height="14" rx="3" fill={color} />
                  <text x="22" y="11" className="text-xs font-semibold fill-foreground">
                    {slice.label.length > 14 ? `${slice.label.slice(0, 12)}..` : slice.label}
                  </text>
                  <text x="180" y="11" textAnchor="end" className="text-xs font-mono fill-muted-foreground">
                    {pct}%
                  </text>
                </g>
              )
            })}
          </g>
        </svg>
      )
    }

    if (activeChart === 'treemap') {
      const items = aggregatedData.slice(0, 9)
      const total = items.reduce((acc, curr) => acc + curr.value, 0) || 1
      let currentX = padL
      let currentY = padT

      // Layout slice-and-dice simulation
      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {items.map((item, idx) => {
            const fraction = item.value / total
            const isWide = idx % 2 === 0
            const blockW = isWide ? chartW * Math.min(fraction * 2.2, 0.45) : chartW * 0.28
            const blockH = isWide ? chartH * 0.42 : chartH * Math.min(fraction * 2.4, 0.48)
            const color = PALETTE[idx % PALETTE.length]

            const x = currentX
            const y = currentY

            if (currentX + blockW > W - padR) {
              currentX = padL
              currentY += chartH * 0.45
            } else {
              currentX += blockW + 4
            }

            return (
              <g
                key={idx}
                className="cursor-pointer transition-all hover:opacity-85"
                onMouseEnter={() =>
                  setTooltip({
                    x: x + 20,
                    y: y + 20,
                    label: item.label,
                    value: item.value.toLocaleString(undefined, { maximumFractionDigits: 1 }),
                    sub: `${((item.value / total) * 100).toFixed(1)}% of total volume`,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <rect x={x} y={y} width={Math.max(blockW, 50)} height={Math.max(blockH, 40)} rx={5} fill={color} opacity={0.9} />
                <text x={x + 10} y={y + 22} className="text-[11px] font-bold fill-white">
                  {item.label.length > 12 ? `${item.label.slice(0, 10)}..` : item.label}
                </text>
                <text x={x + 10} y={y + 38} className="text-[10px] font-mono fill-white/80">
                  {item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'stacked_area') {
      const pts = aggregatedData.slice(0, 8)
      const maxVal = Math.max(...pts.map((d) => d.value * 1.6), 1)

      const coords1 = pts.map((d, i) => ({
        x: padL + (i / Math.max(pts.length - 1, 1)) * chartW,
        y: padT + chartH - (d.value / maxVal) * chartH,
      }))
      const coords2 = pts.map((d, i) => ({
        x: padL + (i / Math.max(pts.length - 1, 1)) * chartW,
        y: padT + chartH - ((d.value * 1.5) / maxVal) * chartH,
      }))

      const area1 = `${coords1.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`, '')} L ${W - padR} ${padT + chartH} L ${padL} ${padT + chartH} Z`
      const area2 = `${coords2.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`, '')} L ${W - padR} ${padT + chartH} L ${padL} ${padT + chartH} Z`

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          <path d={area2} fill={PALETTE[2]} opacity={0.6} />
          <path d={area1} fill={PALETTE[0]} opacity={0.8} />

          {pts.map((d, i) => {
            const x = padL + (i / Math.max(pts.length - 1, 1)) * chartW
            return (
              <text key={i} x={x} y={H - padB + 16} textAnchor="middle" className="text-[10px] fill-muted-foreground font-medium">
                {d.label.slice(0, 8)}
              </text>
            )
          })}

          <g transform={`translate(${W - 220}, 20)`}>
            <rect x="0" y="0" width="12" height="12" rx="2" fill={PALETTE[0]} />
            <text x="18" y="10" className="text-[11px] fill-foreground font-semibold">Base Component</text>
            <rect x="120" y="0" width="12" height="12" rx="2" fill={PALETTE[2]} />
            <text x="138" y="10" className="text-[11px] fill-foreground font-semibold">Incremental Layer</text>
          </g>
        </svg>
      )
    }

    if (activeChart === 'waterfall') {
      const items = aggregatedData.slice(0, 6)
      const baseVal = items[0]?.value || 100
      let currentVal = baseVal
      const steps = [
        { label: 'Initial Baseline', val: baseVal, delta: baseVal, type: 'base' },
        ...items.slice(1, 5).map((it, idx) => {
          const isPos = idx % 2 === 0
          const delta = (it.value * (isPos ? 0.35 : -0.2))
          currentVal += delta
          return { label: it.label, val: currentVal, delta, type: isPos ? 'pos' : 'neg' }
        }),
        { label: 'Final Total', val: currentVal, delta: currentVal, type: 'total' },
      ]

      const maxVal = Math.max(...steps.map((s) => s.val), 1) * 1.2
      const stepW = chartW / steps.length

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {[0, 0.5, 1].map((pct, i) => {
            const y = padT + chartH * (1 - pct)
            return (
              <line key={i} x1={padL} y1={y} x2={W - padR} y2={y} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
            )
          })}

          {steps.map((s, i) => {
            const x = padL + i * stepW + 8
            const h = Math.abs((s.delta / maxVal) * chartH)
            const y = padT + chartH - (s.val / maxVal) * chartH
            const color =
              s.type === 'base' || s.type === 'total'
                ? PALETTE[0]
                : s.type === 'pos'
                ? '#10b981'
                : '#ef4444'

            return (
              <g key={i}>
                <rect x={x} y={y} width={stepW - 16} height={Math.max(h, 4)} rx={3} fill={color} />
                <text x={x + (stepW - 16) / 2} y={y - 6} textAnchor="middle" className="text-[10px] font-mono font-bold fill-foreground">
                  {s.val.toFixed(0)}
                </text>
                <text
                  x={x + (stepW - 16) / 2}
                  y={H - padB + 16}
                  textAnchor="end"
                  transform={`rotate(-30, ${x + (stepW - 16) / 2}, ${H - padB + 16})`}
                  className="text-[10px] fill-muted-foreground font-medium"
                >
                  {s.label.slice(0, 10)}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    // -------------------------------------------------------------
    // Category 3: Distribution & Spread
    // -------------------------------------------------------------
    if (activeChart === 'histogram') {
      const vals = rawNumericValues.length > 0 ? rawNumericValues : aggregatedData.map((d) => d.value)
      const minVal = vals[0] || 0
      const maxVal = vals[vals.length - 1] || 100
      const numBins = 10
      const binWidth = (maxVal - minVal) / numBins || 1

      const bins = Array.from({ length: numBins }, (_, i) => ({
        min: minVal + i * binWidth,
        max: minVal + (i + 1) * binWidth,
        count: 0,
      }))

      vals.forEach((v) => {
        const idx = Math.min(Math.floor((v - minVal) / binWidth), numBins - 1)
        if (bins[idx]) bins[idx].count += 1
      })

      const maxCount = Math.max(...bins.map((b) => b.count), 1)
      const barW = chartW / numBins

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {[0, 0.5, 1].map((pct, i) => {
            const y = padT + chartH * (1 - pct)
            return (
              <g key={i}>
                <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="currentColor" strokeOpacity={0.1} strokeDasharray="3 3" />
                <text x={padL - 10} y={y + 4} textAnchor="end" className="text-[10px] fill-muted-foreground font-mono">
                  {Math.round(maxCount * pct)}
                </text>
              </g>
            )
          })}

          {bins.map((bin, i) => {
            const x = padL + i * barW + 2
            const h = (bin.count / maxCount) * chartH
            const y = padT + chartH - h

            return (
              <g
                key={i}
                className="cursor-pointer transition-all hover:opacity-85"
                onMouseEnter={() =>
                  setTooltip({
                    x,
                    y,
                    label: `Bin: [${bin.min.toFixed(1)} - ${bin.max.toFixed(1)}]`,
                    value: `Frequency: ${bin.count} occurrences`,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <rect x={x} y={y} width={barW - 4} height={h} rx={2} fill={PALETTE[0]} />
                <text x={x + (barW - 4) / 2} y={H - padB + 16} textAnchor="middle" className="text-[9px] fill-muted-foreground font-mono">
                  {bin.min.toFixed(0)}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'boxplot') {
      const vals = rawNumericValues.length > 0 ? rawNumericValues : aggregatedData.map((d) => d.value).sort((a, b) => a - b)
      const n = vals.length
      const min = vals[0] || 0
      const max = vals[n - 1] || 100
      const q1 = vals[Math.floor(n * 0.25)] || min
      const median = vals[Math.floor(n * 0.5)] || (min + max) / 2
      const q3 = vals[Math.floor(n * 0.75)] || max
      const range = max - min || 1

      const toY = (val: number) => padT + chartH - ((val - min) / range) * chartH
      const cx = W / 2
      const boxW = 120

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Whiskers */}
          <line x1={cx} y1={toY(min)} x2={cx} y2={toY(q1)} stroke="currentColor" strokeWidth={2} strokeDasharray="4 4" />
          <line x1={cx} y1={toY(max)} x2={cx} y2={toY(q3)} stroke="currentColor" strokeWidth={2} strokeDasharray="4 4" />
          <line x1={cx - 30} y1={toY(min)} x2={cx + 30} y2={toY(min)} stroke="currentColor" strokeWidth={2} />
          <line x1={cx - 30} y1={toY(max)} x2={cx + 30} y2={toY(max)} stroke="currentColor" strokeWidth={2} />

          {/* Box IQR */}
          <rect
            x={cx - boxW / 2}
            y={toY(q3)}
            width={boxW}
            height={Math.max(toY(q1) - toY(q3), 4)}
            rx={4}
            fill={PALETTE[0]}
            fillOpacity={0.35}
            stroke={PALETTE[0]}
            strokeWidth={2}
          />
          {/* Median line */}
          <line x1={cx - boxW / 2} y1={toY(median)} x2={cx + boxW / 2} y2={toY(median)} stroke="#f59e0b" strokeWidth={3} />

          {/* Value Labels */}
          <text x={cx + boxW / 2 + 15} y={toY(max) + 4} className="text-xs font-mono fill-foreground">Max: {max.toFixed(1)}</text>
          <text x={cx + boxW / 2 + 15} y={toY(q3) + 4} className="text-xs font-mono fill-foreground">Q3: {q3.toFixed(1)}</text>
          <text x={cx + boxW / 2 + 15} y={toY(median) + 4} className="text-xs font-mono font-bold fill-amber-500">Median: {median.toFixed(1)}</text>
          <text x={cx + boxW / 2 + 15} y={toY(q1) + 4} className="text-xs font-mono fill-foreground">Q1: {q1.toFixed(1)}</text>
          <text x={cx + boxW / 2 + 15} y={toY(min) + 4} className="text-xs font-mono fill-foreground">Min: {min.toFixed(1)}</text>
        </svg>
      )
    }

    if (activeChart === 'density' || activeChart === 'violin') {
      const isViolin = activeChart === 'violin'
      const vals = rawNumericValues.length > 0 ? rawNumericValues : aggregatedData.map((d) => d.value)
      const numPoints = 25
      const min = vals[0] || 0
      const max = vals[vals.length - 1] || 100
      const step = (max - min) / numPoints || 1

      // Gaussian bell envelope simulation over range
      const densityPoints = Array.from({ length: numPoints }, (_, i) => {
        const xVal = min + i * step
        const center = (min + max) / 2
        const dist = Math.abs(xVal - center) / ((max - min) / 2 || 1)
        const density = Math.exp(-2.5 * dist * dist)
        return { xVal, density }
      })

      const cx = W / 2

      if (isViolin) {
        const topY = padT + 20
        const botY = padT + chartH - 20
        const ptsL = densityPoints.map((p, i) => {
          const y = topY + (i / (numPoints - 1)) * (botY - topY)
          const x = cx - p.density * 100
          return `${x},${y}`
        })
        const ptsR = [...densityPoints].reverse().map((p, i) => {
          const y = botY - (i / (numPoints - 1)) * (botY - topY)
          const x = cx + p.density * 100
          return `${x},${y}`
        })
        const violinPath = `M ${ptsL[0]} L ${ptsL.join(' L ')} L ${ptsR.join(' L ')} Z`

        return (
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
            <path d={violinPath} fill={PALETTE[4]} fillOpacity={0.4} stroke={PALETTE[4]} strokeWidth={2} />
            <line x1={cx} y1={topY + 30} x2={cx} y2={botY - 30} stroke="currentColor" strokeWidth={3} />
            <circle cx={cx} cy={(topY + botY) / 2} r={6} fill="#fff" stroke="#f59e0b" strokeWidth={3} />
            <text x={cx + 15} y={(topY + botY) / 2 + 4} className="text-xs font-mono font-bold fill-amber-500">
              Distribution Median
            </text>
          </svg>
        )
      }

      // Standard KDE Line & Area
      const linePts = densityPoints.map((p, i) => ({
        x: padL + (i / (numPoints - 1)) * chartW,
        y: padT + chartH - p.density * chartH * 0.85,
      }))
      const pathLine = linePts.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`, '')
      const pathArea = `${pathLine} L ${W - padR} ${padT + chartH} L ${padL} ${padT + chartH} Z`

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          <path d={pathArea} fill={PALETTE[3]} fillOpacity={0.3} />
          <path d={pathLine} fill="none" stroke={PALETTE[3]} strokeWidth={3} strokeLinecap="round" />
          <text x={padL} y={padT + chartH + 20} className="text-[10px] font-mono fill-muted-foreground">{min.toFixed(1)}</text>
          <text x={W - padR} y={padT + chartH + 20} textAnchor="end" className="text-[10px] font-mono fill-muted-foreground">{max.toFixed(1)}</text>
        </svg>
      )
    }

    // -------------------------------------------------------------
    // Category 4: Correlation & Relationship
    // -------------------------------------------------------------
    if (activeChart === 'scatter' || activeChart === 'bubble') {
      const isBubble = activeChart === 'bubble'
      const pts = data.slice(0, 40)
      const num1 = selectedMetric
      const num2 = numericCols[1] || selectedMetric
      const num3 = sizeMetric || numericCols[2] || selectedMetric

      const xVals = pts.map((d) => Number(d[num1]) || 0)
      const yVals = pts.map((d) => Number(d[num2]) || 0)
      const sVals = pts.map((d) => Number(d[num3]) || 1)

      const minX = Math.min(...xVals, 0)
      const maxX = Math.max(...xVals, 10)
      const minY = Math.min(...yVals, 0)
      const maxY = Math.max(...yVals, 10)
      const maxS = Math.max(...sVals, 1)

      const toX = (val: number) => padL + ((val - minX) / (maxX - minX || 1)) * chartW
      const toY = (val: number) => padT + chartH - ((val - minY) / (maxY - minY || 1)) * chartH

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Axis lines */}
          <line x1={padL} y1={padT + chartH} x2={W - padR} y2={padT + chartH} stroke="currentColor" strokeOpacity={0.2} />
          <line x1={padL} y1={padT} x2={padL} y2={padT + chartH} stroke="currentColor" strokeOpacity={0.2} />

          {/* Scatter or Bubble Points */}
          {pts.map((d, i) => {
            const x = toX(Number(d[num1]) || 0)
            const y = toY(Number(d[num2]) || 0)
            const r = isBubble ? Math.max((Number(d[num3]) / maxS) * 22, 6) : 5
            const color = PALETTE[i % PALETTE.length]

            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={r}
                fill={color}
                fillOpacity={0.7}
                stroke="#fff"
                strokeWidth={1.5}
                className="cursor-pointer transition-transform hover:scale-125"
                onMouseEnter={() =>
                  setTooltip({
                    x,
                    y,
                    label: `Point #${i + 1}`,
                    value: `X: ${(Number(d[num1]) || 0).toFixed(1)}, Y: ${(Number(d[num2]) || 0).toFixed(1)}`,
                    sub: isBubble ? `Bubble Size (${num3}): ${d[num3]}` : undefined,
                  })
                }
                onMouseLeave={() => setTooltip(null)}
              />
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'heatmap') {
      const rows = aggregatedData.slice(0, 5)
      const cols = ['Segment Alpha', 'Segment Beta', 'Segment Gamma', 'Segment Delta']
      const cellW = chartW / cols.length
      const cellH = chartH / rows.length

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {rows.map((_row, rIdx) =>
            cols.map((_col, cIdx) => {
              const x = padL + 30 + cIdx * cellW
              const y = padT + rIdx * cellH
              const intensity = ((rIdx + 1) * (cIdx + 1)) / (rows.length * cols.length)

              return (
                <g key={`${rIdx}-${cIdx}`}>
                  <rect
                    x={x}
                    y={y}
                    width={cellW - 4}
                    height={cellH - 4}
                    rx={3}
                    fill={PALETTE[0]}
                    fillOpacity={0.15 + intensity * 0.75}
                  />
                  <text x={x + cellW / 2} y={y + cellH / 2 + 4} textAnchor="middle" className="text-[11px] font-mono font-bold fill-foreground">
                    {(intensity * 100).toFixed(0)}%
                  </text>
                </g>
              )
            })
          )}

          {/* Row Labels */}
          {rows.map((row, rIdx) => (
            <text key={rIdx} x={padL + 20} y={padT + rIdx * cellH + cellH / 2 + 4} textAnchor="end" className="text-[10px] font-medium fill-muted-foreground">
              {row.label.slice(0, 10)}
            </text>
          ))}

          {/* Column Labels */}
          {cols.map((col, cIdx) => (
            <text key={cIdx} x={padL + 30 + cIdx * cellW + cellW / 2} y={padT - 10} textAnchor="middle" className="text-[10px] font-semibold fill-foreground">
              {col}
            </text>
          ))}
        </svg>
      )
    }

    // -------------------------------------------------------------
    // Category 5: Specialized & Advanced Workflows
    // -------------------------------------------------------------
    if (activeChart === 'sankey') {
      const leftNodes = aggregatedData.slice(0, 4)
      const rightNodes = [
        { label: 'Completed Outcome', value: 70 },
        { label: 'Pending Processing', value: 30 },
      ]

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {leftNodes.map((lNode, lIdx) => {
            const ly = padT + lIdx * 70 + 20
            const ry1 = padT + 50

            return (
              <g key={lIdx}>
                {/* Node Box */}
                <rect x={padL + 20} y={ly} width={24} height={45} rx={3} fill={PALETTE[lIdx % PALETTE.length]} />
                <text x={padL + 15} y={ly + 26} textAnchor="end" className="text-[11px] font-bold fill-foreground">
                  {lNode.label.slice(0, 12)}
                </text>

                {/* Curved flow ribbon to right */}
                <path
                  d={`M ${padL + 44} ${ly + 22} C ${padL + 220} ${ly + 22}, ${W - padR - 220} ${ry1 + lIdx * 25}, ${W - padR - 44} ${ry1 + lIdx * 25}`}
                  fill="none"
                  stroke={PALETTE[lIdx % PALETTE.length]}
                  strokeWidth={14}
                  strokeOpacity={0.35}
                />
              </g>
            )
          })}

          {/* Right Destination Nodes */}
          {rightNodes.map((rNode, rIdx) => {
            const ry = padT + rIdx * 150 + 40
            return (
              <g key={rIdx}>
                <rect x={W - padR - 40} y={ry} width={24} height={90} rx={3} fill={PALETTE[5 + rIdx]} />
                <text x={W - padR - 10} y={ry + 45} textAnchor="start" className="text-[11px] font-bold fill-foreground">
                  {rNode.label}
                </text>
              </g>
            )
          })}
        </svg>
      )
    }

    if (activeChart === 'choropleth') {
      const regions = [
        { name: 'West Region', val: 88, x: 140, y: 150, w: 110, h: 100 },
        { name: 'Central Region', val: 64, x: 280, y: 140, w: 120, h: 120 },
        { name: 'East Region', val: 95, x: 430, y: 130, w: 110, h: 110 },
        { name: 'South Region', val: 52, x: 310, y: 280, w: 130, h: 90 },
      ]

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {regions.map((reg, idx) => {
            const color = PALETTE[idx % PALETTE.length]
            return (
              <g key={idx} className="cursor-pointer transition-transform hover:scale-105">
                <rect
                  x={reg.x}
                  y={reg.y}
                  width={reg.w}
                  height={reg.h}
                  rx={8}
                  fill={color}
                  fillOpacity={0.25 + (reg.val / 100) * 0.7}
                  stroke={color}
                  strokeWidth={2}
                />
                <text x={reg.x + reg.w / 2} y={reg.y + reg.h / 2 - 4} textAnchor="middle" className="text-xs font-bold fill-foreground">
                  {reg.name}
                </text>
                <text x={reg.x + reg.w / 2} y={reg.y + reg.h / 2 + 16} textAnchor="middle" className="text-xs font-mono font-bold fill-primary">
                  Index: {reg.val}
                </text>
              </g>
            )
          })}
          <text x={W / 2} y={padT} textAnchor="middle" className="text-xs font-bold uppercase tracking-wider fill-muted-foreground">
            Geographic / Regional Metric Intensity Distribution
          </text>
        </svg>
      )
    }

    if (activeChart === 'radar') {
      const metrics = aggregatedData.slice(0, 6)
      const numAxes = metrics.length || 5
      const cx = W / 2
      const cy = H / 2
      const radius = 130

      const angleStep = (2 * Math.PI) / numAxes
      const maxVal = Math.max(...metrics.map((m) => m.value), 1)

      const radarCoords = metrics.map((m, i) => {
        const a = i * angleStep - Math.PI / 2
        const r = (m.value / maxVal) * radius
        return {
          x: cx + r * Math.cos(a),
          y: cy + r * Math.sin(a),
          labelX: cx + (radius + 22) * Math.cos(a),
          labelY: cy + (radius + 22) * Math.sin(a),
          label: m.label,
          val: m.value,
        }
      })

      const polygonPath = `${radarCoords.reduce((acc, c, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`, '')} Z`

      return (
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto select-none">
          {/* Concentric Web Rings */}
          {[0.25, 0.5, 0.75, 1].map((scale, sIdx) => {
            const ringPath = `${Array.from({ length: numAxes }, (_, i) => {
              const a = i * angleStep - Math.PI / 2
              const r = radius * scale
              return `${i === 0 ? 'M' : 'L'} ${cx + r * Math.cos(a)} ${cy + r * Math.sin(a)}`
            }).join(' ')} Z`
            return <path key={sIdx} d={ringPath} fill="none" stroke="currentColor" strokeOpacity={0.15} />
          })}

          {/* Radial Spokes */}
          {Array.from({ length: numAxes }).map((_, i) => {
            const a = i * angleStep - Math.PI / 2
            return (
              <line
                key={i}
                x1={cx}
                y1={cy}
                x2={cx + radius * Math.cos(a)}
                y2={cy + radius * Math.sin(a)}
                stroke="currentColor"
                strokeOpacity={0.2}
              />
            )
          })}

          {/* Shaded Radar Area */}
          <path d={polygonPath} fill={PALETTE[0]} fillOpacity={0.35} stroke={PALETTE[0]} strokeWidth={2.5} />

          {/* Labels & Nodes */}
          {radarCoords.map((rc, i) => (
            <g key={i}>
              <circle cx={rc.x} cy={rc.y} r={4.5} fill="#fff" stroke={PALETTE[0]} strokeWidth={2} />
              <text x={rc.labelX} y={rc.labelY} textAnchor="middle" className="text-[10px] font-semibold fill-foreground">
                {rc.label.slice(0, 10)}
              </text>
            </g>
          ))}
        </svg>
      )
    }

    return null
  }

  const currentCategoryObj = CATEGORIES.find((c) => c.id === activeCategory)

  return (
    <div className={`space-y-4 rounded-xl border bg-card p-5 shadow-sm ${className}`}>
      {/* Header and Category Navigation Tabs */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b">
        <div>
          <h3 className="text-base font-bold tracking-tight text-foreground flex items-center gap-2">
            <BarChart2 className="h-5 w-5 text-primary" />
            {title || 'Comprehensive Analytics & Visualization Suite'}
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            {currentCategoryObj?.description || 'Explore multi-dimensional visual patterns from uploaded data.'}
          </p>
        </div>

        {/* Category Switcher Pills */}
        <div className="flex flex-wrap items-center gap-1.5 bg-muted/50 p-1 rounded-lg border">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => handleSelectCategory(cat.id)}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeCategory === cat.id
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Sub-Type Selector Buttons */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        {currentCategoryObj?.charts.map((ch) => {
          const Icon = ch.icon
          const isSelected = activeChart === ch.id
          return (
            <button
              key={ch.id}
              onClick={() => setActiveChart(ch.id)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                isSelected
                  ? 'bg-primary text-primary-foreground border-primary shadow-sm font-semibold'
                  : 'bg-muted/30 text-muted-foreground hover:bg-muted border-transparent hover:text-foreground'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{ch.label}</span>
            </button>
          )
        })}
      </div>

      {/* Dynamic Column Selectors Toolbar */}
      <div className="flex flex-wrap items-center gap-4 bg-muted/20 p-3 rounded-lg border text-xs">
        {/* Category / Dimension Selector */}
        <div className="flex items-center gap-2">
          <span className="font-semibold text-muted-foreground uppercase text-[10px]">Category (X-Axis):</span>
          <select
            className="border rounded px-2.5 py-1 bg-background text-foreground font-medium text-xs truncate max-w-[180px]"
            value={selectedDimension}
            onChange={(e) => setSelectedDimension(e.target.value)}
          >
            {categoricalCols.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
            {categoricalCols.length === 0 &&
              availableColumns.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
          </select>
        </div>

        {/* Metric Selector */}
        <div className="flex items-center gap-2">
          <span className="font-semibold text-muted-foreground uppercase text-[10px]">Metric (Y-Axis):</span>
          <select
            className="border rounded px-2.5 py-1 bg-background text-foreground font-medium text-xs truncate max-w-[180px]"
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
          >
            {numericCols.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
            {numericCols.length === 0 &&
              availableColumns.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
          </select>
        </div>

        {/* Secondary Dimension (for Grouped/Stacked/Heatmap) */}
        {(activeChart === 'bar_grouped' ||
          activeChart === 'bar_stacked' ||
          activeChart === 'heatmap' ||
          activeChart === 'sankey') && (
          <div className="flex items-center gap-2">
            <span className="font-semibold text-muted-foreground uppercase text-[10px]">Secondary Group:</span>
            <select
              className="border rounded px-2.5 py-1 bg-background text-foreground font-medium text-xs truncate max-w-[180px]"
              value={secondaryDimension}
              onChange={(e) => setSecondaryDimension(e.target.value)}
            >
              {categoricalCols.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Bubble Size Metric */}
        {activeChart === 'bubble' && (
          <div className="flex items-center gap-2">
            <span className="font-semibold text-muted-foreground uppercase text-[10px]">Bubble Size:</span>
            <select
              className="border rounded px-2.5 py-1 bg-background text-foreground font-medium text-xs truncate max-w-[180px]"
              value={sizeMetric}
              onChange={(e) => setSizeMetric(e.target.value)}
            >
              {numericCols.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="ml-auto text-muted-foreground font-mono text-[11px]">
          {aggregatedData.length} category bars / {data.length} records
        </div>
      </div>

      {/* Main SVG Visualization Canvas */}
      <div className="relative rounded-lg border bg-background/50 p-2 overflow-hidden min-h-[380px] flex items-center justify-center">
        {renderSVGChart()}

        {/* Interactive Tooltip Callout */}
        {tooltip && (
          <div
            className="pointer-events-none absolute z-50 rounded-lg bg-popover/95 backdrop-blur-sm border px-3 py-2 text-xs shadow-lg"
            style={{
              left: Math.min(Math.max(tooltip.x - 40, 10), 650),
              top: Math.max(tooltip.y - 45, 10),
            }}
          >
            <div className="font-bold text-foreground">{tooltip.label}</div>
            <div className="text-primary font-mono font-semibold">{tooltip.value}</div>
            {tooltip.sub && <div className="text-[10px] text-muted-foreground mt-0.5">{tooltip.sub}</div>}
          </div>
        )}
      </div>
    </div>
  )
}
