from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kitchenpilot.db.base import Base


class RecipeORM(Base):
    """SQLAlchemy model for recipe metadata."""
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20), index=True)
    time_minutes: Mapped[int] = mapped_column(Integer)
    beginner_friendly: Mapped[bool] = mapped_column(Boolean, default=True)
    cuisine: Mapped[str] = mapped_column(String(50), default="家常菜")
    seasons: Mapped[str] = mapped_column(String(200), default="")

    ingredients: Mapped[list["RecipeIngredientORM"]] = relationship(back_populates="recipe")
    steps: Mapped[list["RecipeStepORM"]] = relationship(back_populates="recipe")
    failures: Mapped[list["RecipeFailureORM"]] = relationship(back_populates="recipe")
    substitutions: Mapped[list["RecipeSubstitutionORM"]] = relationship(back_populates="recipe")
    safety_notes: Mapped[list["RecipeSafetyNoteORM"]] = relationship(back_populates="recipe")
    sources: Mapped[list["RecipeSourceORM"]] = relationship(back_populates="recipe")


class IngredientORM(Base):
    """SQLAlchemy model for reusable ingredient records."""
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), default="other")
    common_score: Mapped[float] = mapped_column(Float, default=1.0)
    seasons: Mapped[str] = mapped_column(String(200), default="")


class RecipeIngredientORM(Base):
    """SQLAlchemy model linking recipes to ingredients."""
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredients.id"))
    amount: Mapped[str] = mapped_column(String(100), default="")
    required: Mapped[bool] = mapped_column(Boolean, default=True)

    recipe: Mapped[RecipeORM] = relationship(back_populates="ingredients")
    ingredient: Mapped[IngredientORM] = relationship()


class RecipeStepORM(Base):
    """SQLAlchemy model for ordered recipe steps."""
    __tablename__ = "recipe_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    step_order: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    beginner_tip: Mapped[str] = mapped_column(Text, default="")
    risk_tip: Mapped[str] = mapped_column(Text, default="")

    recipe: Mapped[RecipeORM] = relationship(back_populates="steps")


class RecipeFailureORM(Base):
    """SQLAlchemy model for common recipe failure points."""

    __tablename__ = "recipe_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    failure_order: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)

    recipe: Mapped[RecipeORM] = relationship(back_populates="failures")


class RecipeSubstitutionORM(Base):
    """SQLAlchemy model for ingredient substitutions in a recipe."""

    __tablename__ = "recipe_substitutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    ingredient_name: Mapped[str] = mapped_column(String(100))
    substitute_text: Mapped[str] = mapped_column(Text)

    recipe: Mapped[RecipeORM] = relationship(back_populates="substitutions")


class RecipeSafetyNoteORM(Base):
    """SQLAlchemy model for recipe-level safety notes."""

    __tablename__ = "recipe_safety_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    note_order: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)

    recipe: Mapped[RecipeORM] = relationship(back_populates="safety_notes")


class RecipeSourceORM(Base):
    """SQLAlchemy model for source URLs used to prepare seed recipe data."""

    __tablename__ = "recipe_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    source_order: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text)

    recipe: Mapped[RecipeORM] = relationship(back_populates="sources")


class UserCookingHistoryORM(Base):
    """SQLAlchemy model for user cooking history entries."""
    __tablename__ = "user_cooking_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipes.id"))
    rating: Mapped[int] = mapped_column(Integer)
    feedback: Mapped[str] = mapped_column(Text, default="")
    cooked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class QALogORM(Base):
    """SQLAlchemy model for question-answer logs."""
    __tablename__ = "qa_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    question: Mapped[str] = mapped_column(Text)
    retrieved_content: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text)
    check_result: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

