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
from fastapi.responses import HTMLResponse
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
        # Initialize components
        llm_client = LLMClient()

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

        # Determine cache usage
        use_cached = request.use_cache and not request.force_fresh_research
        cache_status_msg = None
        cached_items_count = 0
        fresh_items_count = 0

        # Step 1: Check cache or fetch fresh data
        if use_cached:
            cached_items = research_cache.lookup(request.topic, exact_match=True)
            if cached_items:
                orchestrator_result_raw_items = cached_items
                cache_status_msg = "Cached results"
                cached_items_count = len(cached_items)
            else:
                # No cache hit, fetch fresh
                orchestrator_result = await _fetch_fresh_research(
                    request.topic, request.max_results_per_adapter
                )
                orchestrator_result_raw_items = orchestrator_result.raw_items

                # Save to cache
                saved_count = research_cache.save_items(request.topic, orchestrator_result_raw_items)
                cache_status_msg = f"Fresh research saved to cache ({saved_count} items)"
                fresh_items_count = saved_count

                workspace_manager.save_orchestrator_result(workspace_dir, orchestrator_result)
        else:
            # Force fresh research
            orchestrator_result = await _fetch_fresh_research(
                request.topic, request.max_results_per_adapter
            )
            orchestrator_result_raw_items = orchestrator_result.raw_items

            # Save to cache
            saved_count = research_cache.save_items(request.topic, orchestrator_result_raw_items)
            cache_status_msg = f"Fresh research ({saved_count} items)"
            fresh_items_count = saved_count

            workspace_manager.save_orchestrator_result(workspace_dir, orchestrator_result)

        # Step 2: Rank and deduplicate sources
        ranking_engine = RankingEngine(llm_client=llm_client)

        # 2.1: Deduplicate
        deduplicated = ranking_engine.deduplicate(orchestrator_result_raw_items)

        # 2.2: Score with LLM
        scored_items = ranking_engine.score(
            items=deduplicated,
            research_topic=request.topic,
        )

        # 2.3: Select top papers and patents
        top_papers, top_patents = ranking_engine.select_top(
            scored_items=scored_items,
            top_n=5,
        )

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
            metrics_generator = MetricsGenerator(llm_client=llm_client)
            metrics = metrics_generator.generate(
                topic=request.topic,
                papers=ranked_results.papers,
                patents=ranked_results.patents,
            )
            all_metric_names = [m.name for m in metrics]
            metric_descriptions = {m.name: m.description for m in metrics}

            # Save generated metrics
            workspace_manager.save_artifact(workspace_dir, "metrics.json", [m.model_dump(mode='json') for m in metrics])

        # Step 5: Generate comparison matrix
        comparison_evaluations = None
        if all_metric_names:
            matrix_generator = ComparisonMatrixGenerator(llm_client=llm_client)
            all_sources = ranked_results.patents + ranked_results.papers

            comparison_evaluations = matrix_generator.evaluate_sources(
                sources=all_sources,
                metric_names=all_metric_names,
                metric_descriptions=metric_descriptions,
            )

            # Save comparison evaluations
            workspace_manager.save_artifact(
                workspace_dir,
                "comparison_evaluations.json",
                [e.model_dump() for e in comparison_evaluations]
            )

        # Step 6: Generate report with comparison matrix
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
        )

        # Read report content
        report_content = report_path.read_text(encoding="utf-8")

        # Compile statistics
        papers_raw = [item for item in orchestrator_result_raw_items if item.source_type == "paper"]
        open_access_raw = [p for p in papers_raw if p.is_open_access or p.pdf_url]
        open_access_ranked = [p for p in ranked_results.papers if p.is_open_access or p.pdf_url]

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

        return GenerateResponse(
            success=True,
            message=f"Report generated successfully for topic: {request.topic}",
            report_path=str(report_path),
            report_content=report_content,
            workspace_dir=str(workspace_dir),
            stats=stats,
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



@app.get("/ui", response_class=HTMLResponse)
async def ui():
    """Browser UI for the Research Intelligence Assistant with 2-step workflow."""
    # Read the HTML template
    template_path = Path(__file__).parent / "ria" / "ui_template.html"
    html_content = template_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html_content)
