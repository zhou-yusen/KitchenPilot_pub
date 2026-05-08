from sqlalchemy.orm import Session

from kitchenpilot.db.models import (
    IngredientORM,
    RecipeFailureORM,
    RecipeIngredientORM,
    RecipeORM,
    RecipeSafetyNoteORM,
    RecipeSourceORM,
    RecipeStepORM,
    RecipeSubstitutionORM,
)
from kitchenpilot.db.session import SessionLocal, create_all
from kitchenpilot.seed.recipe_dataset import load_recipe_dataset_entries
from kitchenpilot.schemas.recipe import Recipe


def seed_sqlite() -> None:
    """Create SQLite tables and upsert the initial recipe dataset."""
    create_all()
    entries = load_recipe_dataset_entries()
    with SessionLocal() as session:
        for entry in entries:
            _upsert_recipe(session, Recipe.model_validate(entry), entry)
        session.commit()


def _upsert_recipe(session: Session, recipe: Recipe, entry: dict) -> None:
    """Insert or update one recipe plus its ingredient links and ordered steps."""
    recipe_orm = session.get(RecipeORM, recipe.id)
    if recipe_orm is None:
        recipe_orm = RecipeORM(id=recipe.id, name=recipe.name, description=recipe.description)
        session.add(recipe_orm)

    recipe_orm.name = recipe.name
    recipe_orm.description = recipe.description
    recipe_orm.difficulty = recipe.difficulty
    recipe_orm.time_minutes = recipe.time_minutes
    recipe_orm.beginner_friendly = recipe.beginner_friendly
    recipe_orm.cuisine = recipe.cuisine
    recipe_orm.seasons = ",".join(recipe.seasons)

    existing_ingredients = {
        item.ingredient.name: item
        for item in session.query(RecipeIngredientORM)
        .join(IngredientORM)
        .filter(RecipeIngredientORM.recipe_id == recipe.id)
        .all()
    }
    expected_ingredient_names = {item.ingredient for item in recipe.ingredients}

    for stale_name, stale_link in existing_ingredients.items():
        if stale_name not in expected_ingredient_names:
            session.delete(stale_link)

    for item in recipe.ingredients:
        ingredient = (
            session.query(IngredientORM).filter(IngredientORM.name == item.ingredient).one_or_none()
        )
        if ingredient is None:
            ingredient = IngredientORM(name=item.ingredient)
            session.add(ingredient)
            session.flush()
        exists = (
            session.query(RecipeIngredientORM)
            .filter(
                RecipeIngredientORM.recipe_id == recipe.id,
                RecipeIngredientORM.ingredient_id == ingredient.id,
            )
            .one_or_none()
        )
        if exists is None:
            session.add(
                RecipeIngredientORM(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    amount=item.amount,
                    required=item.required,
                )
            )
        else:
            exists.amount = item.amount
            exists.required = item.required

    existing_steps = {
        step.step_order: step
        for step in session.query(RecipeStepORM).filter(RecipeStepORM.recipe_id == recipe.id).all()
    }
    expected_step_orders = {step.order for step in recipe.steps}
    for stale_order, stale_step in existing_steps.items():
        if stale_order not in expected_step_orders:
            session.delete(stale_step)

    for step in recipe.steps:
        exists = (
            session.query(RecipeStepORM)
            .filter(RecipeStepORM.recipe_id == recipe.id, RecipeStepORM.step_order == step.order)
            .one_or_none()
        )
        if exists is None:
            session.add(
                RecipeStepORM(
                    recipe_id=recipe.id,
                    step_order=step.order,
                    content=step.content,
                    beginner_tip=step.beginner_tip or "",
                    risk_tip=step.risk_tip or "",
                )
            )
        else:
            exists.content = step.content
            exists.beginner_tip = step.beginner_tip or ""
            exists.risk_tip = step.risk_tip or ""

    _replace_failures(session, recipe)
    _replace_substitutions(session, recipe)
    _replace_safety_notes(session, recipe)
    _replace_sources(session, recipe.id, entry.get("source_urls", []))


def _replace_failures(session: Session, recipe: Recipe) -> None:
    """Replace stored common failure points for one recipe."""
    session.query(RecipeFailureORM).filter(RecipeFailureORM.recipe_id == recipe.id).delete()
    for index, content in enumerate(recipe.common_failures, start=1):
        session.add(
            RecipeFailureORM(recipe_id=recipe.id, failure_order=index, content=content)
        )


def _replace_substitutions(session: Session, recipe: Recipe) -> None:
    """Replace stored ingredient substitution notes for one recipe."""
    session.query(RecipeSubstitutionORM).filter(
        RecipeSubstitutionORM.recipe_id == recipe.id
    ).delete()
    for ingredient_name, substitute_text in recipe.substitutions.items():
        session.add(
            RecipeSubstitutionORM(
                recipe_id=recipe.id,
                ingredient_name=ingredient_name,
                substitute_text=substitute_text,
            )
        )


def _replace_safety_notes(session: Session, recipe: Recipe) -> None:
    """Replace stored safety notes for one recipe."""
    session.query(RecipeSafetyNoteORM).filter(
        RecipeSafetyNoteORM.recipe_id == recipe.id
    ).delete()
    for index, content in enumerate(recipe.safety_notes, start=1):
        session.add(RecipeSafetyNoteORM(recipe_id=recipe.id, note_order=index, content=content))


def _replace_sources(session: Session, recipe_id: int, source_urls: list[str]) -> None:
    """Replace stored source URLs for one recipe."""
    session.query(RecipeSourceORM).filter(RecipeSourceORM.recipe_id == recipe_id).delete()
    for index, url in enumerate(source_urls, start=1):
        session.add(RecipeSourceORM(recipe_id=recipe_id, source_order=index, url=url))


if __name__ == "__main__":
    seed_sqlite()
