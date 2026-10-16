"""Build self-contained, responsive toolkit artwork from the technology inventory."""

import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path


SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ROOT = Path(__file__).resolve().parents[1]
PALETTE = {
    "background": ("#0b1625", "#eef5fb"),
    "surface": ("#102033", "#ffffff"),
    "surface-end": ("#0e1b2b", "#f8fbff"),
    "icon": ("#172c41", "#edf5fc"),
    "line": ("#29445f", "#adc4d8"),
    "faint": ("#1c334b", "#dfebf5"),
    "foreground": ("#eef5ff", "#172f48"),
    "muted": ("#9cb1ca", "#4c6680"),
    "teal": ("#65e0c0", "#087c66"),
    "blue": ("#85baff", "#276cae"),
    "purple": ("#c5a4fa", "#8053ac"),
}
CATEGORY_GLYPHS = {
    "languages": '<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-17-2 20"/>',
    "backend": '<rect x="2" y="3" width="20" height="7" rx="2"/><rect x="2" y="14" width="20" height="7" rx="2"/><path d="M6 6.5h1m4 0h7M6 17.5h1m4 0h7"/>',
    "data": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
    "messaging": '<rect x="2" y="5" width="4" height="11" rx="1"/><rect x="10" y="5" width="4" height="11" rx="1"/><rect x="18" y="5" width="4" height="11" rx="1"/><path d="M3 21h17m-3-3 3 3-3 3"/>',
    "infrastructure": '<path d="m12 2 10 6v10l-10 6-10-6V8Zm0 12v10M2 8l10 6 10-6M7 5l10 6"/>',
    "observability": '<path d="M2 2v20h20M5 15l4-9 4 7 4-10 5 5"/>',
    "agents": '<path d="M12 5V2m-9 9H1v7h2m18-7h2v7h-2"/><rect x="3" y="5" width="18" height="16" rx="5"/><path d="M7 11h2m6 0h2m-8 6h6"/>',
    "testing": '<path d="m12 2 10 4v8c-2 5-6 8-10 10C8 22 4 19 2 14V6ZM7 12l4 4 7-8"/>',
}


def add(parent, tag, text=None, **attributes):
    node = ET.SubElement(parent, f"{{{SVG}}}{tag}", {key.replace("_", "-"): str(value) for key, value in attributes.items()})
    node.text = text
    return node


def render(categories, symbols, width, columns):
    desktop = width == 1000
    margin, gap = (24, 16) if desktop else (16, 12)
    card_width = (width - 2 * margin - gap) / 2 if desktop else width - 2 * margin
    height_for = lambda category: 84 + math.ceil(len(category["tools"]) / columns) * 44
    positions = []
    if desktop:
        by_id = {category["id"]: category for category in categories}
        for column, ids in enumerate((('languages', 'data', 'agents', 'testing'), ('backend', 'infrastructure', 'messaging', 'observability'))):
            y = 64
            for identifier in ids:
                category = by_id[identifier]
                positions.append((category, margin + column * (card_width + gap), y))
                y += height_for(category) + gap
        height = int(y - gap + margin)
    else:
        y = 56
        for category in categories:
            positions.append((category, margin, y))
            y += height_for(category) + gap
        height = y - gap + margin

    root = ET.Element(f"{{{SVG}}}svg", {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}", "role": "img", "aria-labelledby": "title desc", "font-family": "Arial,Helvetica,sans-serif"})
    add(root, "title", "Engineering toolkit — backend, infrastructure, and agent tooling", id="title")
    add(root, "desc", "; ".join(category["title"] + ": " + ", ".join(tool["name"] for tool in category["tools"]) for category in categories), id="desc")
    defaults = ";".join(f"--{key}:{value[0]}" for key, value in PALETTE.items())
    light = ";".join(f"--{key}:{value[1]}" for key, value in PALETTE.items())
    add(root, "style", f":root{{{defaults}}}@media(prefers-color-scheme:light){{:root{{{light}}}}}.tool-label{{fill:var(--foreground);font-weight:500}}.category-title{{fill:var(--foreground);font-weight:600}}")
    defs = add(root, "defs")
    gradient = add(defs, "linearGradient", id="card-surface", x2="0", y2="1")
    add(gradient, "stop", offset="0", stop_color="var(--surface)")
    add(gradient, "stop", offset="1", stop_color="var(--surface-end)")
    grid = add(defs, "pattern", id="grid", width="24", height="24", patternUnits="userSpaceOnUse")
    add(grid, "path", d="M24 0H0V24", fill="none", stroke="var(--line)", stroke_width=".6", opacity=".17")
    for symbol in symbols:
        clone = deepcopy(symbol)
        clone.set("id", "brand-" + symbol.get("id"))
        defs.append(clone)
    for identifier, glyph in CATEGORY_GLYPHS.items():
        symbol = add(defs, "symbol", id="category-" + identifier, viewBox="0 0 24 26", fill="none", stroke="currentColor", stroke_width="1.7", stroke_linecap="round", stroke_linejoin="round")
        fragment = ET.fromstring(f'<g xmlns="{SVG}">{glyph}</g>')
        symbol.extend(fragment)

    add(root, "rect", x="1", y="1", width=width - 2, height=height - 2, rx="18", fill="var(--background)", stroke="var(--line)")
    add(root, "rect", x="1", y="1", width=width - 2, height=height - 2, rx="18", fill="url(#grid)")
    add(root, "text", "ENGINEERING TOOLKIT", x=margin, y="34", fill="var(--muted)", font_size="11", letter_spacing="1.8")
    for index, accent in enumerate(("teal", "blue", "purple")):
        add(root, "path", d=f"M{width - margin - 58 + index * 22} 30h14", stroke=f"var(--{accent})", stroke_width="3", stroke_linecap="round")
    if desktop:
        add(root, "path", d=f"M500 112V{height - 72}", stroke="var(--line)", stroke_width="1", stroke_dasharray="2 6", opacity=".6")

    padding = 24 if desktop else 16
    cell_gap = 12 if columns == 2 else 8
    cell_width = (card_width - 2 * padding - (columns - 1) * cell_gap) / columns
    label_size = 15 if columns == 3 else 16
    plate_size, label_x = (22, 29) if columns == 3 else (24, 32)
    for category, x, y in positions:
        card_height = height_for(category)
        accent = f'var(--{category["accent"]})'
        card = add(root, "g", transform=f"translate({x:g} {y:g})", data_category=category["id"], **{"class": "stack-card"})
        add(card, "rect", width=f"{card_width:g}", height=card_height, rx="14", fill="url(#card-surface)", stroke="var(--line)")
        add(card, "path", d="M24 0h42", stroke=accent, stroke_width="2", stroke_linecap="round")
        add(card, "rect", x="20", y="20", width="40", height="40", rx="11", fill="var(--icon)", stroke=accent, stroke_opacity=".35")
        add(card, "use", href="#category-" + category["id"], x="28", y="27", width="24", height="26", color=accent)
        title = add(card, "text", category["title"], x="76", y="41", dominant_baseline="central", font_size="19" if len(category["title"]) > 23 else "20", data_available=f"{card_width - 92:g}", **{"class": "category-title"})
        add(card, "path", d=f"M20 72H{card_width - 20:g}", stroke="var(--faint)")
        for index, tool in enumerate(category["tools"]):
            tx = padding + (index % columns) * (cell_width + cell_gap)
            ty = 84 + (index // columns) * 44
            group = add(card, "g", transform=f"translate({tx:g} {ty:g})", data_tool=tool["name"], **{"class": "tool"})
            add(group, "rect", width=plate_size, height=plate_size, rx="6", fill="var(--icon)")
            add(group, "use", href="#brand-" + tool["icon"], x="3", y="3", width=plate_size - 6, height=plate_size - 6, color=accent)
            add(group, "text", tool["name"], x=label_x, y=plate_size / 2, dominant_baseline="central", font_size=label_size, data_available=f"{cell_width - label_x:g}", **{"class": "tool-label"})
    return ET.tostring(root, encoding="unicode") + "\n"


def main():
    directory = ROOT / "profile/stack"
    categories = json.loads((directory / "toolkit.json").read_text())
    symbols = ET.parse(directory / "symbols.svg").getroot().find(f"{{{SVG}}}defs")
    names = [tool["name"] for category in categories for tool in category["tools"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate technology in toolkit inventory")
    outputs = [(ROOT / "profile" / name, render(categories, symbols, width, columns)) for name, width, columns in (("toolkit.svg", 1000, 2), ("toolkit-mobile.svg", 360, 2), ("toolkit-mobile-wide.svg", 480, 3))]
    for path, content in outputs:
        root = ET.fromstring(content)
        rendered = [group.get("data-tool") for group in root.iter(f"{{{SVG}}}g") if group.get("data-tool")]
        if sorted(rendered) != sorted(names):
            raise ValueError(f"Incomplete technology layout: {path.name}")
    for path, content in outputs:
        path.write_text(content)
    print(f"Rendered {len(names)} technologies across {len(categories)} categories in three layouts.")


if __name__ == "__main__":
    main()
