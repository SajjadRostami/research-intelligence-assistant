"""
Agents module for Research Intelligence Assistant.

Contains specialized agents for validating and processing research outputs.
"""

from ria.agents.comparison_agent import ComparisonAgent
from ria.agents.metric_bank_agent import MetricBankAgent

__all__ = ["ComparisonAgent", "MetricBankAgent"]
