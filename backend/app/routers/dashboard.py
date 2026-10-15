"""Executive Performance Management Dashboard API routes.

Provides endpoints for Power BI-style verified analytics, dynamic cascading
filter dimensions, underlying record drilldown, independent SQL reconciliation,
and verified report export.
Zero mock data, zero simulated metrics, zero synthetic numbers.
"""
import csv
from io import StringIO
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ..analytics import (
    DashboardAnalyticsPayload,
    DashboardReadinessStatus,
    DrilldownRequest,
    DrilldownResponse,
    FilterContext,
    FilterDimensions,
    ReconciliationResponse,
    compute_dashboard_analytics,
    get_drilldown_records,
    get_filter_dimensions,
    verify_dataset_analytics,
)
from ..ingestion import registry

logger = logging.getLogger("mkpath.dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class AnalyticsRequest(BaseModel):
    dataset_id: str
    project_id: str = "default"
    dataset_name: Optional[str] = None
    filter_context: Optional[FilterContext] = None


class VerifyRequest(BaseModel):
    dataset_id: str
    project_id: str = "default"
    filter_context: Optional[FilterContext] = None


class ExportRequest(BaseModel):
    dataset_id: str
    project_id: str = "default"
    format: str = "csv"
    filter_context: Optional[FilterContext] = None


@router.post("/analytics", response_model=DashboardAnalyticsPayload)
async def post_dashboard_analytics(req: AnalyticsRequest) -> DashboardAnalyticsPayload:
    """Compute verified, deterministic Power BI-style analytics for executive dashboard."""
    try:
        payload = await run_in_threadpool(
            compute_dashboard_analytics,
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            filter_ctx=req.filter_context,
            dataset_name=req.dataset_name,
        )
        return payload
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found or parquet missing")
    except Exception as exc:
        logger.error("Failed to compute dashboard analytics: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analytics computation error: {str(exc)}")


@router.get("/filters", response_model=FilterDimensions)
async def get_dashboard_filters(
    dataset_id: str = Query(..., description="Target dataset ID"),
    year: Optional[int] = Query(None),
    quarter: Optional[str] = Query(None),
    month: Optional[int] = Query(None),
    team: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    primary_col: Optional[str] = Query(None),
    secondary_col: Optional[str] = Query(None),
) -> FilterDimensions:
    """Get dynamic cascading filter dimensions for the dataset."""
    try:
        filter_ctx = FilterContext(
            year=year,
            quarter=quarter,
            month=month,
            team=team,
            location=location,
            primary_col=primary_col,
            secondary_col=secondary_col,
        )
        dims = await run_in_threadpool(get_filter_dimensions, dataset_id=dataset_id, filter_ctx=filter_ctx)
        return dims
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    except Exception as exc:
        logger.error("Failed to fetch filter dimensions: %s", exc)
        raise HTTPException(status_code=500, detail=f"Filter extraction error: {str(exc)}")


class FilterDimensionsRequest(BaseModel):
    dataset_id: str
    filter_context: Optional[FilterContext] = None


@router.post("/filters", response_model=FilterDimensions)
async def post_dashboard_filters(req: FilterDimensionsRequest) -> FilterDimensions:
    """Post filter context to retrieve dynamic cascading filter dimensions."""
    try:
        dims = await run_in_threadpool(get_filter_dimensions, dataset_id=req.dataset_id, filter_ctx=req.filter_context)
        return dims
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found")
    except Exception as exc:
        logger.error("Failed to fetch filter dimensions: %s", exc)
        raise HTTPException(status_code=500, detail=f"Filter extraction error: {str(exc)}")


@router.post("/drilldown", response_model=DrilldownResponse)
async def post_dashboard_drilldown(req: DrilldownRequest) -> DrilldownResponse:
    """Retrieve verified underlying records for drilldown context."""
    try:
        records = await run_in_threadpool(get_drilldown_records, req=req)
        return records
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found")
    except Exception as exc:
        logger.error("Failed to fetch drilldown records: %s", exc)
        raise HTTPException(status_code=500, detail=f"Drilldown error: {str(exc)}")


@router.post("/verify", response_model=ReconciliationResponse)
async def post_dashboard_verify(req: VerifyRequest) -> ReconciliationResponse:
    """Run independent SQL checks against raw DuckDB tables and reconcile metrics."""
    try:
        res = await run_in_threadpool(
            verify_dataset_analytics,
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            filter_ctx=req.filter_context,
        )
        return res
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found")
    except Exception as exc:
        logger.error("Reconciliation execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Verification error: {str(exc)}")


@router.post("/export")
async def post_dashboard_export(req: ExportRequest) -> Response:
    """Generate verified export report matching exact dashboard calculation state."""
    try:
        payload = await run_in_threadpool(
            compute_dashboard_analytics,
            dataset_id=req.dataset_id,
            project_id=req.project_id,
            filter_ctx=req.filter_context,
        )

        if req.format.lower() == "json":
            return Response(
                content=payload.model_dump_json(indent=2),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=dashboard_report_{req.dataset_id[:8]}.json"
                },
            )

        # CSV Export
        output = StringIO()
        writer = csv.writer(output)

        # Executive Metadata Header
        writer.writerow(["# EXECUTIVE PERFORMANCE MANAGEMENT DASHBOARD - VERIFIED REPORT"])
        writer.writerow(["# Dataset ID", payload.dataset_id])
        writer.writerow(["# Dataset Name", payload.dataset_name])
        writer.writerow(["# Generated At", payload.generated_at])
        writer.writerow(["# Readiness Status", payload.readiness_status.value])
        writer.writerow(["# Total Dataset Records", payload.quality_summary.total_records])
        writer.writerow(["# Filtered Records Context", payload.quality_summary.filtered_records])
        writer.writerow([])

        # Card 1 & 2 Highlights
        writer.writerow(["METRIC", "PERIOD", "VALUE", "CHANGE %", "NOTE"])
        writer.writerow([
            payload.card1_quarter_to_quarter.title,
            payload.card1_quarter_to_quarter.metric_label,
            payload.card1_quarter_to_quarter.current_value,
            payload.card1_quarter_to_quarter.change_formatted,
            payload.card1_quarter_to_quarter.status_note or "Computed",
        ])
        writer.writerow([
            payload.card2_year_over_year.title,
            payload.card2_year_over_year.metric_label,
            payload.card2_year_over_year.current_value,
            payload.card2_year_over_year.change_formatted,
            payload.card2_year_over_year.status_note or "Computed",
        ])
        writer.writerow([])

        # Card 3 Top & Bottom Teams
        writer.writerow(["RANK", "TEAM / CATEGORY", "TYPE", "RAW VALUE", "PERCENTAGE OF GOAL"])
        for item in payload.card3_top_bottom_teams.top_teams:
            writer.writerow([item.rank, item.name, "TOP", item.raw_value, f"{item.percentage:.1f}%"])
        for item in payload.card3_top_bottom_teams.bottom_teams:
            writer.writerow([item.rank, item.name, "BOTTOM", item.raw_value, f"{item.percentage:.1f}%"])
        writer.writerow([])

        # Card 4 Quarterly Series
        writer.writerow(["PERIOD", "YEAR", "QUARTER", "PERFORMANCE BAR", "TREND LINE", "IS CURRENT QTD"])
        for pt in payload.card4_quarterly_performance.series:
            writer.writerow([pt.period_label, pt.year, pt.quarter, pt.bar_value, pt.line_value or "", pt.is_current_qtd])
        writer.writerow([])

        # Card 5 & 6 Donut Gauges
        writer.writerow(["GAUGE", "TAB / DIMENSION", "PERCENTAGE", "NUMERATOR", "DENOMINATOR"])
        writer.writerow([
            payload.card5_meetings_attended.title,
            payload.card5_meetings_attended.active_tab,
            f"{payload.card5_meetings_attended.percentage:.1f}%",
            payload.card5_meetings_attended.numerator,
            payload.card5_meetings_attended.denominator,
        ])
        writer.writerow([
            payload.card6_engineering_performance.title,
            payload.card6_engineering_performance.active_tab,
            f"{payload.card6_engineering_performance.percentage:.1f}%",
            payload.card6_engineering_performance.numerator,
            payload.card6_engineering_performance.denominator,
        ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=dashboard_report_{req.dataset_id[:8]}.csv"
            },
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset {req.dataset_id} not found")
    except Exception as exc:
        logger.error("Export generation error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Export error: {str(exc)}")
