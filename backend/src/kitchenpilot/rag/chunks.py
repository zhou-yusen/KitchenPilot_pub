from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import Recipe, SourceChunk


def build_recipe_chunks(recipes: list[Recipe]) -> list[SourceChunk]:
    """Build searchable RAG chunks from recipe schemas."""
    chunks: list[SourceChunk] = []
    for recipe in recipes:
        chunks.append(
            SourceChunk(
                recipe_id=recipe.id,
                recipe_name=recipe.name,
                chunk_type=ChunkType.PREP,
                content=f"{recipe.name}的主要食材包括：" + "、".join(
                    item.ingredient for item in recipe.ingredients
                ),
                metadata={
                    "difficulty": recipe.difficulty,
                    "beginner_friendly": recipe.beginner_friendly,
                },
            )
        )

        for step in recipe.steps:
            tip = f" 新手提示：{step.beginner_tip}" if step.beginner_tip else ""
            risk = f" 风险提示：{step.risk_tip}" if step.risk_tip else ""
            chunks.append(
                SourceChunk(
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    chunk_type=ChunkType.STEP,
                    content=f"{recipe.name}步骤{step.order}：{step.content}{tip}{risk}",
                    metadata={"step_order": step.order},
                )
            )

        for failure in recipe.common_failures:
            chunks.append(
                SourceChunk(
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    chunk_type=ChunkType.FAILURE_REASON,
                    content=f"{recipe.name}常见失败点：{failure}",
                )
            )

        for ingredient, substitution in recipe.substitutions.items():
            chunks.append(
                SourceChunk(
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    chunk_type=ChunkType.SUBSTITUTION,
                    content=f"{recipe.name}中{ingredient}的替代方案：{substitution}",
                )
            )

        for note in recipe.safety_notes:
            chunks.append(
                SourceChunk(
                    recipe_id=recipe.id,
                    recipe_name=recipe.name,
                    chunk_type=ChunkType.SAFETY_NOTE,
                    content=f"{recipe.name}安全注意事项：{note}",
                )
            )
    return chunks
