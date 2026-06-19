"""
FastAPI application for Research Intelligence Assistant.

Provides REST API endpoints to run the research intelligence pipeline.
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ria.adapters import SemanticScholarAdapter, SerpAPIPatentAdapter, MockPatentAdapter
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.orchestrator import SearchOrchestrator
from ria.ranking import RankingEngine
from ria.report import ReportRenderer
from ria.workspace import WorkspaceManager

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


class GenerateResponse(BaseModel):
    """Response model for /generate endpoint."""
    success: bool
    message: str
    report_path: Optional[str] = None
    report_content: Optional[str] = None
    workspace_dir: Optional[str] = None
    stats: Optional[dict] = None


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
    1. SearchOrchestrator - searches patents and papers
    2. WorkspaceManager - persists results
    3. RankingEngine - deduplicates, scores, and ranks sources
    4. MetricsGenerator - generates benchmark metrics
    5. ReportRenderer - creates a Markdown report

    Args:
        request: GenerateRequest with topic and optional parameters

    Returns:
        GenerateResponse with report path, content, and statistics
    """
    try:
        # Initialize components
        llm_client = LLMClient()

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

        # Initialize workspace
        workspace_manager = WorkspaceManager(base_dir="./workspaces")
        workspace_dir = workspace_manager.create(request.topic)

        # Step 1: Search across adapters
        orchestrator_result = await orchestrator.search(
            topic=request.topic,
            max_results_per_adapter=request.max_results_per_adapter,
        )

        # Step 2: Save raw results to workspace
        workspace_manager.save_orchestrator_result(workspace_dir, orchestrator_result)

        # Step 3: Rank and deduplicate sources
        ranking_engine = RankingEngine(llm_client=llm_client)

        # 3.1: Deduplicate
        deduplicated = ranking_engine.deduplicate(orchestrator_result.raw_items)

        # 3.2: Score with LLM
        scored_items = ranking_engine.score(
            items=deduplicated,
            research_topic=request.topic,
        )

        # 3.3: Select top papers and patents
        top_papers, top_patents = ranking_engine.select_top(
            scored_items=scored_items,
            top_n=5,
        )

        # Create RankedResults
        from ria.models import RankedResults
        ranked_results = RankedResults(papers=top_papers, patents=top_patents)

        # Step 4: Save ranked results
        workspace_manager.save_artifact(workspace_dir, "ranked_results.json", ranked_results.model_dump(mode='json'))

        # Step 5: Generate benchmark metrics
        metrics_generator = MetricsGenerator(llm_client=llm_client)
        metrics = metrics_generator.generate(
            topic=request.topic,
            papers=ranked_results.papers,
            patents=ranked_results.patents,
        )

        # Step 6: Save metrics
        workspace_manager.save_artifact(workspace_dir, "metrics.json", [m.model_dump(mode='json') for m in metrics])

        # Step 7: Generate report
        report_renderer = ReportRenderer()
        report_path = report_renderer.generate(
            topic=request.topic,
            ranked_results=ranked_results,
            metrics=metrics,
            workspace_dir=workspace_dir,
        )

        # Read report content
        report_content = report_path.read_text(encoding="utf-8")

        # Compile statistics
        stats = {
            "total_raw_items": len(orchestrator_result.raw_items),
            "patents_found": len([item for item in orchestrator_result.raw_items if item.source_type == "patent"]),
            "papers_found": len([item for item in orchestrator_result.raw_items if item.source_type == "paper"]),
            "ranked_patents": len(ranked_results.patents),
            "ranked_papers": len(ranked_results.papers),
            "metrics_generated": len(metrics),
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
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report: {str(e)}",
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
