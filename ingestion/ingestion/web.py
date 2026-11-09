"""Download and parse the meine-tcm.com acupuncture point atlas into curated point records.

Each point page has a fixed layout: location, a "Helps with" symptom list, an
"Acupressure" how-to, and a "Use: <duration> <pressure>" summary. Pages are
downloaded once into `<out_dir>/html/` (re-runs reuse them), parsed, and
written to `<out_dir>/points.json` for `ingestion.points` to load.

The site states no licence: its text is used for retrieval with attribution,
and its images are not reused.

Usage:
    uv run python -m ingestion.web sources/web/meine-tcm
"""

import argparse
import json
import logging
import re
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from ingestion.codes import code_from_parts

log = logging.getLogger(__name__)

INDEX_URL = "https://www.meine-tcm.com/en/atlas-of-acupuncture-points/"
POINT_URL = re.compile(
    r"https://www\.meine-tcm\.com/en/acupuncture-points/acupuncture-point-[\w-]+/"
)
USER_AGENT = "AcupressureAppIngestion/0.1 (one-off download for a student project)"
REQUEST_DELAY_SECONDS = 1.0

SOURCE = {
    "title": "meine-tcm.com Acupuncture Point Atlas",
    "author": "Meine TCM",
    "url": INDEX_URL,
    "language": "en",
    "license": "No licence stated; text used for retrieval with attribution, images not reused",
}

# Extra points (outside the meridians), keyed by the site's URL slug. The site
# numbers them its own way, so they are mapped by hand: to the WHO extra-point
# code where the point is a standard one, otherwise to a descriptive EX- code.
# Unlisted extra points get "EX-" plus their name.
EXTRA_POINT_IDS = {
    "ex-01": "EX-HN3",  # Yintang
    "ex-17": "EX-UE8",  # Wailaogong, "neck stiffness" point
    "ex-18": "EX-UE7",  # Yaotongdian, "lumbago points"
    "ex-23": "EX-LE5",  # Xiyan, "knee eyes"
    "ex-b2": "EX-NECK-SHOULDER",  # the site's own zones, not WHO EX-B points
    "ex-b4": "EX-WAIST",
    "ex-b5": "EX-LOWER-BACK",
    "ex-hn-15": "EX-UPPER-NECK",
}
# Pages describing several points at once, which do not fit a single point record.
SKIPPED_SLUGS = {"ex-a01-a12"}

# Marks the end of a link: the site sometimes omits the comma between a linked
# symptom and the next one ("<a>Knee pain</a>liver harmonizing").
LINK_END = "\u2063"

PRESSURE_WORDS = {"soft": "Soft", "medium": "Medium", "vigorous": "Vigorous"}


@dataclass
class WebPoint:
    id: str
    name: str
    url: str
    summary: str
    location: str
    description: list[str]
    helps_with: list[str]
    tcm_effects: list[str]
    contraindication: str | None
    instructions: list[str]
    duration: str | None
    pressure: str | None
    category: str | None = None
    meridian: str | None = None
    names: list[str] = field(default_factory=list)


class _TextLines(HTMLParser):
    """Flatten HTML into one line per block element; headings are prefixed with '#<level> '."""

    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "br", "tr", "section"}
    SKIPPED = {"script", "style", "svg", "noscript", "header", "footer", "nav", "form"}

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []
        self._current: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIPPED:
            self._skip_depth += 1
        if tag in self.BLOCKS:
            self._flush()
        if tag in {"h1", "h2", "h3", "h4"}:
            self._current.append(f"#{tag[1]} ")
        elif tag == "li":
            self._current.append("- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED and self._skip_depth:
            self._skip_depth -= 1
        if tag == "a" and not self._skip_depth:
            self._current.append(LINK_END)
        if tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._current.append(data)

    def _flush(self) -> None:
        line = " ".join("".join(self._current).split()).strip(LINK_END + " ")
        self._current = []
        if line and line not in {"-", "#1", "#2", "#3", "#4"}:
            self.lines.append(line)


def html_lines(html: str) -> list[str]:
    parser = _TextLines()
    parser.feed(html)
    parser.close()
    parser._flush()
    return parser.lines


def point_links(index_html: str) -> list[str]:
    return sorted(set(POINT_URL.findall(index_html)))


def slug_of(url: str) -> str:
    return url.rstrip("/").rsplit("acupuncture-point-", 1)[1]


def point_id(slug: str, name: str) -> str:
    """WHO code for classical points; a stable EX- code for extra points."""
    if slug in EXTRA_POINT_IDS:
        return EXTRA_POINT_IDS[slug]
    if match := re.fullmatch(r"([a-z]+)-(\d+)", slug):
        if code := code_from_parts(*match.groups()):
            return code
    return "EX-" + re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")


def _after(lines: list[str], label: str) -> int | None:
    """Index of the line after the first line equal to `label` (with or without a heading mark)."""
    for i, line in enumerate(lines):
        if re.sub(r"^#\d ", "", line) == label:
            return i + 1
    return None


def _section(lines: list[str], label: str, stops: tuple[str, ...]) -> list[str]:
    start = _after(lines, label)
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if line.startswith("#") or any(re.sub(r"^- ", "", line).startswith(s) for s in stops):
            break
        out.append(re.sub(r"^- ", "", line))
    return out


def _helps_with(lines: list[str]) -> list[str]:
    items: dict[str, str] = {}
    for line in _section(lines, "Helps with:", ("Properties of the acupuncture point", "Use:")):
        for item in re.split(f"[,{LINK_END}]", line):
            # The site numbers variants of one concern ("Chronic fatigue 1", "Chronic fatigue 2").
            item = re.sub(r"\s+\d+$", "", item).strip()
            if item:
                items.setdefault(item.lower(), item[0].upper() + item[1:])
    return list(items.values())


def _instructions(lines: list[str]) -> list[str]:
    steps = _section(
        lines, "Acupressure:", ("Acupuncture technique:", "Video explanation", "AcuPen:")
    )
    # Drop a dangling disclaimer that refers to a sentence outside this section.
    return [s for s in steps if not s.startswith("These should of course have been clarified")]


def parse_point(html: str, url: str) -> WebPoint:
    marked = html_lines(html)
    lines = [re.sub(rf"\s*{LINK_END}", "", line) for line in marked]
    title_index = next(i for i, line in enumerate(lines) if line.startswith("#1 "))
    summary = lines[title_index + 1].removeprefix("#3 ") if lines[title_index + 1 :] else ""

    location = _section(lines, "Location:", ("Use:", "Helps with:"))
    location_end = (_after(lines, "Location:") or 0) + len(location)
    name_index = next(
        (i for i in range(location_end, len(lines)) if lines[i].startswith("#2 ")), None
    )
    name = lines[name_index].removeprefix("#2 ") if name_index is not None else ""
    if name.endswith(")") and "(" not in name:
        name = name[:-1]  # stray bracket in the source
    description = []
    if name_index is not None:
        for line in lines[name_index + 1 :]:
            if line.startswith(("Use:", "Name:", "#")):
                break
            description.append(line)

    duration = pressure = None
    use = next((line for line in lines if line.startswith("Use: ")), None)
    if use and (match := re.fullmatch(r"Use: (.+?)\s+(\w+)", use)):
        duration = match.group(1)
        pressure = PRESSURE_WORDS.get(match.group(2).lower())
        if pressure is None:
            duration = use.removeprefix("Use: ")

    contraindication = _section(lines, "Contraindication:", ())[:1]
    category = _section(lines, "Category:", ("Effect from",))[:1]
    meridian = _section(lines, "Meridian:", ("Element:",))[:1]
    slug = slug_of(url)
    return WebPoint(
        id=point_id(slug, name),
        name=name,
        url=url,
        summary=summary,
        location=" ".join(location[:1]),
        description=description,
        helps_with=_helps_with(marked),
        tcm_effects=_section(
            lines, "Effect from the point of view of TCM:", ("Contraindication:",)
        ),
        contraindication=contraindication[0] if contraindication else None,
        instructions=_instructions(lines),
        duration=duration,
        pressure=f"{pressure} pressure" if pressure else None,
        category=category[0] if category else None,
        meridian=meridian[0] if meridian else None,
        names=_section(lines, "Name:", ("Helps with:", "Properties")),
    )


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return str(response.read().decode("utf-8"))


def download(url: str, path: Path, refresh: bool = False) -> str:
    """Return the page from the local cache, downloading it first if needed."""
    if path.is_file() and not refresh:
        return path.read_text(encoding="utf-8")
    time.sleep(REQUEST_DELAY_SECONDS)
    html = fetch(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return html


def scrape(out_dir: Path, refresh: bool = False) -> list[WebPoint]:
    html_dir = out_dir / "html"
    points = []
    for url in point_links(download(INDEX_URL, html_dir / "index.html", refresh)):
        slug = slug_of(url)
        if slug in SKIPPED_SLUGS:
            log.info("Skipping multi-point page %s", slug)
            continue
        point = parse_point(download(url, html_dir / f"{slug}.html", refresh), url)
        if not (point.location and point.instructions):
            log.warning("Skipping %s: no location or acupressure instructions", slug)
            continue
        points.append(point)
    ids = [p.id for p in points]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate point ids: {sorted(i for i in ids if ids.count(i) > 1)}")
    return points


def write_points(points: list[WebPoint], path: Path) -> None:
    data = {"source": SOURCE, "points": [asdict(p) for p in points]}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and parse the meine-tcm point atlas.")
    parser.add_argument("out_dir", type=Path, help="Folder for cached pages and points.json")
    parser.add_argument("--refresh", action="store_true", help="Download pages again")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    points = scrape(args.out_dir, args.refresh)
    write_points(points, args.out_dir / "points.json")
    log.info("Wrote %d points to %s", len(points), args.out_dir / "points.json")


if __name__ == "__main__":
    main()
