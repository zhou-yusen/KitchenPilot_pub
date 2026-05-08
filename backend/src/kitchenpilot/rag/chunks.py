from hashlib import sha256

from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import Recipe, RecipeIngredient, SourceChunk


CHUNK_SCHEMA_VERSION = 1


def build_recipe_chunks(recipes: list[Recipe]) -> list[SourceChunk]:
    """Build semantic RAG chunks from recipe schemas."""
    chunks: list[SourceChunk] = []
    for recipe in recipes:
        chunks.append(_build_overview_chunk(recipe))
        chunks.append(_build_ingredients_chunk(recipe))
        chunks.extend(_build_step_chunks(recipe))
        chunks.extend(_build_failure_chunks(recipe))
        chunks.extend(_build_substitution_chunks(recipe))
        chunks.extend(_build_safety_chunks(recipe))
    return chunks


def _build_overview_chunk(recipe: Recipe) -> SourceChunk:
    """Build a summary chunk for recipe-level discovery queries."""
    content = "\n".join(
        [
            f"菜谱：{recipe.name}",
            "类型：菜谱概览",
            f"简介：{recipe.description}",
            f"难度：{recipe.difficulty}",
            f"预计耗时：{recipe.time_minutes} 分钟",
            f"新手友好：{'是' if recipe.beginner_friendly else '否'}",
            f"菜系：{recipe.cuisine}",
            f"适合季节：{_join_text(recipe.seasons)}",
        ]
    )
    return _chunk(
        recipe=recipe,
        chunk_type=ChunkType.OVERVIEW,
        content=content,
        chunk_key="overview",
    )


def _build_ingredients_chunk(recipe: Recipe) -> SourceChunk:
    """Build an ingredient chunk for matching available or missing ingredients."""
    required = [item for item in recipe.ingredients if item.required]
    optional = [item for item in recipe.ingredients if not item.required]
    content = "\n".join(
        [
            f"菜谱：{recipe.name}",
            "类型：食材清单",
            f"必需食材：{_format_ingredients(required)}",
            f"可选食材：{_format_ingredients(optional) if optional else '无'}",
            f"相关食材：{_join_text(_ingredient_names(recipe))}",
        ]
    )
    return _chunk(
        recipe=recipe,
        chunk_type=ChunkType.INGREDIENTS,
        content=content,
        chunk_key="ingredients",
    )


def _build_step_chunks(recipe: Recipe) -> list[SourceChunk]:
    """Build one chunk for each ordered cooking step."""
    chunks: list[SourceChunk] = []
    for step in recipe.steps:
        lines = [
            f"菜谱：{recipe.name}",
            "类型：制作步骤",
            f"步骤 {step.order}：{step.content}",
        ]
        if step.beginner_tip:
            lines.append(f"新手提示：{step.beginner_tip}")
        if step.risk_tip:
            lines.append(f"风险提示：{step.risk_tip}")
        lines.append(f"相关食材：{_join_text(_ingredient_names(recipe))}")
        chunks.append(
            _chunk(
                recipe=recipe,
                chunk_type=ChunkType.STEP,
                content="\n".join(lines),
                chunk_key=f"step:{step.order}",
                extra_metadata={"step_order": step.order},
            )
        )
    return chunks


def _build_failure_chunks(recipe: Recipe) -> list[SourceChunk]:
    """Build one chunk for each common failure reason or fix."""
    return [
        _chunk(
            recipe=recipe,
            chunk_type=ChunkType.FAILURE,
            content="\n".join(
                [
                    f"菜谱：{recipe.name}",
                    "类型：失败排查",
                    f"常见问题 {index}：{failure}",
                    f"相关食材：{_join_text(_ingredient_names(recipe))}",
                ]
            ),
            chunk_key=f"failure:{index}",
            extra_metadata={"failure_order": index},
        )
        for index, failure in enumerate(recipe.common_failures, start=1)
    ]


def _build_substitution_chunks(recipe: Recipe) -> list[SourceChunk]:
    """Build one chunk for each ingredient substitution."""
    chunks: list[SourceChunk] = []
    for index, (ingredient, substitution) in enumerate(recipe.substitutions.items(), start=1):
        chunks.append(
            _chunk(
                recipe=recipe,
                chunk_type=ChunkType.SUBSTITUTION,
                content="\n".join(
                    [
                        f"菜谱：{recipe.name}",
                        "类型：食材替代",
                        f"原食材：{ingredient}",
                        f"替代方案：{substitution}",
                    ]
                ),
                chunk_key=f"substitution:{index}",
                extra_metadata={
                    "substitution_order": index,
                    "ingredient": ingredient,
                },
            )
        )
    return chunks


def _build_safety_chunks(recipe: Recipe) -> list[SourceChunk]:
    """Build one chunk for each safety note."""
    return [
        _chunk(
            recipe=recipe,
            chunk_type=ChunkType.SAFETY,
            content="\n".join(
                [
                    f"菜谱：{recipe.name}",
                    "类型：安全提醒",
                    f"安全事项 {index}：{note}",
                    f"相关食材：{_join_text(_ingredient_names(recipe))}",
                ]
            ),
            chunk_key=f"safety:{index}",
            extra_metadata={"safety_order": index},
        )
        for index, note in enumerate(recipe.safety_notes, start=1)
    ]


def _chunk(
    *,
    recipe: Recipe,
    chunk_type: ChunkType,
    content: str,
    chunk_key: str,
    extra_metadata: dict[str, object] | None = None,
) -> SourceChunk:
    """Create a SourceChunk with stable metadata for vector storage."""
    chunk_id = f"recipe:{recipe.id}:{chunk_key}:v{CHUNK_SCHEMA_VERSION}"
    metadata: dict[str, object] = {
        "chunk_id": chunk_id,
        "content_hash": _hash_text(content),
        "schema_version": CHUNK_SCHEMA_VERSION,
        "difficulty": recipe.difficulty,
        "beginner_friendly": recipe.beginner_friendly,
        "time_minutes": recipe.time_minutes,
        "cuisine": recipe.cuisine,
        "seasons": recipe.seasons,
        "ingredients": _ingredient_names(recipe),
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return SourceChunk(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        chunk_type=chunk_type,
        content=content,
        metadata=metadata,
    )


def _format_ingredients(ingredients: list[RecipeIngredient]) -> str:
    """Format ingredient names and amounts into readable text."""
    if not ingredients:
        return "无"
    return "、".join(
        f"{item.ingredient}（{item.amount}）" if item.amount else item.ingredient
        for item in ingredients
    )


def _ingredient_names(recipe: Recipe) -> list[str]:
    """Return ingredient names from a recipe."""
    return [item.ingredient for item in recipe.ingredients]


def _join_text(values: list[str]) -> str:
    """Join a list of values for chunk text."""
    return "、".join(values) if values else "无"


def _hash_text(text: str) -> str:
    """Return a stable hash used for incremental chunk indexing."""
    return sha256(text.encode("utf-8")).hexdigest()
