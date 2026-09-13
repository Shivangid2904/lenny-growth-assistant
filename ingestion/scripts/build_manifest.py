import json
import os
import yaml
from pathlib import Path

REPO_URL = "https://github.com/ChatPRD/lennys-podcast-transcripts"
COMMIT_HASH = "be8ab89a890a833cbba2c892178f823fff178c65"

SELECTED_EPISODES = [
    {
        "slug": "brian-balfour",
        "primary_topics": ["product-market fit", "retention", "growth loops", "acquisition"],
        "rationale": "Foundational insights on cohort retention curves, four growth fits, and why retention is the foundation of growth loops.",
    },
    {
        "slug": "casey-winters",
        "primary_topics": ["growth loops", "retention", "scaling", "funnels"],
        "rationale": "Core conceptual framework contrasting compounding growth loops with linear acquisition funnels, retention mechanics, and loop design.",
    },
    {
        "slug": "elena-verna",
        "primary_topics": ["product-led growth", "b2b growth", "product-led sales", "monetization"],
        "rationale": "Deep dive into B2B PLG, self-serve acquisition, enterprise sales overlays, and how to structure product-led growth engines.",
    },
    {
        "slug": "adam-fishman",
        "primary_topics": ["onboarding", "growth teams", "activation", "hiring"],
        "rationale": "Tactical frameworks on user onboarding, delivering the core product promise, and structuring high-performing growth teams.",
    },
    {
        "slug": "april-dunford",
        "primary_topics": ["positioning", "product-market fit", "b2b sales", "market category"],
        "rationale": "Authoritative strategy for product positioning, competitive alternatives, differentiated value, and target customer segmentation.",
    },
    {
        "slug": "madhavan-ramanujam",
        "primary_topics": ["pricing", "monetization", "packaging", "willingness to pay"],
        "rationale": "Essential principles for monetization, willingness-to-pay conversations before building features, and packaging architecture.",
    },
    {
        "slug": "shreyas-doshi",
        "primary_topics": ["product management", "product strategy", "execution", "prioritization"],
        "rationale": "High-impact frameworks on LNO (Leverage, Neutral, Overhead), product strategy clarity, and avoiding execution traps.",
    },
    {
        "slug": "bob-moesta",
        "primary_topics": ["jobs to be done", "customer demand", "user research", "product innovation"],
        "rationale": "Jobs to Be Done (JTBD) theory, forces of progress, customer purchase triggers, and understanding the real struggle behind user adoption.",
    },
    {
        "slug": "gibson-biddle",
        "primary_topics": ["product strategy", "dhm model", "branding", "metrics"],
        "rationale": "The Delight, Hard-to-copy, Margin-enhancing (DHM) product strategy framework, proxy metrics, and strategy formulation at scale.",
    },
    {
        "slug": "gustaf-alstromer",
        "primary_topics": ["product-market fit", "startups", "early-stage growth", "retention"],
        "rationale": "Y Combinator partner perspective on identifying early PMF, measuring retention benchmarks, and startup growth trajectories.",
    },
    {
        "slug": "hila-qu",
        "primary_topics": ["product-led growth", "growth loops", "metrics", "experimentation"],
        "rationale": "Advanced PLG playbooks, product growth models, quantitative activation metrics, and driving self-serve conversion.",
    },
    {
        "slug": "nikhyl-singhal",
        "primary_topics": ["product leadership", "career growth", "organizational design", "executive"],
        "rationale": "Comprehensive guidance on transitioning from product manager to VP of Product / CPO, team structures, and leadership dynamics.",
    },
    {
        "slug": "bangaly-kaba",
        "primary_topics": ["activation", "adjacent user theory", "onboarding", "growth metrics"],
        "rationale": "The Adjacent User Theory (AUT) for expanding market reach and breaking through activation plateaus beyond early adopters.",
    },
    {
        "slug": "andy-johns",
        "primary_topics": ["growth strategy", "network effects", "distribution", "psychology"],
        "rationale": "Historical perspective on scaling Facebook, Twitter, and Quora; growth loops, distribution power, and sustainable product momentum.",
    },
    {
        "slug": "ronny-kohavi",
        "primary_topics": ["experimentation", "a/b testing", "growth metrics", "twyman's law"],
        "rationale": "The definitive guide to trustworthy online controlled experiments, A/B testing pitfalls, metric selection, and statistical rigor.",
    },
]

def build_manifest():
    base_dir = Path(__file__).resolve().parent.parent
    raw_episodes_dir = base_dir / "data" / "raw_repo" / "episodes"
    manifest_out = base_dir / "data" / "corpus_manifest.json"

    manifest_episodes = []

    for item in SELECTED_EPISODES:
        slug = item["slug"]
        tfile = raw_episodes_dir / slug / "transcript.md"
        if not tfile.exists():
            raise FileNotFoundError(f"Transcript file not found: {tfile}")

        with open(tfile, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        frontmatter = {}
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}

        guest_name = frontmatter.get("guest") or slug.replace("-", " ").title()
        title = frontmatter.get("title") or f"{guest_name} on Lenny's Podcast"
        youtube_url = frontmatter.get("youtube_url") or ""
        publish_date = str(frontmatter.get("publish_date") or "")
        description = frontmatter.get("description", "").strip()
        duration = frontmatter.get("duration", "")
        keywords = frontmatter.get("keywords", [])

        # Count words / lines
        body_text = parts[2] if len(parts) >= 3 else content
        word_count = len(body_text.split())

        entry = {
            "episode_id": slug,
            "episode_title": title,
            "guest_name": guest_name,
            "source_repo_url": REPO_URL,
            "source_repo_commit": COMMIT_HASH,
            "source_path": f"episodes/{slug}/transcript.md",
            "source_url": youtube_url,
            "publish_date": publish_date,
            "duration": duration,
            "word_count": word_count,
            "primary_topics": item["primary_topics"],
            "keywords": keywords,
            "rationale": item["rationale"],
            "status": "ready_for_ingestion",
        }
        manifest_episodes.append(entry)

    manifest_data = {
        "metadata": {
            "source_repository": REPO_URL,
            "source_commit_hash": COMMIT_HASH,
            "total_episodes": len(manifest_episodes),
            "selection_strategy": "15 representative episodes covering all core product and growth competencies",
            "git_policy": "Raw transcript files are strictly excluded via .gitignore; only this manifest, metadata, and evaluation datasets are tracked.",
        },
        "episodes": manifest_episodes,
    }

    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print(f"[+] Successfully generated manifest with {len(manifest_episodes)} episodes at {manifest_out}")


if __name__ == "__main__":
    build_manifest()
