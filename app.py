"""
FastAPI application for Research Intelligence Assistant.

Provides REST API endpoints to run the research intelligence pipeline.
"""

from dotenv import load_dotenv

load_dotenv(override=True)

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from ria.adapters import SemanticScholarAdapter, SerpAPIPatentAdapter, MockPatentAdapter
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.orchestrator import SearchOrchestrator
from ria.ranking import RankingEngine
from ria.report import ReportRenderer
from ria.workspace import WorkspaceManager

# Load environment variables from .env file
load_dotenv(override=True)

# Initialize FastAPI app
app = FastAPI(
    title="Research Intelligence Assistant",
    description="API for running research intelligence and benchmarking pipelines",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class GenerateRequest(BaseModel):
    """Request model for /generate endpoint."""
    topic: str
    max_results_per_adapter: Optional[int] = 10
    workspace_name: Optional[str] = None
    selected_metrics: Optional[list[str]] = None
    custom_metrics: Optional[list[str]] = None
    use_cache: Optional[bool] = True
    force_fresh_research: Optional[bool] = False


class GenerateResponse(BaseModel):
    """Response model for /generate endpoint."""
    success: bool
    message: str
    report_path: Optional[str] = None
    report_content: Optional[str] = None
    workspace_dir: Optional[str] = None
    stats: Optional[dict] = None
    analytics: Optional[dict] = None
    comparison_evaluations: Optional[list[dict]] = None
    metric_names: Optional[list[str]] = None
    ranked_papers: Optional[list[dict]] = None
    ranked_patents: Optional[list[dict]] = None


class SuggestMetricsRequest(BaseModel):
    """Request model for /suggest-metrics endpoint."""
    topic: str
    max_metrics: Optional[int] = 10


class SuggestMetricsResponse(BaseModel):
    """Response model for /suggest-metrics endpoint."""
    success: bool
    suggested_metrics: list[dict]


class CacheStatusRequest(BaseModel):
    """Request model for /cache/status endpoint."""
    topic: str


class CacheStatusResponse(BaseModel):
    """Response model for /cache/status endpoint."""
    success: bool
    data: dict


class ExportResearchPDFRequest(BaseModel):
    """Request model for /export-research-pdf endpoint."""
    topic: str
    report_content: str
    stats: dict
    analytics: Optional[dict] = None
    comparison_evaluations: Optional[list[dict]] = None
    metric_names: Optional[list[str]] = None
    ranked_papers: Optional[list[dict]] = None
    ranked_patents: Optional[list[dict]] = None


class ExportUsagePDFRequest(BaseModel):
    """Request model for /export-usage-pdf endpoint."""
    topic: str
    analytics: dict


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "message": "Research Intelligence Assistant is running",
        "version": "0.1.0",
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_report(request: GenerateRequest):
    """
    Generate a research intelligence report for the given topic.

    This endpoint runs the complete pipeline:
    1. Check cache for existing research (if use_cache=True and not force_fresh_research)
    2. SearchOrchestrator - searches patents and papers (if not cached or force_fresh_research)
    3. WorkspaceManager - persists results
    4. RankingEngine - deduplicates, scores, and ranks sources
    5. MetricsGenerator - generates benchmark metrics (or use selected_metrics)
    6. ComparisonMatrixGenerator - evaluates sources against metrics
    7. ReportRenderer - creates a Markdown report with comparison matrix

    Args:
        request: GenerateRequest with topic and optional parameters

    Returns:
        GenerateResponse with report path, content, and statistics
    """
    try:
        # Generate unique report ID for LangSmith tracing
        import uuid
        report_id = str(uuid.uuid4())

        # Initialize analytics tracker
        from ria.analytics import AnalyticsTracker
        tracker = AnalyticsTracker(topic=request.topic)

        # Initialize components
        tracker.start_step("Initialize Components")
        llm_client = LLMClient(report_id=report_id, topic=request.topic)

        # Initialize cache and metrics bank
        from ria.research_cache import ResearchCache
        from ria.metrics_bank import MetricsBank
        from ria.comparison_matrix import ComparisonMatrixGenerator

        research_cache = ResearchCache()
        metrics_bank = MetricsBank()
        metrics_bank.initialize_defaults()

        # Initialize workspace
        workspace_manager = WorkspaceManager(base_dir="./workspaces")
        workspace_dir = workspace_manager.create(request.topic)
        tracker.finish_step()

        # Determine cache usage
        use_cached = request.use_cache and not request.force_fresh_research
        cache_status_msg = None
        cached_items_count = 0
        fresh_items_count = 0

        # Step 1: Check cache or fetch fresh data
        tracker.start_step("Check Cache")
        if use_cached:
            cached_items = research_cache.lookup(request.topic, exact_match=True)
            tracker.finish_step()
            if cached_items:
                orchestrator_result_raw_items = cached_items
                cache_status_msg = "Cached results"
                cached_items_count = len(cached_items)
            else:
                # No cache hit, fetch fresh
                tracker.start_step("Fetch Research")
                orchestrator_result = await _fetch_fresh_research(
                    request.topic, request.max_results_per_adapter
                )
                tracker.finish_step()
                orchestrator_result_raw_items = orchestrator_result.raw_items

                # Save to cache
                saved_count = research_cache.save_items(request.topic, orchestrator_result_raw_items)
                cache_status_msg = f"Fresh research saved to cache ({saved_count} items)"
                fresh_items_count = saved_count

                workspace_manager.save_orchestrator_result(workspace_dir, orchestrator_result)
        else:
            # Force fresh research
            tracker.start_step("Fetch Research")
            tracker.finish_step()  # Finish cache check step
            tracker.start_step("Fetch Research")
            orchestrator_result = await _fetch_fresh_research(
                request.topic, request.max_results_per_adapter
            )
            tracker.finish_step()
            orchestrator_result_raw_items = orchestrator_result.raw_items

            # Save to cache
            saved_count = research_cache.save_items(request.topic, orchestrator_result_raw_items)
            cache_status_msg = f"Fresh research ({saved_count} items)"
            fresh_items_count = saved_count

            workspace_manager.save_orchestrator_result(workspace_dir, orchestrator_result)

        # Step 2: Rank and deduplicate sources
        ranking_engine = RankingEngine(llm_client=llm_client)

        # 2.1: Deduplicate
        tracker.start_step("Deduplicate Sources")
        deduplicated = ranking_engine.deduplicate(orchestrator_result_raw_items)
        tracker.finish_step()

        # 2.2: Score with LLM
        tracker.start_step("Score Sources")
        scored_items = ranking_engine.score(
            items=deduplicated,
            research_topic=request.topic,
        )
        # Track LLM calls from scoring (one per source)
        if llm_client.last_call_metadata:
            for _ in deduplicated:
                usage = llm_client.last_call_metadata["usage"]
                tracker.add_llm_call(
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"]
                )
        tracker.finish_step()

        # 2.3: Select top papers and patents
        tracker.start_step("Select Top Sources")
        top_papers, top_patents = ranking_engine.select_top(
            scored_items=scored_items,
            top_n=5,
        )
        tracker.finish_step()

        # Create RankedResults
        from ria.models import RankedResults
        ranked_results = RankedResults(papers=top_papers, patents=top_patents)

        # Step 3: Save ranked results
        workspace_manager.save_artifact(workspace_dir, "ranked_results.json", ranked_results.model_dump(mode='json'))

        # Step 4: Handle metrics (selected/custom or auto-generated)
        all_metric_names = []
        metric_descriptions = {}

        if request.selected_metrics or request.custom_metrics:
            # Use selected and custom metrics
            all_metric_names = (request.selected_metrics or []) + (request.custom_metrics or [])

            # Increment usage for selected metrics
            for metric_name in (request.selected_metrics or []):
                # Find metric ID in metrics bank
                suggestions = metrics_bank.suggest_metrics(metric_name, max_results=1)
                if suggestions:
                    metrics_bank.increment_usage(suggestions[0]["metric_id"])

            # Add custom metrics to bank
            for custom_metric in (request.custom_metrics or []):
                metric_id = custom_metric.lower().replace(" ", "_")
                metrics_bank.add_metric(
                    metric_id=metric_id,
                    name=custom_metric,
                    description=f"Custom metric: {custom_metric}",
                    category="Custom",
                    source="user",
                    usage_count=1,
                )

            # Build metric descriptions
            for metric_name in all_metric_names:
                suggestions = metrics_bank.suggest_metrics(metric_name, max_results=1)
                if suggestions:
                    metric_descriptions[metric_name] = suggestions[0]["description"]
        else:
            # Auto-generate metrics using existing MetricsGenerator
            tracker.start_step("Generate Metrics")
            metrics_generator = MetricsGenerator(llm_client=llm_client)
            metrics = metrics_generator.generate(
                topic=request.topic,
                papers=ranked_results.papers,
                patents=ranked_results.patents,
            )
            # Track LLM call from metrics generation
            if llm_client.last_call_metadata:
                usage = llm_client.last_call_metadata["usage"]
                tracker.add_llm_call(
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"]
                )
            tracker.finish_step()

            all_metric_names = [m.name for m in metrics]
            metric_descriptions = {m.name: m.description for m in metrics}

            # Save generated metrics
            workspace_manager.save_artifact(workspace_dir, "metrics.json", [m.model_dump(mode='json') for m in metrics])

        # Step 5: Generate comparison matrix
        comparison_evaluations = None
        validation_result = None
        if all_metric_names:
            tracker.start_step("Evaluate Comparison Matrix")
            matrix_generator = ComparisonMatrixGenerator(llm_client=llm_client)
            all_sources = ranked_results.patents + ranked_results.papers

            comparison_evaluations = matrix_generator.evaluate_sources(
                sources=all_sources,
                metric_names=all_metric_names,
                metric_descriptions=metric_descriptions,
            )

            # Track LLM calls from comparison matrix (one per source)
            if llm_client.last_call_metadata:
                for _ in all_sources:
                    usage = llm_client.last_call_metadata["usage"]
                    tracker.add_llm_call(
                        prompt_tokens=usage["prompt_tokens"],
                        completion_tokens=usage["completion_tokens"]
                    )
            tracker.finish_step()

            # Save initial comparison evaluations
            workspace_manager.save_artifact(
                workspace_dir,
                "comparison_evaluations_initial.json",
                [e.model_dump() for e in comparison_evaluations]
            )

            # Step 5.5: Validate comparison matrix with Comparison Agent
            try:
                from ria.agents import ComparisonAgent

                comparison_agent = ComparisonAgent(
                    llm_client=llm_client,
                    analytics_tracker=tracker,
                )

                validation_result = comparison_agent.validate_matrix(
                    topic=request.topic,
                    sources=all_sources,
                    selected_metrics=all_metric_names,
                    initial_matrix=comparison_evaluations,
                    metric_descriptions=metric_descriptions,
                )

                # Use validated matrix for report
                comparison_evaluations = validation_result.validated_matrix

                # Save validated comparison evaluations
                workspace_manager.save_artifact(
                    workspace_dir,
                    "comparison_evaluations.json",
                    [e.model_dump() for e in comparison_evaluations]
                )

                # Save validation result
                workspace_manager.save_artifact(
                    workspace_dir,
                    "comparison_validation.json",
                    validation_result.model_dump()
                )

            except Exception as validation_error:
                # Fallback: use original matrix if validation fails
                import traceback
                print(f"Warning: Comparison validation failed: {validation_error}")
                traceback.print_exc()

                # Save original comparison evaluations
                workspace_manager.save_artifact(
                    workspace_dir,
                    "comparison_evaluations.json",
                    [e.model_dump() for e in comparison_evaluations]
                )

                # Create minimal validation result
                validation_result = None

        # Step 6: Generate report with comparison matrix
        tracker.start_step("Generate Report")
        report_renderer = ReportRenderer()

        # Create dummy metrics list if using selected metrics
        from ria.models import BenchmarkMetric
        metrics_for_report = [
            BenchmarkMetric(name=name, description=metric_descriptions.get(name, ""), category="")
            for name in all_metric_names
        ]

        report_path = report_renderer.generate(
            topic=request.topic,
            ranked_results=ranked_results,
            metrics=metrics_for_report,
            workspace_dir=workspace_dir,
            comparison_evaluations=comparison_evaluations,
            comparison_metric_names=all_metric_names if comparison_evaluations else None,
            cache_status=cache_status_msg,
            validation_summary=validation_result.validation_summary if validation_result else None,
        )
        tracker.finish_step()

        # Read report content
        report_content = report_path.read_text(encoding="utf-8")

        # Compile statistics
        papers_raw = [item for item in orchestrator_result_raw_items if item.source_type == "paper"]
        open_access_raw = [p for p in papers_raw if p.is_open_access or p.pdf_url]
        open_access_ranked = [p for p in ranked_results.papers if p.is_open_access or p.pdf_url]

        # Finalize analytics tracking
        tracker.set_cache_status(
            status=cache_status_msg,
            cached_count=cached_items_count,
            fresh_count=fresh_items_count
        )
        tracker.set_data_counts(
            papers=len(papers_raw),
            patents=len([item for item in orchestrator_result_raw_items if item.source_type == "patent"]),
            open_access_papers=len(open_access_raw)
        )

        # Set LangSmith trace info if available
        if llm_client.langsmith_enabled and llm_client.last_call_metadata:
            trace_id = llm_client.last_call_metadata.get("trace_id")
            trace_url = llm_client.last_call_metadata.get("trace_url")
            if trace_id:
                tracker.set_langsmith_trace(trace_id, trace_url)

        tracker.finish()

        # Retrieve analytics from LangSmith if available, otherwise use internal tracker
        from ria.langsmith_analytics import LangSmithAnalyticsProvider
        import asyncio

        langsmith_provider = LangSmithAnalyticsProvider()

        # Wait briefly for LangSmith traces to flush (async tracing may lag)
        if langsmith_provider.enabled:
            await asyncio.sleep(2)

        # Get analytics (will use LangSmith if available, or fall back to internal tracker)
        analytics_data = await langsmith_provider.get_analytics_for_report(
            report_id=report_id,
            fallback_analytics=tracker.get_analytics().to_dict(),
            topic=request.topic,
            max_age_minutes=10,
        )

        # Save analytics to workspace
        workspace_manager.save_artifact(workspace_dir, "analytics.json", analytics_data)

        stats = {
            "total_raw_items": len(orchestrator_result_raw_items),
            "patents_found": len([item for item in orchestrator_result_raw_items if item.source_type == "patent"]),
            "papers_found": len(papers_raw),
            "open_access_papers_found": len(open_access_raw),
            "ranked_patents": len(ranked_results.patents),
            "ranked_papers": len(ranked_results.papers),
            "open_access_papers_ranked": len(open_access_ranked),
            "metrics_generated": len(all_metric_names),
            "cache_status": cache_status_msg,
            "cached_items_used": cached_items_count,
            "fresh_items_fetched": fresh_items_count,
        }

        # Serialize comparison evaluations and ranked results for JSON response
        comparison_evals_dict = None
        if comparison_evaluations:
            comparison_evals_dict = [e.model_dump() if hasattr(e, 'model_dump') else e for e in comparison_evaluations]

        ranked_papers_dict = [p.model_dump(mode='json') if hasattr(p, 'model_dump') else p for p in ranked_results.papers]
        ranked_patents_dict = [p.model_dump(mode='json') if hasattr(p, 'model_dump') else p for p in ranked_results.patents]

        return GenerateResponse(
            success=True,
            message=f"Report generated successfully for topic: {request.topic}",
            report_path=str(report_path),
            report_content=report_content,
            workspace_dir=str(workspace_dir),
            stats=stats,
            analytics=analytics_data,
            comparison_evaluations=comparison_evals_dict,
            metric_names=all_metric_names if all_metric_names else None,
            ranked_papers=ranked_papers_dict,
            ranked_patents=ranked_patents_dict,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}",
        )


async def _fetch_fresh_research(topic: str, max_results_per_adapter: int):
    """Helper function to fetch fresh research data."""
    # Choose patent adapter based on SERPAPI_API_KEY availability
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        patent_adapter = SerpAPIPatentAdapter()
    else:
        patent_adapter = MockPatentAdapter()

    # Initialize adapters and orchestrator
    adapters = [
        patent_adapter,
        SemanticScholarAdapter(),
    ]
    orchestrator = SearchOrchestrator(adapters=adapters)

    # Search across adapters
    return await orchestrator.search(
        topic=topic,
        max_results_per_adapter=max_results_per_adapter,
    )


@app.post("/suggest-metrics", response_model=SuggestMetricsResponse)
async def suggest_metrics(request: SuggestMetricsRequest):
    """
    Suggest relevant metrics for a research topic.

    Uses ChromaDB-based metrics bank to retrieve relevant metrics
    based on embeddings similarity search.

    Args:
        request: SuggestMetricsRequest with topic and max_metrics

    Returns:
        SuggestMetricsResponse with suggested metrics
    """
    try:
        from ria.metrics_bank import MetricsBank

        metrics_bank = MetricsBank()
        metrics_bank.initialize_defaults()

        suggestions = metrics_bank.suggest_metrics(
            topic=request.topic,
            max_results=request.max_metrics,
        )

        return SuggestMetricsResponse(
            success=True,
            suggested_metrics=suggestions,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error suggesting metrics: {str(e)}",
        )


@app.post("/cache/status", response_model=CacheStatusResponse)
async def cache_status(request: CacheStatusRequest):
    """
    Get cache status for a research topic.

    Returns information about cached papers and patents for the topic.

    Args:
        request: CacheStatusRequest with topic

    Returns:
        CacheStatusResponse with cache statistics
    """
    try:
        from ria.research_cache import ResearchCache

        research_cache = ResearchCache()
        status = research_cache.get_cache_status(request.topic)

        return CacheStatusResponse(
            success=True,
            data=status,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache status: {str(e)}",
        )


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    serpapi_configured = bool(os.getenv("SERPAPI_API_KEY"))
    openai_configured = bool(os.getenv("OPENAI_API_KEY"))

    return {
        "status": "healthy",
        "api_keys": {
            "serpapi": serpapi_configured,
            "openai": openai_configured,
        },
        "llm_model": os.getenv("LLM_MODEL", "claude-haiku"),
        "base_url": os.getenv("OPENAI_BASE_URL", "default"),
    }



@app.post("/export-research-pdf")
async def export_research_pdf(request: ExportResearchPDFRequest):
    """
    Export research report as PDF.

    Generates a professional PDF document containing:
    - Title and metadata
    - Report statistics
    - Executive summary
    - Comparison matrix (if available)
    - Top patents and papers
    - References

    Does not expose API keys or secrets.

    Args:
        request: ExportResearchPDFRequest with report data

    Returns:
        FileResponse with PDF file
    """
    try:
        from ria.pdf_export import PDFExporter

        exporter = PDFExporter()
        pdf_path = exporter.generate_research_report_pdf(
            topic=request.topic,
            report_content=request.report_content,
            stats=request.stats,
            analytics=request.analytics,
            comparison_evaluations=request.comparison_evaluations,
            metric_names=request.metric_names,
            ranked_papers=request.ranked_papers,
            ranked_patents=request.ranked_patents,
        )

        # Generate safe filename for download
        safe_topic = "".join(c for c in request.topic if c.isalnum() or c in (' ', '-', '_'))[:50]
        safe_topic = safe_topic.replace(' ', '_')
        download_filename = f"research_report_{safe_topic}.pdf"

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=download_filename,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating research PDF: {str(e)}",
        )


@app.post("/export-usage-pdf")
async def export_usage_pdf(request: ExportUsagePDFRequest):
    """
    Export LLM usage analytics as PDF.

    Generates a PDF document containing:
    - Topic and execution metadata
    - Total execution time and LLM statistics
    - Token usage (prompt, completion, total)
    - Estimated costs (clearly labeled as estimates)
    - Per-step breakdown
    - Workflow pipeline summary
    - LangSmith trace info (if available)

    Does not expose API keys or secrets.
    Costs are labeled as estimates, not official invoices.

    Args:
        request: ExportUsagePDFRequest with analytics data

    Returns:
        FileResponse with PDF file
    """
    try:
        from ria.pdf_export import PDFExporter

        exporter = PDFExporter()
        pdf_path = exporter.generate_usage_report_pdf(
            topic=request.topic,
            analytics=request.analytics,
        )

        # Generate safe filename for download
        safe_topic = "".join(c for c in request.topic if c.isalnum() or c in (' ', '-', '_'))[:50]
        safe_topic = safe_topic.replace(' ', '_')
        download_filename = f"llm_usage_report_{safe_topic}.pdf"

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=download_filename,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating usage PDF: {str(e)}",
        )


@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Browser UI for the Research Intelligence Assistant with 2-step workflow."""
    # Read the HTML template
    template_path = Path(__file__).parent / "ria" / "ui_template.html"
    html_content = template_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
