"""
ChromaDB-based research cache for storing and retrieving source metadata.

The ResearchCache provides persistent storage for papers and patents to avoid
repeated API calls for the same research topics.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError(
        "ChromaDB is required for research cache. Install with: pip install chromadb"
    )

from ria.models import RawSourceItem, SourceType, ConfidenceLevel


def normalize_topic(topic: str) -> str:
    """
    Normalize a research topic for consistent cache lookups.

    Applies:
    - Lowercase conversion
    - Whitespace normalization
    - Acronym expansion for common terms
    - Punctuation removal (except hyphens in compound words)

    Args:
        topic: Raw research topic string

    Returns:
        Normalized topic string
    """
    # Lowercase
    normalized = topic.lower().strip()

    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)

    # Remove punctuation except hyphens
    normalized = re.sub(r'[^\w\s\-]', '', normalized)

    # Expand common acronyms (physics/simulation context)
    acronym_map = {
        r'\bxpbd\b': 'extended position based dynamics',
        r'\bpbd\b': 'position based dynamics',
        r'\bfem\b': 'finite element method',
        r'\bsph\b': 'smoothed particle hydrodynamics',
        r'\bvr\b': 'virtual reality',
        r'\bar\b': 'augmented reality',
        r'\bai\b': 'artificial intelligence',
        r'\bml\b': 'machine learning',
        r'\bgpu\b': 'graphics processing unit',
    }

    for pattern, expansion in acronym_map.items():
        normalized = re.sub(pattern, expansion, normalized)

    return normalized.strip()


def compute_content_hash(item: RawSourceItem) -> str:
    """
    Compute a content hash for deduplication.

    Uses title + publication_date + source_type to identify unique items.

    Args:
        item: Source item to hash

    Returns:
        SHA256 hex digest (first 16 characters)
    """
    content = f"{item.title}|{item.publication_date}|{item.source_type.value}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class ResearchCache:
    """
    Persistent cache for research source metadata using ChromaDB.

    Stores papers and patents with embeddings for similarity-based retrieval.
    Supports exact topic match and fuzzy similarity search.

    Example:
        cache = ResearchCache()
        cache.save_items("XPBD simulation", raw_items)
        cached = cache.lookup("XPBD simulation")
    """

    def __init__(self, persist_directory: str = "./chroma_db/research"):
        """
        Initialize the research cache with ChromaDB.

        Args:
            persist_directory: Directory for ChromaDB persistence
        """
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="research_cache",
            metadata={"description": "Cached research papers and patents"}
        )

    def save_items(
        self,
        topic: str,
        items: list[RawSourceItem],
    ) -> int:
        """
        Save source items to the cache.

        Args:
            topic: Research topic
            items: List of raw source items to cache

        Returns:
            Number of items saved
        """
        normalized = normalize_topic(topic)
        saved_count = 0

        for item in items:
            cache_id = compute_content_hash(item)

            # Skip if already cached
            existing = self.collection.get(ids=[cache_id])
            if existing["ids"]:
                continue

            # Build searchable document text
            document_parts = [item.title]
            if item.relevance_explanation:
                document_parts.append(item.relevance_explanation)

            document = " ".join(document_parts)

            # Prepare metadata (ChromaDB only supports simple types)
            metadata = {
                "topic": topic,
                "normalized_topic": normalized,
                "source_type": item.source_type.value,
                "title": item.title,
                "source_url": item.source_url,
                "publication_date": item.publication_date or "",
                "author_or_assignee": item.author_or_assignee or "",
                "confidence_level": item.confidence_level.value if item.confidence_level else "",
                "doi": item.doi or "",
                "patent_number": item.patent_number or "",
                "raw_adapter_source": item.raw_adapter_source,
                "venue": item.venue or "",
                "citation_count": item.citation_count or 0,
                "is_open_access": item.is_open_access or False,
                "pdf_url": item.pdf_url or "",
                "fetched_at": datetime.utcnow().isoformat(),
                "relevance_explanation": item.relevance_explanation or "",
            }

            self.collection.add(
                documents=[document],
                metadatas=[metadata],
                ids=[cache_id]
            )
            saved_count += 1

        return saved_count

    def lookup(
        self,
        topic: str,
        exact_match: bool = True,
        similarity_threshold: float = 0.8,
    ) -> list[RawSourceItem]:
        """
        Lookup cached items for a topic.

        Args:
            topic: Research topic to search for
            exact_match: If True, only return exact normalized topic matches
            similarity_threshold: Minimum similarity score for fuzzy matches (0.0-1.0)

        Returns:
            List of cached RawSourceItem objects
        """
        normalized = normalize_topic(topic)

        if exact_match:
            # Exact match on normalized topic
            results = self.collection.get(
                where={"normalized_topic": normalized}
            )
        else:
            # Similarity search with threshold
            query_results = self.collection.query(
                query_texts=[topic],
                n_results=min(100, self.collection.count()),
            )

            # Filter by similarity threshold
            filtered_ids = []
            if query_results["ids"] and query_results["ids"][0]:
                for i, distance in enumerate(query_results["distances"][0]):
                    similarity = 1.0 - distance
                    if similarity >= similarity_threshold:
                        filtered_ids.append(query_results["ids"][0][i])

            if not filtered_ids:
                return []

            results = self.collection.get(ids=filtered_ids)

        if not results["ids"]:
            return []

        # Reconstruct RawSourceItem objects
        items = []
        for i, cache_id in enumerate(results["ids"]):
            metadata = results["metadatas"][i]
            items.append(self._metadata_to_item(metadata))

        return items

    def get_cache_status(self, topic: str) -> dict[str, Any]:
        """
        Get cache status for a topic.

        Args:
            topic: Research topic

        Returns:
            Dictionary with cache statistics
        """
        normalized = normalize_topic(topic)
        items = self.lookup(topic, exact_match=True)

        patents = [item for item in items if item.source_type == SourceType.PATENT]
        papers = [item for item in items if item.source_type == SourceType.PAPER]
        open_access = [p for p in papers if p.is_open_access or p.pdf_url]

        last_fetched = None
        if items:
            fetched_dates = []
            for item_id in [compute_content_hash(item) for item in items]:
                result = self.collection.get(ids=[item_id])
                if result["metadatas"]:
                    fetched_at = result["metadatas"][0].get("fetched_at")
                    if fetched_at:
                        fetched_dates.append(datetime.fromisoformat(fetched_at))

            if fetched_dates:
                last_fetched = max(fetched_dates).isoformat()

        return {
            "topic": topic,
            "normalized_topic": normalized,
            "cached": len(items) > 0,
            "patents_count": len(patents),
            "papers_count": len(papers),
            "open_access_papers_count": len(open_access),
            "last_fetched_at": last_fetched,
            "total_items": len(items),
        }

    def clear_topic(self, topic: str) -> int:
        """
        Clear cached items for a specific topic.

        Args:
            topic: Research topic to clear

        Returns:
            Number of items deleted
        """
        normalized = normalize_topic(topic)
        items = self.lookup(topic, exact_match=True)

        if not items:
            return 0

        ids_to_delete = [compute_content_hash(item) for item in items]
        self.collection.delete(ids=ids_to_delete)

        return len(ids_to_delete)

    def _metadata_to_item(self, metadata: dict[str, Any]) -> RawSourceItem:
        """
        Convert ChromaDB metadata back to RawSourceItem.

        Args:
            metadata: ChromaDB metadata dictionary

        Returns:
            Reconstructed RawSourceItem
        """
        return RawSourceItem(
            title=metadata["title"],
            source_type=SourceType(metadata["source_type"]),
            source_url=metadata["source_url"],
            publication_date=metadata["publication_date"] or None,
            author_or_assignee=metadata["author_or_assignee"] or None,
            relevance_explanation=metadata["relevance_explanation"] or None,
            confidence_level=ConfidenceLevel(metadata["confidence_level"]) if metadata["confidence_level"] else None,
            doi=metadata["doi"] or None,
            patent_number=metadata["patent_number"] or None,
            raw_adapter_source=metadata["raw_adapter_source"],
            venue=metadata["venue"] or None,
            citation_count=metadata["citation_count"] or None,
            is_open_access=metadata["is_open_access"] or None,
            pdf_url=metadata["pdf_url"] or None,
        )
