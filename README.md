# MK-Path

Multi-agent Knowledge Platform for Autonomous Transformation & Healing

**Positioning:** Evidence-Gated Autonomous Data Platform

## Architecture

- **Backend:** Python 3.10+, FastAPI, MongoDB Atlas, DuckDB (Zero-LLM Profiling), Semantic Knowledge Layer (LangChain / Gemini).
- **Frontend:** React, TypeScript, Tailwind CSS, shadcn/ui.
- **Storage:** Fully isolated to the E: drive environment (`E:\MKPATH`).

## Current Status
- **Phases 1-6:** Backend foundation, API, Ingestion, Profiling, Semantic layer completed and verified.
- **Phase 7:** Frontend application shell completed (React Router, Dashboard, Project Workspace, typed API client).
- **Phase 8:** Universal Data Upload UI completed (Drag and drop, CSV/Excel/JSON/Parquet/SQL/ZIP support, processing state indicators).
- **Phase 9:** Dataset Explorer and Data Quality UI completed (Data visualization, schema inspection, pagination, quality metrics).
- **Phase 10:** Knowledge Layer UI completed (Concept editing, ambiguity resolution panel, deterministic evidence display).
- **Phase 11:** Human-in-the-Loop Clarification UI completed (Semantic Breakpoint logic handling LangGraph pauses).
- **Phase 12:** Agent Execution Center completed (Visual pipeline, node states, safe evidence and output logs).
- **Phase 13:** Data Analyst Workspace completed (Analysis planning, user approval flow, KPIs, explicit provenance tracking).
- **Phase 14:** Temporal Leakage Verification UI completed (Deployment blocking, visual timelines, strictly mapped feature events).
- **Phase 15:** Causal Analysis UI completed (Effect estimation, causal graphs, robust refutation tests, explicit limitations).
- **Phase 16:** Model Tournament UI completed (Candidate scoring, strict optimization terminology, verification-gated artifacts).
- **Phase 17:** Verification Center completed (Central trust interface mapping gates to deployment readiness).
- **Phase 18:** Transformation and Healing UI completed (Automated derived dataset generation rules and approvals).
- **Phase 19:** Artifact Center completed (Model cards, service endpoints, reports with strict verification gating).
- **Phase 20:** Audit UI completed (Chronological event timeline, safe tracking, event filters).
- **Phase 21-23:** End-to-End Integration, Security, and Polish completed (Real API connectivity, strict linting, styling refinement).

## Getting Started

### Backend
1. `cd backend`
2. `..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

### Frontend
1. `cd frontend`
2. `npm run dev`

## Core Capabilities
- DATA → KNOWLEDGE → AGENTS → VERIFICATION → TRANSFORMATION → HEALING
- **Ingestion:** Secure ZIP extraction, extension validation, path traversal prevention.
- **Zero-LLM Profiling:** Deterministic DuckDB metrics and quality scores.
- **Semantic Layer:** Structured mapping of columns to business domains.
- **Human Breakpoint:** Deterministic evidence collection with user resolution persistence.
- **LangGraph Orchestrator:** Strongly-typed state graph governing agent flows.
- **Data Analyst Agent:** Structured LLM planning executed deterministically by DuckDB with full provenance.
- **Temporal Leakage Interceptor:** Strict `available_time <= prediction_time` enforcement blocking leaking features from entering modeling stages.
- **Data Scientist Agent (Causal):** DoWhy-backed effect estimation with explicit assumption logging.
- **Model Tournament:** 3D Pareto optimization (performance, latency, cost) with OOT validation logic for temporal datasets.
- **Explainability & Fairness:** SHAP global/local importance mapping and conditional disparity checking across sensitive attributes.
- **Evidence-Gated Verification Engine:** Aggregates multi-gate deterministic checks strictly enforcing `deployment_status = BLOCKED` upon any failures.
- **Data Healing:** Immutable derivation-based data repairs (imputation/normalization) mapping before/after quality reports.
- **Verified Artifact Generator:** Automated secure generation of FastAPI services, Pydantic schemas, and Pytests entirely reliant on Verification gate passing.
- **Audit Lineage:** Secure deterministic timeline recording for every state-transition (without persisting secrets).
- **Frontend Verification:** React UI safely mapping to all backend hooks including dynamic ZIP multi-file unbundling.
- **E2E Integration:** Full connection of React uploads, LangGraph agent workflows, human breakpoints, and safe artifact generation.
- **Fail-Safe Integrity:** Rigorous failure matrices capturing ZIP path traversal, SQL-drop injections, temporal leakage, and corruption handling gracefully.
- **Storage Isolation Audit:** Aggressive monitoring of drive footprints restricting all system artifacts to `E:\MKPATH` protecting C-drive cache limits.
