"""Application services for Pferdehof workflows."""

from .candidate_generator import generate_candidate_horses
from .onboarding import (
	StartOnboardingResult,
	ViewCandidatesResult,
	start_onboarding_flow,
	view_candidates_flow,
)

__all__ = [
	"generate_candidate_horses",
	"StartOnboardingResult",
	"ViewCandidatesResult",
	"start_onboarding_flow",
	"view_candidates_flow",
]
