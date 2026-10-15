"""Pydantic schemas and typed models for the Power BI-Style Executive Analytics Engine."""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardReadinessStatus(str, Enum):
    VALIDATING = "VALIDATING"
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    BLOCKED = "BLOCKED"
    STALE = "STALE"
    ERROR = "ERROR"


class FilterContext(BaseModel):
    """Dynamic cascading filter context."""
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None  # Q1, Q2, Q3, Q4
    month: Optional[int] = None    # 1 to 12
    team: Optional[str] = None     # Primary category filter value
    location: Optional[str] = None # Secondary attribute filter value
    primary_col: Optional[str] = None   # Explicit column name for primary dimension
    secondary_col: Optional[str] = None # Explicit column name for secondary dimension
    search_query: Optional[str] = None


class SparklinePoint(BaseModel):
    label: str
    value: float
    formatted: str


class TopBottomTeamItem(BaseModel):
    name: str
    raw_value: float
    percentage: float
    target_value: Optional[float] = None
    rank: int
    is_top: bool
    icon_type: str = "default"  # code, design, qa, product, data, analytics


class QuarterlySeriesPoint(BaseModel):
    period_label: str  # e.g. "Q1 2023", "Q2 2023"
    year: int
    quarter: str
    bar_value: float
    line_value: Optional[float] = None
    is_current_qtd: bool = False


class Card1QuarterToQuarter(BaseModel):
    title: str = "Quarter-to-Quarter Performance"
    metric_label: str = "(QTD)"
    change_pct: Optional[float] = None
    change_formatted: str = "N/A"
    is_positive: bool = True
    current_value: float = 0.0
    previous_value: Optional[float] = None
    sparkline_title: str = "Monthly Trend"
    sparkline_subtitle: str = "(Recent months)"
    sparkline_points: List[SparklinePoint] = Field(default_factory=list)
    last_updated_text: str = "Live calculated"
    status_note: Optional[str] = None


class Card2YearOverYear(BaseModel):
    title: str = "Year-over-Year Trajectory"
    metric_label: str = "(QTD)"
    selected_team: str = "Primary Dimension"
    change_pct: Optional[float] = None
    change_formatted: str = "N/A"
    is_positive: bool = True
    current_value: float = 0.0
    prior_year_value: Optional[float] = None
    sparkline_title: str = "Yearly Trend"
    sparkline_subtitle: str = "(Multi-year)"
    sparkline_points: List[SparklinePoint] = Field(default_factory=list)
    last_updated_text: str = "Live calculated"
    status_note: Optional[str] = None


class Card3TopBottomTeams(BaseModel):
    title: str = "Top and bottom 3 categories - Proportion (YTD)"
    primary_dimension: str
    top_teams: List[TopBottomTeamItem] = Field(default_factory=list)
    bottom_teams: List[TopBottomTeamItem] = Field(default_factory=list)
    calculation_basis: str = "Proportion of target / volume"
    eligible_record_count: int = 0
    last_updated_text: str = "Live calculated"


class Card4QuarterlyPerformance(BaseModel):
    title: str = "Quarterly Distribution & Trends"
    available_tabs: List[str] = Field(default_factory=list)
    active_tab: str = ""
    series: List[QuarterlySeriesPoint] = Field(default_factory=list)
    metric_name: str = "Metric"
    legend_label: str = "Monthly"
    last_updated_text: str = "Live calculated"


class Card5MeetingsAttended(BaseModel):
    title: str = "Category Concentration (QTD)"
    available_tabs: List[str] = Field(default_factory=list)
    active_tab: str = ""
    percentage: float = 0.0
    numerator: float = 0.0
    denominator: float = 0.0
    center_label: str = "Share"
    metric_description: str = "Distribution within dataset"
    last_updated_text: str = "Live calculated"


class Card6EngineeringPerformance(BaseModel):
    title: str = "Secondary Attribute Benchmark (QTD)"
    available_tabs: List[str] = Field(default_factory=list)
    active_tab: str = ""
    percentage: float = 0.0
    numerator: float = 0.0
    denominator: float = 0.0
    center_label: str = "Share"
    benchmark_comparison: str = "Normalized to dataset benchmark"
    last_updated_text: str = "Live calculated"


class DataQualitySummary(BaseModel):
    total_records: int
    filtered_records: int
    rejected_records: int = 0
    null_value_rate: float = 0.0
    date_field_identified: Optional[str] = None
    date_range_min: Optional[str] = None
    date_range_max: Optional[str] = None
    data_freshness_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    warnings: List[str] = Field(default_factory=list)


class DashboardAnalyticsPayload(BaseModel):
    """Complete, verified response payload for Executive Performance Management Dashboard."""
    dataset_id: str
    dataset_name: str
    project_id: str
    readiness_status: DashboardReadinessStatus
    status_explanation: str
    filter_context: FilterContext
    quality_summary: DataQualitySummary
    card1_quarter_to_quarter: Card1QuarterToQuarter
    card2_year_over_year: Card2YearOverYear
    card3_top_bottom_teams: Card3TopBottomTeams
    card4_quarterly_performance: Card4QuarterlyPerformance
    card5_meetings_attended: Card5MeetingsAttended
    card6_engineering_performance: Card6EngineeringPerformance
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    computation_time_ms: float = 0.0


class FilterDimensions(BaseModel):
    """Available distinct values for cascading filters."""
    years: List[int] = Field(default_factory=list)
    quarters: List[str] = Field(default_factory=list)
    months: List[Dict[str, Any]] = Field(default_factory=list)
    teams: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    date_min: Optional[str] = None
    date_max: Optional[str] = None
    primary_dim_col: Optional[str] = None
    primary_dim_label: Optional[str] = None
    secondary_dim_col: Optional[str] = None
    secondary_dim_label: Optional[str] = None
    total_records: int = 0
    filtered_records: int = 0


class DrilldownRequest(BaseModel):
    dataset_id: str
    card_id: str
    category_tab: Optional[str] = None
    location_tab: Optional[str] = None
    period_label: Optional[str] = None
    filter_context: Optional[FilterContext] = None
    page: int = 1
    page_size: int = 50


class DrilldownResponse(BaseModel):
    card_id: str
    filter_description: str
    total_matching_records: int
    page: int
    page_size: int
    columns: List[str]
    rows: List[Dict[str, Any]]


class ReconciliationItem(BaseModel):
    metric_name: str
    dashboard_value: Any
    independent_sql_value: Any
    tolerance: float = 0.0
    is_exact_match: bool
    sql_query: str


class ReconciliationResponse(BaseModel):
    dataset_id: str
    reconciliation_passed: bool
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    items: List[ReconciliationItem]
    summary: str
