"""Refresh compact public GitHub metrics in the profile banners."""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)


def adapt_theme(content):
    """Let embedded SVGs inherit GitHub's color scheme without picture rewrites."""
    palette = {
        "line": ("#35516e", "#a4bcd2"),
        "blue": ("#85baff", "#276cae"),
        "node": ("#14273b", "#ffffff"),
        "background": ("#0b1625", "#eef5fb"),
        "muted": ("#9cb1ca", "#4c6680"),
        "foreground": ("#eef5ff", "#172f48"),
        "accent": ("#65e0c0", "#087c66"),
        "purple": ("#c5a4fa", "#8053ac"),
    }
    root = ET.fromstring(content)
    for style in root.findall(f"{{{SVG}}}style[@id='adaptive-theme']"):
        root.remove(style)
    content = ET.tostring(root, encoding="unicode")
    for name, (dark, _) in palette.items():
        content = content.replace(dark, f"var(--{name})")
    root = ET.fromstring(content)
    style = ET.Element(f"{{{SVG}}}style", {"id": "adaptive-theme"})
    dark = ";".join(f"--{name}:{colors[0]}" for name, colors in palette.items())
    light = ";".join(f"--{name}:{colors[1]}" for name, colors in palette.items())
    style.text = f":root{{{dark}}}@media(prefers-color-scheme:light){{:root{{{light}}}}}"
    root.insert(2, style)
    return ET.tostring(root, encoding="unicode") + "\n"


def fetch(path):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        "https://api.github.com" + path,
        headers=headers,
    )
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def read_languages(path):
    root = ET.parse(path).getroot()
    languages = []
    for group in root.iter(f"{{{SVG}}}g"):
        label = next(
            (node for node in group if node.get("data-testid") == "lang-name"), None
        )
        if label is None:
            continue
        match = re.fullmatch(r"(.+?)\s+(\d+(?:\.\d+)?)%", "".join(label.itertext()).strip())
        circle = group.find(f"{{{SVG}}}circle")
        if match is None or circle is None:
            raise ValueError("Invalid language card entry")
        color = circle.get("fill", "")
        percent = float(match[2])
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color) or not 0 < percent <= 100:
            raise ValueError("Invalid language color or percentage")
        languages.append((match[1], percent, color))
    if not 1 <= len(languages) <= 6 or abs(sum(row[1] for row in languages) - 100) > 0.1:
        raise ValueError("Expected up to six languages totaling 100 percent")
    return languages


def render_banner(path, metrics, languages, date):
    root = ET.parse(path).getroot()
    mobile = "mobile" in path.stem
    wide = "mobile-wide" in path.stem
    dark = "dark" in path.stem
    width, base, height = (480, 350, 594) if wide else (360, 372, 694) if mobile else (1000, 390, 506)
    foreground, muted, line, accent = (
        ("#eef5ff", "#9cb1ca", "#35516e", "#65e0c0")
        if dark else ("#172f48", "#4c6680", "#a4bcd2", "#087c66")
    )
    root.set("height", str(height))
    root.set("viewBox", f"0 0 {width} {height}")
    for child in list(root):
        if child.get("id") == "profile-summary":
            root.remove(child)
        elif child.tag == f"{{{SVG}}}rect" and child.get("x") == "1" and child.get("y") == "1":
            child.set("height", str(height - 2))

    margin = 24 if mobile else 42
    parts = [
        f'<g xmlns="{SVG}" id="profile-summary" font-family="Segoe UI,Arial,sans-serif">',
        f'<path d="M{margin} {base}H{width-margin}" stroke="{line}"/>',
    ]

    def text(x, y, value, size=12, color=muted, weight="400", extra=""):
        parts.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" {extra}>{escape(str(value))}</text>'
        )

    text(margin, base + (26 if mobile else 22), "PUBLIC GITHUB", 13 if mobile else 10, extra='letter-spacing="1.5"')
    for index, (label, value) in enumerate(metrics):
        x = margin + (index % 2) * 160 if mobile else margin + index * 102
        row = (index // 2) * 56 if mobile else 0
        text(x, base + (58 if mobile else 52) + row, f"{value:,}", 28 if mobile else 24, accent, "700")
        text(x, base + (79 if mobile else 72) + row, label, 18 if mobile else 14)

    left, top, bar_width = (24, 544, 312) if mobile else (486, 421, 472)
    if mobile:
        text(left, 528, "REPOSITORY LANGUAGES", 13, extra='letter-spacing="1"')
    else:
        text(left, base + 22, "PUBLIC REPO LANGUAGES", 10, extra='letter-spacing="1.4"')
    total = sum(language[1] for language in languages)
    offset = 0
    for _, percent, color in languages:
        segment = bar_width * percent / total
        parts.append(
            f'<rect x="{left+offset:.3f}" y="{top}" width="{segment:.3f}" '
            f'height="{7 if mobile else 5}" rx="1" fill="{color}"/>'
        )
        offset += segment
    for index, (name, percent, color) in enumerate(languages):
        columns = 2 if mobile else 3
        x = left + (index % columns) * (160 if mobile else 163)
        y = top + (32 if mobile else 25) + (index // columns) * (26 if mobile else 20)
        parts.append(f'<circle cx="{x+3}" cy="{y-4}" r="3" fill="{color}"/>')
        text(x + 12, y, f"{name} {percent:g}%", 17 if mobile else 16, foreground)

    if mobile:
        text(margin, 659, f"Counts updated {date} UTC", 12)
        text(margin, 678, "Languages describe public repository code.", 12)
    else:
        text(margin, 487, f"Updated {date} UTC · Stars/forks: original public repos", 9)
        text(left, 487, "Languages describe public repository code, not full professional experience.", 9)
    parts.append("</g>")
    summary = ET.fromstring("".join(parts))
    if wide:
        texts = summary.findall(f"{{{SVG}}}text")
        texts[0].set("y", "376")
        texts[0].set("font-size", "11")
        for index in range(4):
            value, label = texts[1 + index * 2:3 + index * 2]
            for node in (value, label):
                node.set("x", str(24 + index * 112))
            value.set("y", "410")
            value.set("font-size", "26")
            label.set("y", "430")
            label.set("font-size", "12")
        texts[9].set("y", "460")
        texts[9].set("font-size", "11")
        offset = 0
        for rect, (_, percent, _) in zip(summary.findall(f"{{{SVG}}}rect"), languages):
            segment = 432 * percent / total
            rect.set("x", f"{24 + offset:.3f}")
            rect.set("y", "476")
            rect.set("width", f"{segment:.3f}")
            offset += segment
        for index, circle in enumerate(summary.findall(f"{{{SVG}}}circle")):
            x, y = 24 + (index % 3) * 148, 508 + (index // 3) * 24
            circle.set("cx", str(x + 3))
            circle.set("cy", str(y - 4))
            node = texts[10 + index]
            node.set("x", str(x + 12))
            node.set("y", str(y))
            node.set("font-size", "13")
        for node, y in zip(texts[-2:], (558, 578)):
            node.set("y", str(y))
            node.set("font-size", "11")
    root.append(summary)
    content = ET.tostring(root, encoding="unicode") + "\n"
    return adapt_theme(content) if dark else content


def main():
    owner = sys.argv[1]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", owner):
        raise ValueError("Invalid GitHub username")
    profile = Path(__file__).resolve().parents[1] / "profile"
    languages = read_languages(profile / "top-langs.svg")
    user = fetch(f"/users/{owner}")
    repositories = []
    page = 1
    while True:
        batch = fetch(f"/users/{owner}/repos?type=owner&per_page=100&page={page}")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    originals = [repo for repo in repositories if not repo["fork"] and not repo["private"]]
    metrics = [
        ("Public repos", user["public_repos"]),
        ("Stars", sum(repo["stargazers_count"] for repo in originals)),
        ("Forks", sum(repo["forks_count"] for repo in originals)),
        ("Followers", user["followers"]),
    ]
    if any(type(value) is not int or value < 0 for _, value in metrics):
        raise ValueError("Invalid public profile metric")
    date = datetime.now(timezone.utc).date().isoformat()
    outputs = []
    for name in ["banner-dark.svg", "banner-light.svg", "banner-mobile-dark.svg", "banner-mobile-light.svg", "banner-mobile-wide-dark.svg", "banner-mobile-wide-light.svg"]:
        path = profile / name
        outputs.append((path, render_banner(path, metrics, languages, date)))
    # Validate and render every variant before replacing any existing banner.
    for path, content in outputs:
        temporary = path.with_suffix(".svg.tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    print(f"Updated public GitHub summary in six profile banners for {owner}")


if __name__ == "__main__":
    main()
