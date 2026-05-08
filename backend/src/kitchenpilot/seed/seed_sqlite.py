from sqlalchemy.orm import Session

from kitchenpilot.db.models import IngredientORM, RecipeIngredientORM, RecipeORM, RecipeStepORM
from kitchenpilot.db.session import SessionLocal, create_all
from kitchenpilot.services.mock_data import RECIPES


def seed_sqlite() -> None:
    create_all()
    with SessionLocal() as session:
        for recipe in RECIPES:
            _upsert_recipe(session, recipe)
        session.commit()


def _upsert_recipe(session: Session, recipe) -> None:
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


if __name__ == "__main__":
    seed_sqlite()

