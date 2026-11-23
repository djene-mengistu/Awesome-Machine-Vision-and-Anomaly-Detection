#!/usr/bin/env python3
"""Insert a reviewed GitHub Issue submission into an existing Markdown catalog."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

CATALOGS = {
    "Industrial anomaly detection": "industrial-anomaly-detection.md",
    "Defect classification, detection and segmentation": "classification-detection-and-segmentation.md",
    "Semi-supervised and weakly-supervised learning": "semi-supervised-and-weakly-supervised-learning.md",
    "Few-shot and zero-shot learning": "industrial-anomaly-detection.md",
    "Vision-language and foundation models": "industrial-anomaly-detection.md",
    "3D and multimodal inspection": "industrial-anomaly-detection.md",
    "Datasets and benchmarks": "industrial-anomaly-detection.md",
}
LABELS = {
    "paper_title": "Paper title", "paper_url": "Paper URL",
    "year": "Publication year", "category": "Research category",
    "venue": "Journal or conference (optional)",
    "code_url": "Official code repository (optional)",
}


def parse_form(body):
    result = {}
    sections = re.split(r"(?m)^###\s+", body)
    for section in sections[1:]:
        heading, _, value = section.partition("\n")
        result[heading.strip()] = value.strip()
    return {key: result.get(label, "").strip() for key, label in LABELS.items()}


def clean_text(value, field, maxlen=350):
    if not value or value == "_No response_":
        raise ValueError(f"Missing {field}")
    if len(value) > maxlen or "\n" in value or "\r" in value or any(x in value for x in "|[]<>`\\"):
        raise ValueError(f"Invalid Markdown characters or length in {field}")
    return value


def clean_url(value, field):
    value = clean_text(value, field, 1200)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in value):
        raise ValueError(f"{field} must be a plain HTTPS URL")
    if parsed.hostname in {"localhost", "127.0.0.1"}:
        raise ValueError(f"Invalid {field} hostname")
    return value


def normalize_title(title):
    return re.sub(r"[^a-z0-9]+", "", title.casefold())


def normalize_url(url):
    p = urlsplit(url)
    return (p.hostname or "").lower(), p.path.rstrip("/").lower()


def main():
    issue_path = Path(os.environ.get("ISSUE_JSON", "issue.json"))
    issue = json.loads(issue_path.read_text(encoding="utf-8"))
    if not issue.get("title", "").startswith("[Paper]"):
        raise ValueError("Only [Paper] submission issues can be approved")
    data = parse_form(issue.get("body") or "")
    title = clean_text(data["paper_title"], "paper title")
    paper_url = clean_url(data["paper_url"], "paper URL")
    category = clean_text(data["category"], "category")
    if category not in CATALOGS:
        raise ValueError("Unknown research category")
    year_text = clean_text(data["year"], "publication year", 4)
    if not re.fullmatch(r"\d{4}", year_text):
        raise ValueError("Year must be four digits")
    year = int(year_text)
    if not (1990 <= year <= datetime.now(timezone.utc).year + 1):
        raise ValueError("Year outside accepted range")
    venue = data["venue"]
    venue = clean_text(venue, "venue", 140) if venue and venue != "_No response_" else "Not specified"
    code = data["code_url"]
    code = clean_url(code, "code URL") if code and code != "_No response_" else ""
    root = Path(os.environ.get("REPO_ROOT", "."))
    folder = root / "catalog"
    target = folder / CATALOGS[category]
    if not target.is_file():
        raise ValueError(f"Catalog missing: {target}")
    # Check across all catalogs, not just the selected one.
    for path in folder.glob("*.md"):
        contents = path.read_text(encoding="utf-8")
        for existing_title, existing_url in re.findall(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)", contents):
            if normalize_title(existing_title) == normalize_title(title) or normalize_url(existing_url) == normalize_url(paper_url):
                raise ValueError(f"Possible duplicate found in {path.name}: {existing_title}")
    content = target.read_text(encoding="utf-8")
    row = f"|{year}|[{title}]({paper_url})|{venue}|" + (f"[Code]({code})" if code else "Code not provided") + "|"
    lines = content.splitlines(keepends=True)
    header_index = next((i for i, line in enumerate(lines) if re.match(r"^\|\s*Year\s*\|", line, re.I)), None)
    if header_index is None or header_index + 1 >= len(lines) or not re.match(r"^\|[-:\s|]+\|\s*$", lines[header_index + 1].strip()):
        raise ValueError("Expected Year-first Markdown table not found")
    start = header_index + 2
    end = start
    while end < len(lines) and lines[end].startswith("|"):
        end += 1
    insert_at = end
    for i in range(start, end):
        match = re.match(r"^\|\s*(\d{4})\s*\|", lines[i])
        if match and int(match.group(1)) <= year:
            insert_at = i
            break
    lines.insert(insert_at, row + "\n")
    target.write_text("".join(lines), encoding="utf-8")
    print(f"Added {title} to {target} from issue #{issue.get('number')}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Submission not published: {exc}", file=sys.stderr)
        sys.exit(1)
