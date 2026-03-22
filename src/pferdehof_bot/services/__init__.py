"""Application services for Pferdehof workflows."""

from .candidate_generator import generate_candidate_horses
from .onboarding import (
	ChooseCandidateResult,
	StartOnboardingResult,
	ViewCandidatesResult,
	choose_candidate_flow,
	start_onboarding_flow,
	view_candidates_flow,
)

__all__ = [
	"generate_candidate_horses",
	"ChooseCandidateResult",
	"StartOnboardingResult",
	"ViewCandidatesResult",
	"choose_candidate_flow",
	"start_onboarding_flow",
	"view_candidates_flow",
]
