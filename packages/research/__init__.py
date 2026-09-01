"""
Research Module for Heyaaashu Studio.
"""

from packages.research.collector import ResearchCandidate
from packages.research.dedup_rank import collect_and_rank_candidates

__all__ = ["ResearchCandidate", "collect_and_rank_candidates"]
