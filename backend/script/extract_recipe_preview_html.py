import argparse
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML_PATH = (
    BACKEND_ROOT
    / "src"
    / "script"
    / "data"
    / "preview_fixed_clickable_links.html"
)
DEFAULT_OUTPUT_PATH = (
    BACKEND_ROOT / "src" / "kitchenpilot" / "seed" / "data" / "recipes_extracted.json"
)


@dataclass
class HtmlNode:
    """Small HTML tree node used to parse the generated recipe preview."""

    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["HtmlNode | str"] = field(default_factory=list)


class HtmlTreeParser(HTMLParser):
    """Build a minimal HTML tree from the recipe preview document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Append a new node and make it the active parent."""
        node = HtmlNode(tag=tag, attrs={key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Append self-closing nodes without changing the active parent."""
        self.stack[-1].children.append(
            HtmlNode(tag=tag, attrs={key: value or "" for key, value in attrs})
        )

    def handle_endtag(self, tag: str) -> None:
        """Pop the matching active element when the document closes a tag."""
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        """Append text nodes to the active parent."""
        if data:
            self.stack[-1].children.append(data)


def main() -> None:
    """Extract the fixed HTML recipe preview into the eval JSON dataset."""
    parser = argparse.ArgumentParser(description="Extract recipe JSON from the HTML preview.")
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()

    recipes = extract_recipes(args.html)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Extracted recipes: {len(recipes)}")
    print(f"Extracted steps: {sum(len(recipe['steps']) for recipe in recipes)}")
    print(f"Output: {args.output.resolve()}")


def extract_recipes(path: Path) -> list[dict[str, object]]:
    """Parse recipe cards from a KitchenPilot recipe preview HTML file."""
    parser = HtmlTreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    recipes = [extract_recipe(article) for article in descendants(parser.root, "article")]
    if not recipes:
        raise ValueError(f"No recipe articles found in HTML: {path}")
    return recipes


def extract_recipe(article: HtmlNode) -> dict[str, object]:
    """Extract one recipe card from the preview HTML."""
    recipe_id = 0
    recipe_name = ""
    difficulty = ""
    time_text = ""
    intro = ""
    ingredients = ""
    steps: list[str] = []
    failures: list[str] = []
    chunks: list[dict[str, str]] = []
    sources: list[str] = []
    section = ""

    for child in child_nodes(article):
        if child.tag == "h2":
            recipe_id, recipe_name = parse_heading(node_text(child))
        elif child.tag == "div" and "meta" in classes(child):
            pills = [node_text(span) for span in descendants(child, "span")]
            difficulty = pills[0] if pills else ""
            time_text = pills[1] if len(pills) > 1 else ""
        elif child.tag == "h3":
            section = node_text(child)
        elif child.tag == "p" and not section:
            intro = node_text(child)
        elif child.tag == "p" and section == "食材":
            ingredients = node_text(child)
        elif child.tag == "ol" and section == "步骤":
            steps = list_text(child)
        elif child.tag == "ul" and section == "常见失败点":
            failures = list_text(child)
        elif child.tag == "ul" and section == "RAG chunks":
            chunks = parse_chunks(list_text(child))
        elif child.tag == "ul" and section == "来源":
            sources = parse_sources(child)

    if not recipe_id or not recipe_name:
        raise ValueError(f"Recipe heading is missing an id or name: {node_text(article)[:80]}")
    return {
        "id": recipe_id,
        "name": recipe_name,
        "description": intro,
        "difficulty": difficulty,
        "time_minutes": parse_time_minutes(time_text),
        "beginner_friendly": difficulty != "hard",
        "cuisine": "家常菜",
        "seasons": [],
        "ingredients": parse_ingredients(ingredients),
        "steps": parse_steps(steps),
        "common_failures": [*failures, *chunk_contents(chunks, "failure_reason")],
        "substitutions": {
            substitution_key(content, index): content
            for index, content in enumerate(chunk_contents(chunks, "substitution"), start=1)
        },
        "safety_notes": chunk_contents(chunks, "safety_note"),
        "source_urls": sources,
    }


def parse_heading(value: str) -> tuple[int, str]:
    """Return the numeric recipe id and recipe name from a card heading."""
    match = re.match(r"(\d+)\.\s*(.+)", value)
    if not match:
        raise ValueError(f"Unexpected recipe heading: {value}")
    return int(match.group(1)), match.group(2)


def parse_chunks(values: list[str]) -> list[dict[str, str]]:
    """Split list items such as 'failure_reason: ...' into chunk records."""
    chunks: list[dict[str, str]] = []
    for value in values:
        chunk_type, separator, content = value.partition(":")
        if not separator:
            raise ValueError(f"Unexpected RAG chunk text: {value}")
        chunks.append({"chunk_type": chunk_type.strip(), "content": content.strip()})
    return chunks


def parse_time_minutes(value: str) -> int:
    """Extract the first minute count from card text such as '15 分钟'."""
    match = re.search(r"\d+", value)
    if not match:
        raise ValueError(f"Recipe time must include minutes: {value!r}")
    return int(match.group())


def parse_ingredients(value: str) -> list[dict[str, object]]:
    """Split the preview ingredient line into runtime ingredient records."""
    ingredients: list[dict[str, object]] = []
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        name, separator, amount = item.partition(" ")
        ingredients.append(
            {
                "ingredient": name,
                "amount": amount.strip() if separator else "",
                "required": True,
            }
        )
    if not ingredients:
        raise ValueError("Recipe must include ingredients.")
    return ingredients


def parse_steps(values: list[str]) -> list[dict[str, object]]:
    """Split inline step markers into runtime step records."""
    return [
        {
            "order": order,
            "content": re.sub(r"\s*\[(提示|风险)：.*?\]", "", value).strip(),
            "beginner_tip": marker(value, "提示"),
            "risk_tip": marker(value, "风险"),
        }
        for order, value in enumerate(values, start=1)
    ]


def marker(value: str, label: str) -> str | None:
    """Return text from an inline marker such as '[提示：...]'."""
    match = re.search(rf"\[{label}：(.*?)\]", value)
    return match.group(1).strip() if match else None


def chunk_contents(chunks: list[dict[str, str]], chunk_type: str) -> list[str]:
    """Return chunk content strings for one HTML chunk category."""
    return [
        chunk["content"].strip()
        for chunk in chunks
        if chunk["chunk_type"] == chunk_type and chunk["content"].strip()
    ]


def substitution_key(content: str, index: int) -> str:
    """Build a substitution dictionary key when the HTML chunk lacks a slot field."""
    match = re.match(r"(?:没有|不想放)(.+?)(?:时|，)", content)
    if match:
        return match.group(1)
    return f"替代建议 {index}"


def parse_sources(node: HtmlNode) -> list[str]:
    """Prefer anchor href values and fall back to visible source list text."""
    sources: list[str] = []
    for item in child_nodes(node, "li"):
        links = [link.attrs.get("href", "").strip() for link in descendants(item, "a")]
        visible = node_text(item)
        source = next((link for link in links if link), visible)
        if source:
            sources.append(source)
    return sources


def list_text(node: HtmlNode) -> list[str]:
    """Return normalized text from direct list items."""
    return [node_text(item) for item in child_nodes(node, "li")]


def node_text(node: HtmlNode) -> str:
    """Return compact text from a node and its descendants."""
    parts: list[str] = []
    collect_text(node, parts)
    return normalize_text("".join(parts))


def collect_text(node: HtmlNode, parts: list[str]) -> None:
    """Collect descendant text nodes in document order."""
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        else:
            collect_text(child, parts)


def normalize_text(value: str) -> str:
    """Collapse HTML whitespace without changing inline punctuation."""
    return re.sub(r"\s+", " ", value).strip()


def child_nodes(node: HtmlNode, tag: str | None = None) -> list[HtmlNode]:
    """Return direct child element nodes, optionally filtered by tag."""
    return [
        child
        for child in node.children
        if isinstance(child, HtmlNode) and (tag is None or child.tag == tag)
    ]


def descendants(node: HtmlNode, tag: str) -> list[HtmlNode]:
    """Return descendant element nodes with the requested tag."""
    matches: list[HtmlNode] = []
    for child in child_nodes(node):
        if child.tag == tag:
            matches.append(child)
        matches.extend(descendants(child, tag))
    return matches


def classes(node: HtmlNode) -> set[str]:
    """Return CSS classes from an element."""
    return set(node.attrs.get("class", "").split())


if __name__ == "__main__":
    main()
