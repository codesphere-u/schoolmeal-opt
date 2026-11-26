"""Home-Grown School Feeding (HGSF) RDA nutrition verifier & Two-Phase Simplex LP meal planner."""

from .planner import (
    LOCAL_SCHOOL_FOODS,
    PRIMARY_SCHOOL_TARGETS,
    FoodCommodity,
    MealTarget,
    SchoolFeedingPlan,
    optimize_school_meal,
)

__all__ = [
    "LOCAL_SCHOOL_FOODS",
    "PRIMARY_SCHOOL_TARGETS",
    "FoodCommodity",
    "MealTarget",
    "SchoolFeedingPlan",
    "optimize_school_meal",
]
__version__ = "0.1.0"
