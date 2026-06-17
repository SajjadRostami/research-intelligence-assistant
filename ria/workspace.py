"""
Workspace persistence for managing research artifacts and history.

The WorkspaceManager creates and manages local workspace directories for
research topics, handling JSON serialization of orchestrator results,
ranked results, and other artifacts throughout the research pipeline.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ria.models import HistoryEntry, OrchestratorResult


class WorkspaceManager:
    """
    Manages workspace directories and artifact persistence.

    Each research topic gets its own workspace directory with a safe
    slug-based name. The manager handles saving/loading JSON artifacts,
    tracking history, and organizing results.

    Example:
        manager = WorkspaceManager(base_dir="./workspaces")
        workspace = manager.create("XPBD simulation")
        manager.save_orchestrator_result(workspace, orchestrator_result)
        result = manager.load_orchestrator_result(workspace)
    """

    def __init__(self, base_dir: str | Path = "./workspaces"):
        """
        Initialize the workspace manager.

        Args:
            base_dir: Base directory for all workspaces (default: ./workspaces)
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _make_slug(self, topic: str) -> str:
        """
        Convert a topic string into a safe directory name slug.

        Args:
            topic: Research topic string

        Returns:
            Safe slug suitable for directory names

        Example:
            "XPBD Simulation & Physics" -> "xpbd-simulation-physics"
        """
        # Convert to lowercase
        slug = topic.lower()
        # Replace spaces and special characters with hyphens
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        # Limit length to 100 characters
        return slug[:100]

    def create(self, topic: str) -> Path:
        """
        Create a workspace directory for a research topic.

        If the workspace already exists, returns the existing path.
        Creates the directory structure and initializes metadata.

        Args:
            topic: Research topic string

        Returns:
            Path to the workspace directory

        Example:
            workspace = manager.create("XPBD simulation")
            # Returns: Path("./workspaces/xpbd-simulation")
        """
        slug = self._make_slug(topic)
        workspace_path = self.base_dir / slug
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Save topic metadata if it doesn't exist
        metadata_path = workspace_path / "metadata.json"
        if not metadata_path.exists():
            metadata = {
                "topic": topic,
                "slug": slug,
                "created_at": datetime.utcnow().isoformat(),
                "last_updated": datetime.utcnow().isoformat(),
            }
            self._save_json(metadata_path, metadata)

        return workspace_path

    def _save_json(self, file_path: Path, data: dict[str, Any] | list[Any]) -> None:
        """
        Save data to a JSON file with pretty formatting.

        Args:
            file_path: Path to the JSON file
            data: Data to serialize to JSON
        """
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _load_json(self, file_path: Path) -> dict[str, Any] | list[Any]:
        """
        Load data from a JSON file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Deserialized JSON data

        Raises:
            FileNotFoundError: If the file doesn't exist
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_orchestrator_result(
        self,
        workspace: Path,
        result: OrchestratorResult,
    ) -> Path:
        """
        Save orchestrator results to the workspace.

        Saves the result using Pydantic's model_dump() for serialization
        and updates the workspace metadata timestamp.

        Args:
            workspace: Workspace directory path
            result: OrchestratorResult to save

        Returns:
            Path to the saved JSON file
        """
        result_path = workspace / "orchestrator_result.json"
        result_data = result.model_dump(mode='json')
        self._save_json(result_path, result_data)

        # Update metadata timestamp
        self._update_metadata_timestamp(workspace)

        return result_path

    def load_orchestrator_result(self, workspace: Path) -> OrchestratorResult:
        """
        Load orchestrator results from the workspace.

        Args:
            workspace: Workspace directory path

        Returns:
            OrchestratorResult loaded from JSON

        Raises:
            FileNotFoundError: If the orchestrator result file doesn't exist
        """
        result_path = workspace / "orchestrator_result.json"
        data = self._load_json(result_path)
        return OrchestratorResult.model_validate(data)

    def save_artifact(
        self,
        workspace: Path,
        artifact_name: str,
        data: dict[str, Any] | list[Any],
    ) -> Path:
        """
        Save an arbitrary JSON artifact to the workspace.

        Generic method for saving any JSON-serializable data.

        Args:
            workspace: Workspace directory path
            artifact_name: Name for the artifact file (should end with .json)
            data: Data to save

        Returns:
            Path to the saved artifact file
        """
        if not artifact_name.endswith('.json'):
            artifact_name += '.json'

        artifact_path = workspace / artifact_name
        self._save_json(artifact_path, data)

        # Update metadata timestamp
        self._update_metadata_timestamp(workspace)

        return artifact_path

    def load_artifact(
        self,
        workspace: Path,
        artifact_name: str,
    ) -> dict[str, Any] | list[Any]:
        """
        Load an arbitrary JSON artifact from the workspace.

        Args:
            workspace: Workspace directory path
            artifact_name: Name of the artifact file

        Returns:
            Deserialized artifact data

        Raises:
            FileNotFoundError: If the artifact doesn't exist
        """
        if not artifact_name.endswith('.json'):
            artifact_name += '.json'

        artifact_path = workspace / artifact_name
        return self._load_json(artifact_path)

    def _update_metadata_timestamp(self, workspace: Path) -> None:
        """
        Update the last_updated timestamp in workspace metadata.

        Args:
            workspace: Workspace directory path
        """
        metadata_path = workspace / "metadata.json"
        if metadata_path.exists():
            metadata = self._load_json(metadata_path)
            metadata["last_updated"] = datetime.utcnow().isoformat()
            self._save_json(metadata_path, metadata)

    def update_history(self, workspace: Path, **kwargs: Any) -> None:
        """
        Update workspace history with additional metadata.

        Allows updating workspace metadata with arbitrary key-value pairs
        such as report_version, paper_count, patent_count, etc.

        Args:
            workspace: Workspace directory path
            **kwargs: Key-value pairs to update in metadata
        """
        metadata_path = workspace / "metadata.json"
        if metadata_path.exists():
            metadata = self._load_json(metadata_path)
            metadata.update(kwargs)
            metadata["last_updated"] = datetime.utcnow().isoformat()
            self._save_json(metadata_path, metadata)

    def list_history(self) -> list[HistoryEntry]:
        """
        List all workspace history entries.

        Scans all workspace directories and returns history entries
        sorted by last_updated timestamp (most recent first).

        Returns:
            List of HistoryEntry objects for all workspaces
        """
        history_entries: list[HistoryEntry] = []

        # Scan all workspace directories
        for workspace_dir in self.base_dir.iterdir():
            if not workspace_dir.is_dir():
                continue

            metadata_path = workspace_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            try:
                metadata = self._load_json(metadata_path)

                # Build HistoryEntry from metadata
                entry = HistoryEntry(
                    topic=metadata.get("topic", "Unknown"),
                    creation_date=datetime.fromisoformat(metadata["created_at"]),
                    last_updated=datetime.fromisoformat(metadata["last_updated"]),
                    report_version=metadata.get("report_version", 1),
                    paper_count=metadata.get("paper_count", 0),
                    patent_count=metadata.get("patent_count", 0),
                    report_file_path=metadata.get("report_file_path", ""),
                    workspace_dir=str(workspace_dir),
                )
                history_entries.append(entry)

            except (KeyError, ValueError) as e:
                # Skip malformed metadata files
                continue

        # Sort by last_updated (most recent first)
        history_entries.sort(key=lambda e: e.last_updated, reverse=True)

        return history_entries

    def get_workspace_by_topic(self, topic: str) -> Path | None:
        """
        Get workspace path for a topic if it exists.

        Args:
            topic: Research topic string

        Returns:
            Workspace path if it exists, None otherwise
        """
        slug = self._make_slug(topic)
        workspace_path = self.base_dir / slug
        return workspace_path if workspace_path.exists() else None

    def workspace_exists(self, topic: str) -> bool:
        """
        Check if a workspace exists for a topic.

        Args:
            topic: Research topic string

        Returns:
            True if workspace exists, False otherwise
        """
        return self.get_workspace_by_topic(topic) is not None
