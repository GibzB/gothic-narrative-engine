"""
Request Router for Skill Triage.

Classifies user requests into one of five intents:
- USE: Apply an existing skill
- IMPROVE: Enhance/refine an existing skill
- CREATE: Build a new skill from scratch
- COMPOSE: Combine multiple skills
- CLARIFY: Need more information before proceeding

Adapted from tripleyak/SkillForge triage_skill_request.py patterns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TriageIntent(Enum):
    """Classification of skill request intent."""

    USE = "USE"
    IMPROVE = "IMPROVE"
    CREATE = "CREATE"
    COMPOSE = "COMPOSE"
    CLARIFY = "CLARIFY"

    def __str__(self) -> str:
        return self.value


@dataclass
class TriageResult:
    """Result of triaging a skill request."""

    intent: TriageIntent
    confidence: float = 1.0
    matched_skill: str | None = None
    matched_skills: list[str] = field(default_factory=list)
    reasoning: str = ""
    suggested_questions: list[str] = field(default_factory=list)


# Intent detection patterns
INTENT_PATTERNS: dict[TriageIntent, list[re.Pattern[str]]] = {
    TriageIntent.USE: [
        re.compile(r"\b(use|apply|run|execute|invoke)\b.*\bskill\b", re.IGNORECASE),
        re.compile(r"\busing\b.*\bskill\b", re.IGNORECASE),
    ],
    TriageIntent.IMPROVE: [
        re.compile(r"\b(improve|enhance|refine|update|fix|modify)\b.*\bskill\b", re.IGNORECASE),
        re.compile(r"\bimproving\b.*\bskill\b", re.IGNORECASE),
    ],
    TriageIntent.CREATE: [
        re.compile(r"\b(create|build|make|new|generate)\b.*\bskill\b", re.IGNORECASE),
        re.compile(r"\bcreating\b.*\bskill\b", re.IGNORECASE),
        re.compile(r"\bnew\b.*\bskill\b", re.IGNORECASE),
    ],
    TriageIntent.COMPOSE: [
        re.compile(r"\b(combine|compose|merge|chain|link)\b.*\bskills?\b", re.IGNORECASE),
        re.compile(r"\bcomposing\b.*\bskills?\b", re.IGNORECASE),
    ],
    TriageIntent.CLARIFY: [
        re.compile(r"\b(what|how|why|when|which|explain|help|clarify)\b", re.IGNORECASE),
        re.compile(r"\?", re.IGNORECASE),
    ],
}

# Skill name extraction patterns
SKILL_NAME_PATTERNS = [
    re.compile(r"\bskill[:\s]+['\"]?([a-zA-Z0-9_-]+)['\"]?", re.IGNORECASE),
    re.compile(r"\b([a-zA-Z0-9_-]+)\s+skill\b", re.IGNORECASE),
    re.compile(r"\bthe\s+([a-zA-Z0-9_-]+)\b", re.IGNORECASE),
    re.compile(r"\b([a-zA-Z0-9_-]+)\b", re.IGNORECASE),
]


class TriageRouter:
    """
    Routes skill requests to appropriate intent handlers.

    The router analyzes natural language requests and classifies them
    into one of five intents, optionally extracting referenced skill names.

    Example:
        >>> router = TriageRouter()
        >>> result = router.triage("Use the aws-audit skill")
        >>> result.intent
        <TriageIntent.USE: 'USE'>
        >>> result.matched_skill
        'aws-audit'
    """

    def __init__(
        self,
        *,
        available_skills: list[str] | None = None,
        confidence_threshold: float = 0.6,
    ) -> None:
        """
        Initialize the triage router.

        Args:
            available_skills: List of known skill names for matching
            confidence_threshold: Minimum confidence for intent classification
        """
        self.available_skills = set(available_skills or [])
        self.confidence_threshold = confidence_threshold

    def triage(self, request: str) -> TriageResult:
        """
        Classify a skill request into an intent.

        Args:
            request: Natural language skill request

        Returns:
            TriageResult with classified intent and metadata
        """
        # Score each intent
        scores: dict[TriageIntent, float] = {
            intent: self._score_intent(request, patterns)
            for intent, patterns in INTENT_PATTERNS.items()
        }

        # Find best intent
        best_intent = max(scores, key=lambda i: scores[i])
        confidence = scores[best_intent]

        # Extract referenced skills
        matched_skills = self._extract_skill_names(request)

        # Build reasoning
        reasoning = self._build_reasoning(best_intent, confidence, matched_skills)

        # Generate clarification questions if needed
        suggested_questions = (
            self._generate_questions(best_intent, matched_skills)
            if confidence < self.confidence_threshold or best_intent == TriageIntent.CLARIFY
            else []
        )

        return TriageResult(
            intent=best_intent,
            confidence=confidence,
            matched_skill=matched_skills[0] if matched_skills else None,
            matched_skills=matched_skills,
            reasoning=reasoning,
            suggested_questions=suggested_questions,
        )

    def _score_intent(self, request: str, patterns: list[re.Pattern[str]]) -> float:
        """Score how well the request matches an intent."""
        matches = sum(1 for pattern in patterns if pattern.search(request))
        return min(1.0, matches * 0.5 + 0.1) if matches > 0 else 0.0

    def _extract_skill_names(self, request: str) -> list[str]:
        """Extract skill names referenced in the request."""
        found: list[str] = []

        for pattern in SKILL_NAME_PATTERNS:
            for match in pattern.finditer(request):
                name = match.group(1).lower()
                # Skip common non-skill words
                if name in ('the', 'a', 'an', 'new', 'existing'):
                    continue
                if name in self.available_skills or not self.available_skills:
                    found.append(name)

        # Dedupe while preserving order
        seen = set()
        return [s for s in found if not (s in seen or seen.add(s))]

    def _build_reasoning(
        self, intent: TriageIntent, confidence: float, matched_skills: list[str]
    ) -> str:
        """Build human-readable reasoning for the classification."""
        skill_str = f" referencing skill(s): {', '.join(matched_skills)}" if matched_skills else ""
        return f"Classified as {intent.value} with {confidence:.0%} confidence{skill_str}"

    def _generate_questions(
        self, intent: TriageIntent, matched_skills: list[str]
    ) -> list[str]:
        """Generate clarifying questions for low-confidence classifications."""
        questions: list[str] = []

        if not matched_skills and intent in (TriageIntent.USE, TriageIntent.IMPROVE):
            questions.append("Which skill would you like to work with?")

        if intent == TriageIntent.CREATE:
            questions.append("What should the new skill do?")
            questions.append("What triggers or parameters should it accept?")

        if intent == TriageIntent.COMPOSE:
            questions.append("Which skills would you like to combine?")

        return questions

    def register_skill(self, skill_name: str) -> None:
        """Register a new skill name for matching."""
        self.available_skills.add(skill_name.lower())

    def unregister_skill(self, skill_name: str) -> None:
        """Unregister a skill name."""
        self.available_skills.discard(skill_name.lower())
