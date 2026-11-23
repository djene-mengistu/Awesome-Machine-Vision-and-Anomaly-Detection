
#!/usr/bin/env python3
"""Automatically update README paper counts from the research catalogs."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CATALOG = ROOT / "catalog"

TRACKS = {
    "industrial-anomaly-detection.md": "Industrial Anomaly Detection",
    "classification-detection-and-segmentation.md": "Classification, Detection & Segmentation",
    "semi-supervised-and-weakly-supervised-learning.md": "Semi-supervised & Weakly-supervised Learning",
}

MARKER = "<!-- PAPER_COUNT_AUTO -->"


def count_rows(path):
    """Count paper entries in a Year-first Markdown table."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    headers = [
        i for i, line in enumerate(lines)
        if re.match(r"^\|\s*Year\s*\|", line, re.I)
    ]

    if len(headers) != 1:
        raise ValueError(
            f"Expected exactly one Year-first table in {path}"
        )

    header_index = headers[0]
    separator_index = header_index + 1

    if separator_index >= len(lines):
        raise ValueError(f"Missing table separator in {path}")

    separator = lines[separator_index]

    if not re.fullmatch(r"\|[\s:|\-]+\|", separator):
        raise ValueError(f"Invalid table separator in {path}")

    count = 0

    for i in range(separator_index + 1, len(lines)):
        line = lines[i]

        if not line.startswith("|"):
            break

        if not re.match(r"^\|\s*\d{4}\s*\|", line):
            raise ValueError(
                f"Invalid paper year in {path}, line {i + 1}"
            )

        count += 1

    return count


def update_readme():
    """Recalculate category counts and update the README."""
    counts = {
        filename: count_rows(CATALOG / filename)
        for filename in TRACKS
    }

    total = sum(counts.values())

    # Read UTF-8 safely, including files with a BOM.
    original = README.read_text(encoding="utf-8-sig")
    text = original

    # Update existing research-track table counts.
    for filename, label in TRACKS.items():
        pattern = re.compile(
            r"(?m)^(\|\s*\*\*" +
            re.escape(label) +
            r"\*\*\s*\|\s*)\d+(\s*\|[^\n]*\|\s*)$"
        )

        text, replacements = pattern.subn(
            lambda match: (
                match.group(1)
                + str(counts[filename])
                + match.group(2)
            ),
            text,
        )

        if replacements != 1:
            raise ValueError(
                f"Expected one README row for {label}; "
                f"found {replacements}"
            )

    # Create a visible automatically updated total.
    total_line = (
        f"**Total papers: {total}** "
        "(automatically counted from the three catalogs)."
    )

    if MARKER in text:
        pattern = re.compile(
            r"(?m)^" + re.escape(MARKER) + r"[^\n]*$"
        )

        text, replacements = pattern.subn(
            lambda match: MARKER + " " + total_line,
            text,
        )

        if replacements != 1:
            raise ValueError(
                "Expected exactly one paper-count marker"
            )

    else:
        # Locate the heading by its English text rather than
        # relying on a particular emoji or terminal encoding.
        headings = [
            line
            for line in text.splitlines()
            if line.startswith("## ")
            and "Explore the library" in line
        ]

        if len(headings) != 1:
            raise ValueError(
                "Expected exactly one Explore the library heading"
            )

        heading = headings[0]

        text = text.replace(
            heading,
            heading + "\n\n" + MARKER + " " + total_line,
            1,
        )

    # Write only after all validation succeeds.
    if text != original:
        README.write_text(text, encoding="utf-8")

    print("Updated README statistics:")
    for filename, label in TRACKS.items():
        print(f"  {label}: {counts[filename]}")
    print(f"  Total papers: {total}")


if __name__ == "__main__":
    update_readme()
