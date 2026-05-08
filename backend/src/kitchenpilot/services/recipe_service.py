from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from kitchenpilot.db.models import RecipeORM
from kitchenpilot.db.session import SessionLocal
from kitchenpilot.schemas.recipe import Recipe
from kitchenpilot.services.mock_data import RECIPES


class RecipeService:
    """Read recipes from SQLite, falling back to mock data when SQLite is unavailable."""

    def __init__(self, db: Session | None = None) -> None:
        """Optionally accept a caller-managed database session for tests or API dependencies."""
        self._db = db

    def list_recipes(self) -> list[Recipe]:
        """Return all recipes, preferring SQLite rows over bundled mock recipes."""
        recipes = self._run_with_session(self._list_recipes_from_db)
        return recipes or RECIPES

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        """Return a single recipe by ID from SQLite, then fallback mock data."""
        recipe = self._run_with_session(lambda session: self._get_recipe_from_db(session, recipe_id))
        if recipe is not None:
            return recipe
        return next((recipe for recipe in RECIPES if recipe.id == recipe_id), None)

    def find_by_name(self, query: str) -> Recipe | None:
        """Find the first recipe whose name appears in a free-form query string."""
        recipe = self._run_with_session(lambda session: self._find_by_name_from_db(session, query))
        if recipe is not None:
            return recipe
        return next((recipe for recipe in RECIPES if recipe.name in query), None)

    def find_by_ingredients(self, ingredients: list[str]) -> list[Recipe]:
        """Return recipes that share at least one ingredient with the provided ingredient list."""
        normalized = set(ingredients)
        candidates: list[Recipe] = []
        for recipe in self.list_recipes():
            recipe_ingredients = {item.ingredient for item in recipe.ingredients}
            if normalized & recipe_ingredients:
                candidates.append(recipe)
        return candidates

    def _run_with_session(self, operation):
        """Run a database operation with either the injected session or a short-lived session."""
        if self._db is not None:
            try:
                return operation(self._db)
            except SQLAlchemyError:
                return None

        try:
            with SessionLocal() as session:
                return operation(session)
        except SQLAlchemyError:
            return None

    def _list_recipes_from_db(self, session: Session) -> list[Recipe]:
        """Load every recipe from SQLite with ingredients and steps eagerly loaded."""
        rows = (
            session.query(RecipeORM)
            .options(
                selectinload(RecipeORM.ingredients),
                selectinload(RecipeORM.steps),
            )
            .order_by(RecipeORM.id)
            .all()
        )
        return [self._to_schema(row) for row in rows]

    def _get_recipe_from_db(self, session: Session, recipe_id: int) -> Recipe | None:
        """Load one recipe from SQLite by primary key."""
        row = (
            session.query(RecipeORM)
            .options(
                selectinload(RecipeORM.ingredients),
                selectinload(RecipeORM.steps),
            )
            .filter(RecipeORM.id == recipe_id)
            .one_or_none()
        )
        return self._to_schema(row) if row is not None else None

    def _find_by_name_from_db(self, session: Session, query: str) -> Recipe | None:
        """Scan SQLite recipes for a name contained in the user query."""
        rows = (
            session.query(RecipeORM)
            .options(
                selectinload(RecipeORM.ingredients),
                selectinload(RecipeORM.steps),
            )
            .order_by(RecipeORM.id)
            .all()
        )
        for row in rows:
            if row.name in query:
                return self._to_schema(row)
        return None

    def _to_schema(self, row: RecipeORM) -> Recipe:
        """Convert a SQLAlchemy recipe row into the public Pydantic Recipe schema."""
        return Recipe.model_validate(
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "difficulty": row.difficulty,
                "time_minutes": row.time_minutes,
                "beginner_friendly": row.beginner_friendly,
                "cuisine": row.cuisine,
                "seasons": [item for item in row.seasons.split(",") if item],
                "ingredients": [
                    {
                        "ingredient": item.ingredient.name,
                        "amount": item.amount,
                        "required": item.required,
                    }
                    for item in sorted(row.ingredients, key=lambda item: item.id)
                ],
                "steps": [
                    {
                        "order": step.step_order,
                        "content": step.content,
                        "beginner_tip": step.beginner_tip or None,
                        "risk_tip": step.risk_tip or None,
                    }
                    for step in sorted(row.steps, key=lambda step: step.step_order)
                ],
                "common_failures": [],
                "substitutions": {},
                "safety_notes": [],
            }
        )
