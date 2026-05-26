"""
Badge generation for repo health scores.
Generates SVG badges matching Shields.io style.
"""

import html
import re
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/badge", tags=["badge"])

# Badge colors by letter grade
LETTER_COLORS = {
    "A": "#4c1",
    "B": "#9c6",
    "C": "#dfb317",
    "D": "#d9730d",
    "F": "#e05c44",
}

# Brightness mapping for text (white on dark colors)
LETTER_TEXT_COLORS = {
    "A": "#fff",
    "B": "#fff",
    "C": "#333",
    "D": "#fff",
    "F": "#fff",
}


def generate_badge_svg(letter: str, score: float, owner: str, repo: str) -> str:
    """Generate a Shields.io-style SVG badge."""
    color = LETTER_COLORS.get(letter, "#9c6")
    text_color = LETTER_TEXT_COLORS.get(letter, "#fff")

    # Sanitize all user-controlled text before embedding in SVG
    safe_owner = _sanitize_svg_text(owner)
    safe_repo = _sanitize_svg_text(repo)
    label = f"{safe_owner}/{safe_repo}"
    grade_text = _sanitize_svg_text(letter)
    score_text = f"{score:.0f}"

    # Approximate text widths for sizing
    # Using monospace-ish approximations
    label_width = len(label) * 6.2 + 20
    grade_width = 22
    score_width = len(score_text) * 7.5 + 14

    # Colors bar: left (grade) + right (score)
    grade_bar_width = grade_width + 16
    score_bar_width = score_width + 16

    total_width = label_width + grade_bar_width + score_bar_width + 4
    height = 20

    # Calculate x positions
    label_x = 10
    grade_bar_x = label_width + 2
    grade_text_x = grade_bar_x + grade_width // 2 + 2
    score_bar_x = grade_bar_x + grade_bar_width
    score_text_x = score_bar_x + score_width // 2 + 2

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="{height}" role="img" aria-label="{label} health score">
  <linearGradient id="grad" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#242424"/>
    <stop offset="{label_width / total_width * 100}%" stop-color="#242424"/>
    <stop offset="{label_width / total_width * 100}%" stop-color="{color}"/>
    <stop offset="100%" stop-color="{color}"/>
  </linearGradient>
  <rect width="{total_width}" height="{height}" fill="url(#grad)" rx="3"/>
  <rect x="{grade_bar_x}" width="{grade_bar_width}" height="{height}" fill="{color}" opacity="0.5"/>
  <text x="{label_x}" y="14" fill="#fff" font-family="monospace" font-size="11" font-weight="bold">{label}</text>
  <text x="{grade_text_x}" y="14" fill="{text_color}" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">{grade_text}</text>
  <text x="{score_text_x}" y="14" fill="{text_color}" font-family="monospace" font-size="11" font-weight="bold" text-anchor="middle">{score_text}</text>
</svg>'''

    return svg


_OWNER_REPO_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def _sanitize_svg_text(value: str) -> str:
    """
    Sanitize user input for safe embedding in SVG text elements.
    Escapes < > & " ' to prevent SVG-injected content and XSS.
    """
    return html.escape(value, quote=True)


@router.get("/{owner}/{repo}.svg")
def get_badge(
    owner: str,
    repo: str,
    score: float = Query(..., description="The numeric health score (0-100)"),
    letter: str = Query(..., description="The letter grade (A-F)"),
):
    """
    Generate an SVG badge for a repo's health score.

    Example: /badge/owner/repo.svg?score=87&letter=B
    """
    # Validate inputs
    if not 0 <= score <= 100:
        raise HTTPException(status_code=400, detail="Score must be between 0 and 100")
    if letter not in LETTER_COLORS:
        raise HTTPException(status_code=400, detail="Letter must be A, B, C, D, or F")
    if not _OWNER_REPO_RE.match(owner) or not _OWNER_REPO_RE.match(repo):
        raise HTTPException(
            status_code=400,
            detail="owner and repo must contain only alphanumeric characters, hyphens, underscores, and periods."
        )
    if len(owner) > 100 or len(repo) > 100:
        raise HTTPException(status_code=400, detail="owner and repo must be 100 characters or fewer.")

    svg = generate_badge_svg(letter, score, owner, repo)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        }
    )