import argparse
import html
from pathlib import Path
from statistics import mean
from typing import Any

from kitchenpilot.seed.recipe_dataset import (
    DEFAULT_RECIPE_DATA_PATH,
    load_recipe_dataset_entries,
    load_recipes,
)


OUTPUT_DIR = Path(__file__).with_name("output")
DEFAULT_HTML_PATH = OUTPUT_DIR / "recipe_dataset_preview.html"


def main() -> None:
    """Parse CLI arguments, validate the recipe dataset, and optionally write an HTML preview."""
    parser = argparse.ArgumentParser(description="Visualize the KitchenPilot recipe dataset.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_RECIPE_DATA_PATH,
        help="Path to the recipe JSON dataset.",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_PATH,
        help="Path for the generated HTML preview.",
    )
    parser.add_argument(
        "--no-html",
        action="store_true",
        help="Only print the terminal summary; do not write an HTML preview.",
    )
    args = parser.parse_args()

    entries = load_recipe_dataset_entries(args.data)
    recipes = load_recipes(args.data)

    print_terminal_summary(entries)
    print("\nPydantic validation: OK")
    print(f"Validated recipes: {len(recipes)}")

    if not args.no_html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(entries), encoding="utf-8")
        print(f"\nHTML preview written to: {args.html.resolve()}")


def print_terminal_summary(entries: list[dict[str, Any]]) -> None:
    """Print a compact terminal summary of recipe counts and per-recipe coverage."""
    step_counts = [len(entry["steps"]) for entry in entries]
    ingredient_counts = [len(entry["ingredients"]) for entry in entries]

    print("KitchenPilot Recipe Dataset Preview")
    print("=" * 36)
    print(f"Recipes: {len(entries)}")
    print(f"Steps: min={min(step_counts)}, max={max(step_counts)}, avg={mean(step_counts):.1f}")
    print(
        "Ingredients: "
        f"min={min(ingredient_counts)}, max={max(ingredient_counts)}, "
        f"avg={mean(ingredient_counts):.1f}"
    )
    print()
    print(f"{'ID':>2}  {'Recipe':<14} {'Diff':<6} {'Min':>3} {'Ing':>3} {'Step':>4} {'Risk':>4}")
    print("-" * 54)
    for entry in entries:
        risk_count = sum(1 for step in entry["steps"] if step.get("risk_tip"))
        print(
            f"{entry['id']:>2}  "
            f"{entry['name']:<14} "
            f"{entry['difficulty']:<6} "
            f"{entry['time_minutes']:>3} "
            f"{len(entry['ingredients']):>3} "
            f"{len(entry['steps']):>4} "
            f"{risk_count:>4}"
        )


def render_html(entries: list[dict[str, Any]]) -> str:
    """Render the full dataset preview as a standalone HTML document."""
    cards = "\n".join(render_recipe_card(entry) for entry in entries)
    step_counts = [len(entry["steps"]) for entry in entries]
    ingredient_counts = [len(entry["ingredients"]) for entry in entries]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>KitchenPilot Recipe Dataset Preview</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #202124;
      background: #f6f7f9;
    }}
    header {{
      padding: 28px 36px;
      background: #ffffff;
      border-bottom: 1px solid #e4e7ec;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 28px;
      letter-spacing: 0;
    }}
    .summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .metric {{
      padding: 10px 14px;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      background: #fbfcfe;
    }}
    main {{
      padding: 24px 36px 40px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 16px;
    }}
    article {{
      background: #ffffff;
      border: 1px solid #e1e5eb;
      border-radius: 8px;
      padding: 18px;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 12px;
      color: #4b5563;
      font-size: 13px;
    }}
    .pill {{
      padding: 3px 8px;
      border-radius: 999px;
      background: #eef2f7;
    }}
    p {{
      line-height: 1.55;
    }}
    ol, ul {{
      padding-left: 22px;
    }}
    li {{
      margin: 5px 0;
      line-height: 1.45;
    }}
    h3 {{
      margin: 16px 0 6px;
      font-size: 15px;
    }}
    .risk {{
      color: #9a3412;
    }}
    .source {{
      color: #2563eb;
      word-break: break-all;
    }}
  </style>
</head>
<body>
  <header>
    <h1>KitchenPilot Recipe Dataset Preview</h1>
    <div class="summary">
      <div class="metric">菜谱数：{len(entries)}</div>
      <div class="metric">步骤数：{min(step_counts)}-{max(step_counts)}，平均 {mean(step_counts):.1f}</div>
      <div class="metric">食材数：{min(ingredient_counts)}-{max(ingredient_counts)}，平均 {mean(ingredient_counts):.1f}</div>
    </div>
  </header>
  <main>
    {cards}
  </main>
</body>
</html>
"""


def render_recipe_card(entry: dict[str, Any]) -> str:
    """Render one recipe as an HTML card with ingredients, steps, and sources."""
    ingredients = ", ".join(
        f"{item['ingredient']} {item.get('amount', '')}".strip()
        for item in entry["ingredients"]
    )
    steps = "\n".join(
        "<li>"
        f"{escape(step['content'])}"
        f"{render_tip(step.get('beginner_tip'), '提示')}"
        f"{render_tip(step.get('risk_tip'), '风险', risk=True)}"
        "</li>"
        for step in entry["steps"]
    )
    failures = "\n".join(f"<li>{escape(item)}</li>" for item in entry.get("common_failures", []))
    sources = "\n".join(
        f'<li><span class="source">{escape(source)}</span></li>'
        for source in entry.get("source_urls", [])
    )

    return f"""<article>
  <h2>{escape(entry["id"])}. {escape(entry["name"])}</h2>
  <div class="meta">
    <span class="pill">{escape(entry["difficulty"])}</span>
    <span class="pill">{escape(entry["time_minutes"])} 分钟</span>
    <span class="pill">步骤 {len(entry["steps"])}</span>
    <span class="pill">食材 {len(entry["ingredients"])}</span>
  </div>
  <p>{escape(entry["description"])}</p>
  <h3>食材</h3>
  <p>{escape(ingredients)}</p>
  <h3>步骤</h3>
  <ol>{steps}</ol>
  <h3>常见失败点</h3>
  <ul>{failures}</ul>
  <h3>来源</h3>
  <ul>{sources}</ul>
</article>"""


def render_tip(value: str | None, label: str, risk: bool = False) -> str:
    """Render an optional beginner or risk tip inline with a recipe step."""
    if not value:
        return ""
    class_name = ' class="risk"' if risk else ""
    return f" <small{class_name}>[{escape(label)}：{escape(value)}]</small>"


def escape(value: object) -> str:
    """Escape arbitrary values before embedding them in generated HTML."""
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    main()
