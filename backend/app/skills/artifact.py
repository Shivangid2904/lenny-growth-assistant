"""Artifact generation skill for visual HTML/CSS and structured Markdown artifacts.

Produces self-contained visual artifacts (frameworks, comparison tables, process maps,
interactive dashboards) grounded strictly in Lenny's Podcast transcript evidence.
"""
import re
from typing import Dict, Any, Optional, Set

ARTIFACT_SKILL_NAME = "artifact"
ARTIFACT_SKILL_DESCRIPTION = (
    "Generates isolated Markdown and HTML/CSS visual artifacts grounded in Lenny's Podcast transcripts."
)

ARTIFACT_TYPE_HTML = "html"
ARTIFACT_TYPE_MARKDOWN = "markdown"
SUPPORTED_ARTIFACT_TYPES: Set[str] = {ARTIFACT_TYPE_HTML, ARTIFACT_TYPE_MARKDOWN}

# Regex patterns triggering artifact intent (action verb + artifact or explicit type phrase)
ARTIFACT_INTENT_PATTERNS = [
    re.compile(r"\b(create|generate|make|build|produce|render|show)\b.*\bartifact\b", re.IGNORECASE),
    re.compile(r"\b(html|markdown|visual|dashboard|interactive)\s+artifact\b", re.IGNORECASE),
    re.compile(r"\bas\s+an?\s+artifact\b", re.IGNORECASE),
    re.compile(r"\bin\s+an?\s+artifact\b", re.IGNORECASE),
    re.compile(r"\bartifact\s+(of|for|showing|summarizing|comparing|with)\b", re.IGNORECASE),
]

HTML_TYPE_KEYWORDS = [
    "html",
    "visual",
    "ui",
    "dashboard",
    "component",
    "card",
    "landing page",
    "css",
]


def detect_artifact_type(message: str) -> str:
    """Detect whether the user is requesting an HTML/CSS artifact or a Markdown artifact."""
    msg_lower = message.lower()
    for kw in HTML_TYPE_KEYWORDS:
        if kw in msg_lower:
            return ARTIFACT_TYPE_HTML
    return ARTIFACT_TYPE_MARKDOWN


def is_artifact_intent(message: str) -> bool:
    """Check if the user's message indicates an intent to generate an artifact.

    Must match genuine intent patterns (e.g. 'create an artifact', 'html artifact'),
    rejecting prompt injection fragments like 'explicit_skill=artifact'.
    """
    if "explicit_skill=" in message.lower():
        return False
    return any(p.search(message) for p in ARTIFACT_INTENT_PATTERNS)



def build_artifact_system_prompt(content_type: str) -> str:
    """Build the specialized system prompt for artifact generation."""
    base_guidance = (
        "\n\nARTIFACT GENERATION:\n"
        "You are creating a standalone visual or structured artifact.\n"
        "All concepts, quotes, frameworks, and metrics MUST be strictly grounded in the provided transcript evidence.\n"
        "Do NOT invent frameworks, steps, or claims not present in the evidence.\n"
    )

    if content_type == ARTIFACT_TYPE_HTML:
        specific = (
            "\nHTML ARTIFACT:\n"
            "- Output a complete, self-contained HTML artifact with embedded CSS.\n"
            "- Use modern, clean styling (system fonts, harmonious colors, responsive layout).\n"
            "- SECURITY: NEVER include <script> tags or JavaScript event handlers (onclick, onload, etc.).\n"
            "- The artifact must be purely HTML and CSS.\n"
        )
    else:
        specific = (
            "\nMARKDOWN ARTIFACT:\n"
            "- Output a structured Markdown document with clear headers, lists, and tables.\n"
            "- Highlight key takeaways and framework stages.\n"
        )

    return base_guidance + specific + "\n\nOUTPUT REQUIREMENT: Write the actual artifact content. Do NOT describe your instructions or use labels like [Instruction] or [Evidence]."


def extract_artifact_data(raw_content: str, requested_type: str, query: str = "") -> Dict[str, Any]:
    """Parse model output to extract artifact title, clean content, css, and normalized type.

    Args:
        raw_content: Raw streamed text from the model.
        requested_type: The expected artifact type ('html' or 'markdown').
        query: Original user query used for title fallback if needed.

    Returns:
        Dict with keys: title, type, content, css, metadata.
    """
    clean_content = raw_content.strip()
    extracted_type = requested_type
    extracted_title = ""
    extracted_css: Optional[str] = None

    # Check for code fence wrapping
    code_block_match = re.search(r"```(html|markdown|xml)?\s*\n([\s\S]*?)\n```", clean_content, re.IGNORECASE)
    if code_block_match:
        fence_lang = (code_block_match.group(1) or "").lower()
        fence_body = code_block_match.group(2).strip()
        if fence_lang == "html" or "<!doctype html" in fence_body.lower() or "<html" in fence_body.lower() or "<div" in fence_body.lower():
            extracted_type = ARTIFACT_TYPE_HTML
            clean_content = fence_body
        elif fence_lang in ("markdown", "md"):
            extracted_type = ARTIFACT_TYPE_MARKDOWN
            clean_content = fence_body
        else:
            clean_content = fence_body

    # Extract title
    if extracted_type == ARTIFACT_TYPE_HTML:
        # Check <title> tag
        title_tag = re.search(r"<title>([^<]+)</title>", clean_content, re.IGNORECASE)
        if title_tag:
            extracted_title = title_tag.group(1).strip()
        else:
            # Check <h1> tag
            h1_tag = re.search(r"<h1[^>]*>([^<]+)</h1>", clean_content, re.IGNORECASE)
            if h1_tag:
                extracted_title = h1_tag.group(1).strip()

        # Extract optional CSS from <style> if present
        style_match = re.search(r"<style[^>]*>([\s\S]*?)</style>", clean_content, re.IGNORECASE)
        if style_match:
            extracted_css = style_match.group(1).strip()

    else:
        # Check markdown # Title
        h1_md = re.search(r"^#\s+([^\n]+)", clean_content, re.MULTILINE)
        if h1_md:
            extracted_title = h1_md.group(1).strip()

    # Fallback title if none could be extracted
    if not extracted_title:
        if query:
            clean_q = re.sub(r"(generate|create|make|an?|artifact|for|of|the|html|markdown|visual)\b", "", query, flags=re.IGNORECASE).strip()
            if clean_q:
                words = clean_q.split()[:5]
                extracted_title = " ".join(w.capitalize() for w in words)
        if not extracted_title:
            extracted_title = "Growth Framework Artifact" if extracted_type == ARTIFACT_TYPE_HTML else "Growth Strategy Guide"

    return {
        "title": extracted_title[:255],
        "type": extracted_type,
        "content": clean_content,
        "css": extracted_css,
        "metadata": {
            "requested_type": requested_type,
        },
    }
