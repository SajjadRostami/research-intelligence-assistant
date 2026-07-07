"""
Comparison Agent for validating source comparison matrices.

The ComparisonAgent acts as a critic/reviewer that validates each cell
in the comparison matrix before the final report is generated.

It performs:
1. Rule-based validation for specific metrics (Open Access, XPBD, etc.)
2. LLM-based validation for ambiguous evaluations
3. Change tracking with explanations
4. Confidence scoring

The agent ensures that YES/PART/NO values are justified by evidence.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ria.comparison_matrix import MetricEvaluation, SourceMetricEvaluation
from ria.llm import LLMClient
from ria.models import ScoredSourceItem


class CellValidation(BaseModel):
    """Validation result for a single matrix cell."""
    metric_name: str
    original_status: Literal["full", "partial", "none"]
    validated_status: Literal["full", "partial", "none"]
    confidence: Literal["high", "medium", "low"]
    evidence: str
    changed: bool
    reason_for_change: Optional[str] = None


class SourceValidation(BaseModel):
    """Validation result for all cells in a single source."""
    source_id: str
    source_title: str
    cells: list[CellValidation]


class ValidationChange(BaseModel):
    """A single change made during validation."""
    source_label: str
    metric: str
    old_status: Literal["YES", "PART", "NO"]
    new_status: Literal["YES", "PART", "NO"]
    reason: str


class ValidationResult(BaseModel):
    """Complete validation result for the comparison matrix."""
    validated_matrix: list[SourceMetricEvaluation]
    changes: list[ValidationChange]
    validation_summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    cells_reviewed: int
    cells_changed: int


class ComparisonAgent:
    """
    Agent for validating source comparison matrices.

    The ComparisonAgent reviews each source/metric evaluation and validates
    whether the coverage status (full/partial/none) is justified by the
    available evidence.

    It uses rule-based checks for well-defined metrics and LLM validation
    for ambiguous cases.

    Example:
        agent = ComparisonAgent(llm_client, analytics_tracker)
        result = agent.validate_matrix(
            topic="XPBD soft body simulation",
            sources=all_sources,
            selected_metrics=["XPBD Support", "Open Access"],
            initial_matrix=comparison_evaluations
        )
    """

    # Status mapping for internal consistency
    STATUS_MAP = {
        "full": "YES",
        "partial": "PART",
        "none": "NO",
    }

    REVERSE_STATUS_MAP = {
        "YES": "full",
        "PART": "partial",
        "NO": "none",
    }

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        analytics_tracker: Optional[Any] = None,
    ):
        """
        Initialize the Comparison Agent.

        Args:
            llm_client: LLM client for validation (optional)
            analytics_tracker: Analytics tracker for metrics (optional)
        """
        self.llm = llm_client
        self.tracker = analytics_tracker

    def validate_matrix(
        self,
        topic: str,
        sources: list[ScoredSourceItem],
        selected_metrics: list[str],
        initial_matrix: list[SourceMetricEvaluation],
        metric_descriptions: dict[str, str] | None = None,
    ) -> ValidationResult:
        """
        Validate the comparison matrix.

        Args:
            topic: Research topic
            sources: List of source items being evaluated
            selected_metrics: List of metric names
            initial_matrix: Initial comparison matrix evaluations
            metric_descriptions: Optional metric descriptions

        Returns:
            ValidationResult with validated matrix and changes
        """
        if self.tracker:
            self.tracker.start_step("Validate Comparison Matrix")

        # Build source lookup
        source_lookup = {self._generate_source_id(s): s for s in sources}

        # Track changes
        changes: list[ValidationChange] = []
        validated_evaluations: list[SourceMetricEvaluation] = []

        cells_reviewed = 0
        cells_changed = 0
        confidence_scores = []

        # Validate each source evaluation
        for source_eval in initial_matrix:
            source = source_lookup.get(source_eval.source_id)
            if not source:
                # Source not found, keep original
                validated_evaluations.append(source_eval)
                continue

            # Validate each metric evaluation for this source
            validated_metric_evals = []
            for metric_eval in source_eval.metric_evaluations:
                cells_reviewed += 1

                # Rule-based validation
                rule_result = self._apply_rule_based_validation(
                    source=source,
                    metric_name=metric_eval.metric_name,
                    current_status=metric_eval.status,
                    metric_description=metric_descriptions.get(metric_eval.metric_name) if metric_descriptions else None,
                )

                if rule_result:
                    # Rule-based validation found a correction
                    validated_status, confidence, evidence, reason = rule_result
                    if validated_status != metric_eval.status:
                        cells_changed += 1
                        changes.append(ValidationChange(
                            source_label=self._get_source_label(source),
                            metric=metric_eval.metric_name,
                            old_status=self.STATUS_MAP[metric_eval.status],
                            new_status=self.STATUS_MAP[validated_status],
                            reason=reason,
                        ))

                    validated_metric_evals.append(MetricEvaluation(
                        metric_name=metric_eval.metric_name,
                        status=validated_status,
                        symbol=self._status_to_symbol(validated_status),
                        score=self._status_to_score(validated_status),
                        evidence=evidence,
                        confidence=confidence,
                    ))
                    confidence_scores.append(self._confidence_to_score(confidence))

                elif self.llm:
                    # LLM validation for ambiguous cases
                    llm_result = self._apply_llm_validation(
                        topic=topic,
                        source=source,
                        metric_name=metric_eval.metric_name,
                        current_status=metric_eval.status,
                        current_evidence=metric_eval.evidence,
                        metric_description=metric_descriptions.get(metric_eval.metric_name) if metric_descriptions else None,
                    )

                    if llm_result:
                        validated_status, confidence, evidence, reason = llm_result
                        if validated_status != metric_eval.status:
                            cells_changed += 1
                            changes.append(ValidationChange(
                                source_label=self._get_source_label(source),
                                metric=metric_eval.metric_name,
                                old_status=self.STATUS_MAP[metric_eval.status],
                                new_status=self.STATUS_MAP[validated_status],
                                reason=reason,
                            ))

                        validated_metric_evals.append(MetricEvaluation(
                            metric_name=metric_eval.metric_name,
                            status=validated_status,
                            symbol=self._status_to_symbol(validated_status),
                            score=self._status_to_score(validated_status),
                            evidence=evidence,
                            confidence=confidence,
                        ))
                        confidence_scores.append(self._confidence_to_score(confidence))
                    else:
                        # LLM validation failed, keep original
                        validated_metric_evals.append(metric_eval)
                        confidence_scores.append(self._confidence_to_score(metric_eval.confidence))
                else:
                    # No LLM available, keep original
                    validated_metric_evals.append(metric_eval)
                    confidence_scores.append(self._confidence_to_score(metric_eval.confidence))

            # Calculate overall score for validated source
            total_score = sum(m.score for m in validated_metric_evals)
            overall_score = round(total_score / len(selected_metrics), 2) if selected_metrics else 0.0

            validated_evaluations.append(SourceMetricEvaluation(
                source_id=source_eval.source_id,
                source_title=source_eval.source_title,
                source_type=source_eval.source_type,
                metric_evaluations=validated_metric_evals,
                overall_score=overall_score,
            ))

        # Calculate overall confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Build validation summary
        summary = self._build_validation_summary(
            cells_reviewed=cells_reviewed,
            cells_changed=cells_changed,
            changes=changes,
        )

        if self.tracker:
            self.tracker.finish_step()
            # Add analytics metrics
            self.tracker.custom_metrics["comparison_cells_reviewed"] = cells_reviewed
            self.tracker.custom_metrics["comparison_cells_changed"] = cells_changed
            self.tracker.custom_metrics["comparison_agent_confidence"] = round(avg_confidence, 2)

        return ValidationResult(
            validated_matrix=validated_evaluations,
            changes=changes,
            validation_summary=summary,
            confidence_score=round(avg_confidence, 2),
            cells_reviewed=cells_reviewed,
            cells_changed=cells_changed,
        )

    def _apply_rule_based_validation(
        self,
        source: ScoredSourceItem,
        metric_name: str,
        current_status: Literal["full", "partial", "none"],
        metric_description: str | None,
    ) -> tuple[Literal["full", "partial", "none"], Literal["high", "medium", "low"], str, str] | None:
        """
        Apply rule-based validation for well-defined metrics.

        Returns:
            Tuple of (validated_status, confidence, evidence, reason) or None
        """
        metric_lower = metric_name.lower()

        # Rule 1: Open Access metric
        if "open access" in metric_lower:
            if source.is_open_access or source.pdf_url:
                validated_status = "full"
                evidence = f"Open access confirmed: PDF available at {source.pdf_url}" if source.pdf_url else "Source is marked as open access."
                if current_status != "full":
                    reason = "Open access status verified: PDF URL exists or source is marked open access."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            else:
                validated_status = "none"
                evidence = "No open access or PDF URL found."
                if current_status != "none":
                    reason = "Open access not available: no PDF URL and not marked as open access."
                    return ("none", "high", evidence, reason)
                return ("none", "high", evidence, "Already correct.")

        # Rule 2: Patent / IP metric
        if any(kw in metric_lower for kw in ["patent", "ip", "intellectual property"]):
            if source.source_type.value == "patent":
                validated_status = "full"
                evidence = f"Source is a patent: {source.patent_number}"
                if current_status != "full":
                    reason = "Source is a patent, so it inherently relates to IP/patents."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            else:
                # Papers may discuss patents but don't inherently represent IP
                # Check if patent is mentioned in title or relevance
                text_to_check = f"{source.title} {source.relevance_explanation or ''}".lower()
                if "patent" in text_to_check or "intellectual property" in text_to_check:
                    validated_status = "partial"
                    evidence = "Paper discusses patents or IP but is not itself a patent."
                    if current_status != "partial":
                        reason = "Paper discusses patents but is not a patent itself."
                        return ("partial", "medium", evidence, reason)
                    return ("partial", "medium", evidence, "Already correct.")
                else:
                    validated_status = "none"
                    evidence = "Paper does not mention patents or IP."
                    if current_status != "none":
                        reason = "Paper does not mention patents or IP."
                        return ("none", "high", evidence, reason)
                    return ("none", "high", evidence, "Already correct.")

        # Rule 3: XPBD Support
        if "xpbd" in metric_lower or "extended position based dynamics" in metric_lower:
            text_to_check = f"{source.title} {source.relevance_explanation or ''}".lower()
            if "xpbd" in text_to_check or "extended position based dynamics" in text_to_check:
                validated_status = "full"
                evidence = "Explicitly mentions XPBD or Extended Position Based Dynamics."
                if current_status != "full":
                    reason = "Source explicitly mentions XPBD or Extended Position Based Dynamics."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            elif any(kw in text_to_check for kw in ["position-based", "position based", "pbd", "constraint-based"]):
                validated_status = "partial"
                evidence = "Mentions position-based dynamics or constraint-based simulation but not XPBD explicitly."
                if current_status != "partial":
                    reason = "Mentions related methods (PBD, constraint-based) but not XPBD explicitly."
                    return ("partial", "medium", evidence, reason)
                return ("partial", "medium", evidence, "Already correct.")
            else:
                validated_status = "none"
                evidence = "Does not mention XPBD, PBD, or position-based dynamics."
                if current_status != "none":
                    reason = "No mention of XPBD or related position-based dynamics methods."
                    return ("none", "high", evidence, reason)
                return ("none", "high", evidence, "Already correct.")

        # Rule 4: VR HMD Integration
        if any(kw in metric_lower for kw in ["vr", "hmd", "head-mounted", "virtual reality"]):
            text_to_check = f"{source.title} {source.relevance_explanation or ''}".lower()
            if any(kw in text_to_check for kw in ["vr", "hmd", "head-mounted display", "virtual reality", "oculus", "htc vive"]):
                validated_status = "full"
                evidence = "Explicitly mentions VR, HMD, or virtual reality."
                if current_status != "full":
                    reason = "Source explicitly mentions VR/HMD/virtual reality."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            elif any(kw in text_to_check for kw in ["simulation", "training", "immersive"]):
                validated_status = "partial"
                evidence = "Mentions simulation/training context that may involve VR but not explicit."
                if current_status != "partial":
                    reason = "Mentions simulation/training but VR integration not explicit."
                    return ("partial", "low", evidence, reason)
                return ("partial", "low", evidence, "Already correct.")
            else:
                validated_status = "none"
                evidence = "Does not mention VR, HMD, or virtual reality."
                if current_status != "none":
                    reason = "No mention of VR or HMD."
                    return ("none", "high", evidence, reason)
                return ("none", "high", evidence, "Already correct.")

        # Rule 5: Haptic Robot Support
        if any(kw in metric_lower for kw in ["haptic", "force feedback", "tactile"]):
            text_to_check = f"{source.title} {source.relevance_explanation or ''}".lower()
            if any(kw in text_to_check for kw in ["haptic device", "haptic robot", "force feedback device", "haptic interface", "robotic haptic"]):
                validated_status = "full"
                evidence = "Explicitly mentions haptic devices, robots, or force feedback interfaces."
                if current_status != "full":
                    reason = "Source explicitly mentions haptic devices or robotic haptics."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            elif any(kw in text_to_check for kw in ["haptic feedback", "haptic", "force feedback", "tactile"]):
                validated_status = "partial"
                evidence = "Mentions haptic feedback or tactile interaction but no device/robot details."
                if current_status != "partial":
                    reason = "Mentions haptic feedback but no explicit device or robot details."
                    return ("partial", "medium", evidence, reason)
                return ("partial", "medium", evidence, "Already correct.")
            else:
                validated_status = "none"
                evidence = "Does not mention haptic devices or force feedback."
                if current_status != "none":
                    reason = "No mention of haptic or force feedback."
                    return ("none", "high", evidence, reason)
                return ("none", "high", evidence, "Already correct.")

        # Rule 6: AI Support
        if any(kw in metric_lower for kw in ["ai", "machine learning", "deep learning", "neural"]):
            text_to_check = f"{source.title} {source.relevance_explanation or ''}".lower()
            if any(kw in text_to_check for kw in ["ai", "machine learning", "deep learning", "neural network", "learning-based", "ml "]):
                validated_status = "full"
                evidence = "Explicitly mentions AI, machine learning, or deep learning."
                if current_status != "full":
                    reason = "Source explicitly mentions AI, ML, or deep learning."
                    return ("full", "high", evidence, reason)
                return ("full", "high", evidence, "Already correct.")
            elif any(kw in text_to_check for kw in ["optimization", "automated", "intelligent", "adaptive"]):
                validated_status = "partial"
                evidence = "Mentions optimization or automation but not clearly AI/ML."
                if current_status != "partial":
                    reason = "Mentions optimization/automation but AI/ML not explicit."
                    return ("partial", "low", evidence, reason)
                return ("partial", "low", evidence, "Already correct.")
            else:
                validated_status = "none"
                evidence = "Does not mention AI, machine learning, or deep learning."
                if current_status != "none":
                    reason = "No mention of AI or ML."
                    return ("none", "high", evidence, reason)
                return ("none", "high", evidence, "Already correct.")

        # No rule-based validation applies
        return None

    def _apply_llm_validation(
        self,
        topic: str,
        source: ScoredSourceItem,
        metric_name: str,
        current_status: Literal["full", "partial", "none"],
        current_evidence: str,
        metric_description: str | None,
    ) -> tuple[Literal["full", "partial", "none"], Literal["high", "medium", "low"], str, str] | None:
        """
        Apply LLM-based validation for ambiguous cases.

        Returns:
            Tuple of (validated_status, confidence, evidence, reason) or None
        """
        if not self.llm:
            return None

        # Build source context
        source_context = self._build_source_context(source)

        # Build prompt
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a critical reviewer validating a comparison matrix cell.\n\n"
                    "Your task is to determine whether the current status (full/partial/none) "
                    "is justified by the available evidence.\n\n"
                    "CRITICAL RULES:\n"
                    "- Base your decision ONLY on the provided evidence.\n"
                    "- Do NOT hallucinate.\n"
                    "- If evidence is missing or unclear, prefer 'partial' or 'none' over 'full'.\n"
                    "- 'full' = clear and explicit support for the metric.\n"
                    "- 'partial' = indirect, related, or implied support.\n"
                    "- 'none' = no support or unrelated.\n\n"
                    "Return JSON only with your validation decision."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"TOPIC: {topic}\n\n"
                    f"SOURCE:\n{source_context}\n\n"
                    f"METRIC: {metric_name}\n"
                    f"{f'DESCRIPTION: {metric_description}' if metric_description else ''}\n\n"
                    f"CURRENT STATUS: {self.STATUS_MAP[current_status]}\n"
                    f"CURRENT EVIDENCE: {current_evidence}\n\n"
                    f"Validate whether the current status is justified. "
                    f"If not, provide the correct status and explain why."
                ),
            },
        ]

        try:
            class ValidationResponse(BaseModel):
                validated_status: Literal["full", "partial", "none"]
                confidence: Literal["high", "medium", "low"]
                evidence: str = Field(description="Short evidence sentence")
                changed: bool = Field(description="True if status changed")
                reason_for_change: Optional[str] = Field(description="Reason if changed, else null")

            response = self.llm.chat_json(
                messages=messages,
                response_model=ValidationResponse,
                temperature=0.2,
            )

            # Track LLM call
            if self.tracker and self.llm.last_call_metadata:
                usage = self.llm.last_call_metadata["usage"]
                self.tracker.add_llm_call(
                    prompt_tokens=usage["prompt_tokens"],
                    completion_tokens=usage["completion_tokens"]
                )

            if response.changed:
                return (
                    response.validated_status,
                    response.confidence,
                    response.evidence,
                    response.reason_for_change or "LLM determined status should change.",
                )
            else:
                # No change, but update evidence/confidence if provided
                return (
                    current_status,
                    response.confidence,
                    response.evidence,
                    "Validation confirmed original status.",
                )

        except Exception as e:
            # LLM validation failed, return None to keep original
            return None

    def _build_source_context(self, source: ScoredSourceItem) -> str:
        """Build context string for a source."""
        context_parts = [
            f"Title: {source.title}",
            f"Type: {source.source_type.value}",
        ]

        if source.author_or_assignee:
            label = "Assignee" if source.source_type.value == "patent" else "Authors"
            context_parts.append(f"{label}: {source.author_or_assignee}")

        if source.publication_date:
            context_parts.append(f"Publication Date: {source.publication_date}")

        if source.relevance_explanation:
            context_parts.append(f"Relevance Analysis: {source.relevance_explanation}")

        if source.venue:
            context_parts.append(f"Venue: {source.venue}")

        if source.doi:
            context_parts.append(f"DOI: {source.doi}")

        if source.patent_number:
            context_parts.append(f"Patent Number: {source.patent_number}")

        if source.is_open_access:
            context_parts.append("Open Access: Yes")

        if source.pdf_url:
            context_parts.append(f"PDF URL: {source.pdf_url}")

        return "\n".join(context_parts)

    def _generate_source_id(self, source: ScoredSourceItem) -> str:
        """Generate a unique ID for a source."""
        if source.doi:
            return source.doi
        if source.patent_number:
            return source.patent_number
        return source.title[:50].replace(" ", "_")

    def _get_source_label(self, source: ScoredSourceItem) -> str:
        """Get a human-readable label for a source."""
        if source.source_type.value == "patent":
            return f"Patent ({source.patent_number or source.title[:30]})"
        else:
            return f"Paper ({source.title[:30]})"

    def _status_to_symbol(self, status: Literal["full", "partial", "none"]) -> Literal["✅", "⚠️", "❌"]:
        """Convert status to symbol."""
        if status == "full":
            return "✅"
        elif status == "partial":
            return "⚠️"
        else:
            return "❌"

    def _status_to_score(self, status: Literal["full", "partial", "none"]) -> float:
        """Convert status to score."""
        if status == "full":
            return 1.0
        elif status == "partial":
            return 0.5
        else:
            return 0.0

    def _confidence_to_score(self, confidence: Literal["high", "medium", "low"]) -> float:
        """Convert confidence to numeric score."""
        if confidence == "high":
            return 1.0
        elif confidence == "medium":
            return 0.7
        else:
            return 0.4

    def _build_validation_summary(
        self,
        cells_reviewed: int,
        cells_changed: int,
        changes: list[ValidationChange],
    ) -> str:
        """Build validation summary text."""
        summary = f"Validation reviewed {cells_reviewed} matrix cells. "

        if cells_changed == 0:
            summary += "All evaluations were confirmed as accurate."
        else:
            summary += f"{cells_changed} cells were corrected:\n"
            for i, change in enumerate(changes[:5], 1):  # Show top 5 changes
                summary += f"\n{i}. {change.source_label} / {change.metric}: {change.old_status} → {change.new_status}"
                summary += f"\n   Reason: {change.reason}"

            if len(changes) > 5:
                summary += f"\n... and {len(changes) - 5} more changes."

        return summary
