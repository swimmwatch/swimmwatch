"""Build responsive language-stack cards and shared technology cards."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from html import escape
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
ROOT = Path(__file__).resolve().parents[1]
PALETTE = {
    "background": ("#0b1625", "#f5f9fc"),
    "surface": ("#102033", "#ffffff"),
    "chip": ("#192e43", "#eef4f8"),
    "line": ("#29445f", "#cfdee9"),
    "foreground": ("#eef5ff", "#172f48"),
    "muted": ("#a2b8cf", "#4c6680"),
    "teal": ("#65e0c0", "#087c66"),
    "purple": ("#c5a4fa", "#8053ac"),
}
GLYPHS = {
    "typescript": '<path d="M14 2H4v22h16V8Z M14 2v6h6 M9 12l-3 4 3 4m6-8 3 4-3 4"/>',
    "packaging": '<path d="m12 2 10 6v12l-10 4-10-4V8Zm0 12v10M2 8l10 6 10-6M7 5l10 6v5"/>',
    "web": '<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-17-2 20"/>',
    "data": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 4 18 4 18 0V5M3 12c0 4 18 4 18 0"/>',
    "messaging": '<rect x="2" y="2" width="7" height="7" rx="2"/><rect x="15" y="15" width="7" height="7" rx="2"/><path d="M5 9v8h10M9 5h9v10"/>',
    "infrastructure": '<path d="m12 2 10 6v10l-10 6-10-6V8Zm0 12v10M2 8l10 6 10-6M7 5l10 6"/>',
    "delivery": '<circle cx="6" cy="5" r="3"/><circle cx="6" cy="20" r="3"/><circle cx="19" cy="20" r="3"/><path d="M6 8v9m4-12h3a6 6 0 0 1 6 6v6m-9-16-4 4 4 4"/>',
    "security": '<circle cx="8" cy="9" r="6"/><path d="m12 13 10 10m-5-5 3-3m-6 0 3-3"/>',
    "observability": '<path d="M1 13h5l4-10 5 20 4-10h5"/>',
    "agents": '<path d="M12 5V2m-9 9H1v7h2m18-7h2v7h-2"/><rect x="3" y="5" width="18" height="16" rx="5"/><path d="M7 11h2m6 0h2m-8 6h6"/>',
    "testing": '<path d="M8 2H3v5m13-5h5v5M3 17v5h5m8 0h5v-5M7 12l3 3 7-7"/>',
}


def add(parent, tag, text=None, **attributes):
    node = ET.SubElement(parent, f"{{{SVG}}}{tag}", {key.replace("_", "-"): str(value) for key, value in attributes.items()})
    node.text = text
    return node


def text_width(text, size):
    """Reserve conservative Arial widths without external font dependencies."""
    return sum(0.3 if char in "ilI.,:;!|'" else 0.9 if char in "MW@%" else 0.68 if char.isupper() else 0.59 for char in text) * size


def chip_layout(tools, width, size):
    x = y = 0
    items = []
    height, gap = size + 14, 8
    for tool in tools:
        chip_width = max(38, text_width(tool["name"], size) + 24)
        if chip_width > width:
            raise ValueError(f"Technology label exceeds card width: {tool['name']}")
        if x and x + chip_width > width:
            x, y = 0, y + height + gap
        items.append((tool, x, y, chip_width))
        x += chip_width + gap
    return items, y + height if items else 0


def card_plan(category, width, size, section_columns=1):
    padding, gap = 20, 20
    inner = width - padding * 2
    sections = {}
    for tool in category["tools"]:
        sections.setdefault(tool.get("section", ""), []).append(tool)
    cells = []
    y = 72
    entries = list(sections.items())
    cell_width = (inner - gap * (section_columns - 1)) / section_columns
    for start in range(0, len(entries), section_columns):
        row_height = 0
        for column, (label, tools) in enumerate(entries[start:start + section_columns]):
            items, height = chip_layout(tools, cell_width, size)
            offset = 25 if label else 0
            cells.append((label, padding + column * (cell_width + gap), y, items, offset))
            row_height = max(row_height, offset + height)
        y += row_height + 16
    return cells, y + 4


def render(categories, symbols, width):
    desktop = width == 1000
    margin, gap = (24, 16) if desktop else (14, 12)
    size = 16 if desktop else 14
    inner = width - margin * 2
    by_id = {category["id"]: category for category in categories}
    positions = []
    y = 58

    def place(category, x, top, card_width, columns=1):
        cells, height = card_plan(category, card_width, size, columns)
        positions.append((category, x, top, card_width, height, cells))
        return height

    y += place(by_id["python"], margin, y, inner, 2 if desktop else 1) + gap
    half = (inner - gap) / 2

    def place_row(row, top):
        card_width = half if len(row) == 2 else inner
        heights = [place(category, margin + index * (card_width + gap), top, card_width) for index, category in enumerate(row)]
        for index in range(1, len(row) + 1):
            category, x, card_top, w, _, cells = positions[-index]
            positions[-index] = (category, x, card_top, w, max(heights), cells)
        return max(heights)

    language_columns = 2 if desktop or width >= 480 else 1
    languages = [category for category in categories if category["scope"] == "language" and category["id"] != "python"]
    for start in range(0, len(languages), language_columns):
        row = languages[start:start + language_columns]
        y += place_row(row, y) + gap
    y += 26
    shared_label_y = y
    y += 26
    shared = [category for category in categories if category["scope"] == "shared"]
    columns = 2 if desktop else 1
    for start in range(0, len(shared), columns):
        row = shared[start:start + columns]
        y += place_row(row, y) + gap
    height = y - gap + margin
    root = ET.Element(f"{{{SVG}}}svg", {"width": str(width), "height": str(height), "viewBox": f"0 0 {width} {height}", "role": "img", "aria-labelledby": "title desc", "font-family": "Arial,Helvetica,sans-serif"})
    add(root, "title", "Technology stacks: Python, Go, TypeScript, web, and shared tools", id="title")
    add(root, "desc", "; ".join(category["title"] + ": " + ", ".join(tool["name"] for tool in category["tools"]) for category in categories), id="desc")
    defaults = ";".join(f"--{key}:{value[0]}" for key, value in PALETTE.items())
    light = ";".join(f"--{key}:{value[1]}" for key, value in PALETTE.items())
    add(root, "style", f":root{{{defaults}}}@media(prefers-color-scheme:light){{:root{{{light}}}}}")
    defs = add(root, "defs")
    for symbol in symbols:
        if symbol.get("id") in {"python", "go"}:
            clone = deepcopy(symbol)
            clone.set("id", "brand-" + symbol.get("id"))
            defs.append(clone)
    for identifier, glyph in GLYPHS.items():
        symbol = add(defs, "symbol", id="category-" + identifier, viewBox="0 0 24 26", fill="none", stroke="currentColor", stroke_width="1.7", stroke_linecap="round", stroke_linejoin="round")
        symbol.extend(ET.fromstring(f'<g xmlns="{SVG}">{glyph}</g>'))
    add(root, "rect", x="1", y="1", width=width - 2, height=height - 2, rx="18", fill="var(--background)", stroke="var(--line)")
    for label, baseline in (("LANGUAGE STACKS", 34), ("SHARED TECHNOLOGIES", shared_label_y)):
        add(root, "text", label, x=margin, y=baseline, fill="var(--muted)", font_size="12", letter_spacing="1.5")
        start = margin + text_width(label, 12) + len(label) * 1.5 + 18
        add(root, "path", d=f"M{start:g} {baseline - 4:g}H{width - margin:g}", stroke="var(--line)")
    for category, x, top, w, h, cells in positions:
        accent = f'var(--{category["accent"]})'
        card = add(root, "g", transform=f"translate({x:g} {top:g})", data_category=category["id"])
        add(card, "rect", width=f"{w:g}", height=h, rx="14", fill="var(--surface)", stroke="var(--line)")
        add(card, "rect", x="20", y="18", width="34", height="34", rx="9", fill="var(--chip)")
        icon = "brand-" + category["id"] if category["id"] in {"python", "go"} else "category-" + category["id"]
        add(card, "use", href="#" + icon, x="27", y="24", width="20", height="22", color=accent)
        add(card, "text", category["title"], x="66", y="36", dominant_baseline="central", font_size="20" if desktop else "17", font_weight="600", fill="var(--foreground)", data_available=f"{w - 86:g}")
        for label, cx, cy, items, offset in cells:
            if label:
                add(card, "text", label.upper(), x=cx, y=cy + 10, font_size="12", fill="var(--muted)", letter_spacing=".6")
            for tool, tx, ty, chip_width in items:
                group = add(card, "g", transform=f"translate({cx + tx:g} {cy + offset + ty:g})", data_tool=tool["name"])
                add(group, "rect", width=f"{chip_width:g}", height=size + 14, rx="6", fill="var(--chip)")
                add(group, "text", tool["name"], x="10", y=(size + 14) / 2, dominant_baseline="central", font_size=size, fill="var(--foreground)", data_available=f"{chip_width - 20:g}")
    return ET.tostring(root, encoding="unicode") + "\n"


def text_version(categories):
    lines = ["<ul>"]
    for category in categories:
        lines.append(f'<li><strong>{escape(category["title"])}:</strong> {escape(", ".join(tool["name"] for tool in category["tools"]))}</li>')
    return "\n".join([*lines, "</ul>"])


def main():
    directory = ROOT / "profile/stack"
    categories = json.loads((directory / "toolkit.json").read_text())
    symbols = ET.parse(directory / "symbols.svg").getroot().find(f"{{{SVG}}}defs")
    names = [tool["name"] for category in categories for tool in category["tools"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate technology in toolkit inventory")
    outputs = [(ROOT / "profile" / name, render(categories, symbols, width)) for name, width in (("toolkit.svg", 1000), ("toolkit-mobile.svg", 360), ("toolkit-mobile-wide.svg", 480))]
    for path, content in outputs:
        root = ET.fromstring(content)
        rendered = [group.get("data-tool") for group in root.iter(f"{{{SVG}}}g") if group.get("data-tool")]
        if sorted(rendered) != sorted(names):
            raise ValueError(f"Incomplete technology layout: {path.name}")
    readme = ROOT / "README.md"
    start, end = "<!-- TECH_STACK_START -->", "<!-- TECH_STACK_END -->"
    before, rest = readme.read_text().split(start)
    _, after = rest.split(end)
    for path, content in outputs:
        path.write_text(content)
    readme.write_text(before + start + "\n" + text_version(categories) + "\n" + end + after)
    print(f"Rendered {len(names)} technologies across {len(categories)} cards in three layouts; synchronized README text.")


if __name__ == "__main__":
    main()
