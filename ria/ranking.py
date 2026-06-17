"""
Ranking engine for deduplicating, scoring, and selecting top sources.

The RankingEngine takes raw search results and produces ranked outputs by:
1. Deduplicating by title, DOI, and patent number
2. Scoring each source for relevance using LLM-assisted evaluation
3. Selecting the top 3 papers and top 3 patents
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ria.llm import LLMClient
from ria.models import RawSourceItem, ScoredSourceItem, SourceType


class RelevanceScore(BaseModel):
    """LLM-generated relevance score with reasoning."""
    score: float = Field(ge=0.0, le=1.0, description="Relevance score from 0.0 to 1.0")
    reasoning: str = Field(description="Brief explanation of the score")


class RankingEngine:
    """
    Engine for ranking and selecting research sources.

    Uses LLM-assisted scoring to evaluate source relevance and selects
    the top papers and patents after deduplication.

    Example:
        engine = RankingEngine(llm_client)
        deduplicated = engine.deduplicate(raw_items)
        scored = engine.score(deduplicated, "XPBD simulation")
        top_papers, top_patents = engine.select_top(scored)
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the ranking engine.

        Args:
            llm_client: LLM client for scoring relevance
        """
        self.llm = llm_client

    def deduplicate(self, items: list[RawSourceItem]) -> list[RawSourceItem]:
        """
        Remove duplicate sources by title, DOI, and patent number.

        Deduplication logic:
        1. Remove duplicates by normalized title (case-insensitive, whitespace-normalized)
        2. Remove duplicates by DOI if available
        3. Remove duplicates by patent number if available

        When duplicates are found, the first occurrence is kept.

        Args:
            items: List of raw source items to deduplicate

        Returns:
            Deduplicated list of source items
        """
        seen_titles: set[str] = set()
        seen_dois: set[str] = set()
        seen_patent_numbers: set[str] = set()

        deduplicated: list[RawSourceItem] = []

        for item in items:
            # Normalize title for comparison
            normalized_title = " ".join(item.title.lower().split())

            # Check for duplicate title
            if normalized_title in seen_titles:
                continue

            # Check for duplicate DOI
            if item.doi:
                normalized_doi = item.doi.lower().strip()
                if normalized_doi in seen_dois:
                    continue
                seen_dois.add(normalized_doi)

            # Check for duplicate patent number
            if item.patent_number:
                normalized_patent = item.patent_number.upper().strip()
                if normalized_patent in seen_patent_numbers:
                    continue
                seen_patent_numbers.add(normalized_patent)

            # Not a duplicate - add to results
            seen_titles.add(normalized_title)
            deduplicated.append(item)

        return deduplicated

    def score(
        self,
        items: list[RawSourceItem],
        research_topic: str,
    ) -> list[ScoredSourceItem]:
        """
        Score each source for relevance to the research topic.

        Uses the LLM to generate a relevance score from 0.0 to 1.0 along
        with reasoning. The score reflects how relevant the source is to
        the research topic based on its title, abstract/explanation, and metadata.

        Args:
            items: List of raw source items to score
            research_topic: The research topic to score against

        Returns:
            List of scored source items with relevance_score and updated
            relevance_explanation (includes the LLM's reasoning)
        """
        scored_items: list[ScoredSourceItem] = []

        for item in items:
            # Build scoring prompt
            source_info = self._format_source_for_scoring(item)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a research analyst evaluating source relevance. "
                        "Score how relevant a source is to a research topic on a scale from 0.0 to 1.0. "
                        "Consider the title, abstract/explanation, and metadata. "
                        "Be rigorous: 1.0 means highly relevant and directly addresses the topic, "
                        "0.5 means moderately relevant or tangentially related, "
                        "0.0 means not relevant at all."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Research topic: {research_topic}\n\n"
                        f"Source to evaluate:\n{source_info}\n\n"
                        f"Provide a relevance score (0.0 to 1.0) and brief reasoning."
                    ),
                },
            ]

            # Get LLM score
            try:
                relevance = self.llm.chat_json(
                    messages=messages,
                    response_model=RelevanceScore,
                    temperature=0.3,  # Lower temperature for more consistent scoring
                )

                # Create scored item (exclude relevance_explanation to avoid duplicate)
                scored_item = ScoredSourceItem(
                    **item.model_dump(exclude={'relevance_explanation'}),
                    relevance_score=relevance.score,
                    relevance_explanation=relevance.reasoning,
                )
                scored_items.append(scored_item)

            except Exception as e:
                # If scoring fails, assign a default low score
                print(f"Warning: Failed to score item '{item.title}': {e}")
                scored_item = ScoredSourceItem(
                    **item.model_dump(exclude={'relevance_explanation'}),
                    relevance_score=0.0,
                    relevance_explanation=f"Scoring failed: {str(e)}",
                )
                scored_items.append(scored_item)

        return scored_items

    def _format_source_for_scoring(self, item: RawSourceItem) -> str:
        """
        Format a source item into a text description for LLM scoring.

        Args:
            item: Source item to format

        Returns:
            Formatted text description
        """
        lines = [
            f"Title: {item.title}",
            f"Type: {item.source_type.value}",
        ]

        if item.publication_date:
            lines.append(f"Date: {item.publication_date}")

        if item.author_or_assignee:
            lines.append(f"Author/Assignee: {item.author_or_assignee}")

        if item.relevance_explanation:
            lines.append(f"Abstract/Description: {item.relevance_explanation}")

        if item.doi:
            lines.append(f"DOI: {item.doi}")

        if item.patent_number:
            lines.append(f"Patent Number: {item.patent_number}")

        return "\n".join(lines)

    def select_top(
        self,
        scored_items: list[ScoredSourceItem],
        top_n: int = 3,
    ) -> tuple[list[ScoredSourceItem], list[ScoredSourceItem]]:
        """
        Select the top N papers and top N patents by score.

        Sorts items by relevance_score in descending order and selects
        the top N from each source type.

        Args:
            scored_items: List of scored source items
            top_n: Number of items to select from each type (default: 3)

        Returns:
            Tuple of (top_papers, top_patents), each sorted by score descending
        """
        # Separate by source type
        papers = [item for item in scored_items if item.source_type == SourceType.PAPER]
        patents = [item for item in scored_items if item.source_type == SourceType.PATENT]

        # Sort by score descending
        papers.sort(key=lambda x: x.relevance_score, reverse=True)
        patents.sort(key=lambda x: x.relevance_score, reverse=True)

        # Select top N
        top_papers = papers[:top_n]
        top_patents = patents[:top_n]

        return top_papers, top_patents
