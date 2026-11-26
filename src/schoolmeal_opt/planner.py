"""Home-Grown School Feeding (HGSF) Two-Phase Simplex LP nutrition & local procurement optimizer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class FoodCommodity:
    """Locally sourced East African school-feeding commodity (nutrients per 100g edible dry/fresh)."""

    key: str
    display_name: str
    price_usd_per_kg: float
    kcal_100g: float
    protein_g_100g: float
    iron_mg_100g: float
    vit_a_ug_rae_100g: float
    zinc_mg_100g: float
    min_grams_per_meal: float = 0.0
    max_grams_per_meal: float = 200.0


LOCAL_SCHOOL_FOODS: tuple[FoodCommodity, ...] = (
    FoodCommodity("maize_flour", "Fortified Maize Flour (Posho)", 0.52, 362.0, 8.8, 2.7, 0.0, 1.8, 60.0, 160.0),
    FoodCommodity("biofortified_beans", "High-Iron Beans (NARO)", 1.05, 335.0, 21.5, 8.2, 0.0, 3.2, 30.0, 90.0),
    FoodCommodity("ofsp", "Orange-Fleshed Sweet Potato", 0.40, 86.0, 1.6, 0.7, 709.0, 0.3, 0.0, 120.0),
    FoodCommodity("mukene_silverfish", "Dried Mukene / Omena Fish", 2.40, 320.0, 62.0, 6.5, 40.0, 9.5, 0.0, 25.0),
    FoodCommodity("groundnut_paste", "Groundnut (Peanut) Paste", 1.75, 588.0, 25.0, 2.1, 0.0, 3.3, 0.0, 35.0),
    FoodCommodity("amaranth_greens", "Fresh Amaranth / Sukuma Greens", 0.35, 34.0, 3.2, 3.5, 290.0, 0.9, 15.0, 80.0),
    FoodCommodity("fortified_oil", "Vitamin-A Fortified Vegetable Oil", 1.90, 884.0, 0.0, 0.0, 600.0, 0.0, 5.0, 20.0),
)


@dataclass(frozen=True)
class MealTarget:
    """FAO/WFP single hot school lunch nutritional target (~35-40% of child 6-12y RDA)."""

    min_kcal: float = 700.0
    max_kcal: float = 950.0
    min_protein_g: float = 20.0
    min_iron_mg: float = 4.5
    min_vit_a_ug_rae: float = 200.0
    min_zinc_mg: float = 3.0


PRIMARY_SCHOOL_TARGETS = MealTarget()


def _solve_simplex_min(
    c: list[float],
    a_le: list[list[float]],
    b_le: list[float],
    a_ge: list[list[float]],
    b_ge: list[float],
) -> list[float] | None:
    """Self-contained pure-Python Two-Phase Simplex LP solver (min c^T x, x >= 0)."""
    n_vars = len(c)
    m_le = len(b_le)
    m_ge = len(b_ge)
    m = m_le + m_ge
    n_slack = m_le + m_ge
    n_art = m_ge
    total_cols = n_vars + n_slack + n_art

    # Build tableau: rows 0..m-1 are constraints, row m is objective
    tab: list[list[float]] = [[0.0] * (total_cols + 1) for _ in range(m + 1)]
    basis: list[int] = []

    for i in range(m_le):
        for j in range(n_vars):
            tab[i][j] = a_le[i][j]
        s_col = n_vars + i
        tab[i][s_col] = 1.0
        tab[i][-1] = b_le[i]
        basis.append(s_col)

    for idx in range(m_ge):
        r = m_le + idx
        for j in range(n_vars):
            tab[r][j] = a_ge[idx][j]
        surplus_col = n_vars + m_le + idx
        art_col = n_vars + n_slack + idx
        tab[r][surplus_col] = -1.0
        tab[r][art_col] = 1.0
        tab[r][-1] = b_ge[idx]
        basis.append(art_col)

    def _pivot(piv_r: int, piv_c: int) -> None:
        piv_val = tab[piv_r][piv_c]
        for j in range(total_cols + 1):
            tab[piv_r][j] /= piv_val
        for r in range(m + 1):
            if r == piv_r:
                continue
            fac = tab[r][piv_c]
            if abs(fac) > 1e-12:
                for j in range(total_cols + 1):
                    tab[r][j] -= fac * tab[piv_r][j]
        basis[piv_r] = piv_c

    def _run_simplex(allowed_cols: int) -> bool:
        for _ in range(500):
            # Bland's rule: pick smallest index with negative reduced cost
            enter = -1
            for j in range(allowed_cols):
                if tab[m][j] < -1e-9:
                    enter = j
                    break
            if enter == -1:
                return True
            leave = -1
            best_ratio = float("inf")
            for r in range(m):
                a_rc = tab[r][enter]
                if a_rc > 1e-9:
                    ratio = tab[r][-1] / a_rc
                    if ratio < best_ratio - 1e-12 or (abs(ratio - best_ratio) <= 1e-12 and basis[r] < basis[leave]):
                        best_ratio = ratio
                        leave = r
            if leave == -1:
                return False
            _pivot(leave, enter)
        return False

    # Phase 1: minimize sum of artificial variables
    if n_art > 0:
        for j in range(n_vars + n_slack, total_cols):
            tab[m][j] = 1.0
        for r in range(m_le, m):
            for j in range(total_cols + 1):
                tab[m][j] -= tab[r][j]
        if not _run_simplex(total_cols):
            return None
        if abs(tab[m][-1]) > 1e-5:
            return None  # Infeasible

    # Phase 2: original objective over non-artificial columns
    tab[m] = [0.0] * (total_cols + 1)
    for j in range(n_vars):
        tab[m][j] = c[j]
    for r, b_col in enumerate(basis):
        if b_col < n_vars and abs(tab[m][b_col]) > 1e-12:
            fac = tab[m][b_col]
            for j in range(total_cols + 1):
                tab[m][j] -= fac * tab[r][j]

    if not _run_simplex(n_vars + n_slack):
        return None

    sol = [0.0] * n_vars
    for r, b_col in enumerate(basis):
        if b_col < n_vars:
            sol[b_col] = max(0.0, tab[r][-1])
    return sol


@dataclass(frozen=True)
class SchoolFeedingPlan:
    """Optimal least-cost school meal ration, nutrient audit & smallholder term procurement."""

    feasible: bool
    students: int
    school_days: int
    ration_grams_per_student: dict[str, float]
    cost_usd_per_student_meal: float
    total_term_budget_usd: float
    kcal_per_meal: float
    protein_g_per_meal: float
    iron_mg_per_meal: float
    vit_a_ug_per_meal: float
    zinc_mg_per_meal: float
    term_procurement_kg_by_commodity: dict[str, float]
    institutional_firewood_kg_term: float
    improved_rocket_stove_firewood_saved_kg: float


def optimize_school_meal(
    *,
    students: int,
    school_days: int = 65,  # One school term (~13 weeks)
    foods: Sequence[FoodCommodity] = LOCAL_SCHOOL_FOODS,
    target: MealTarget = PRIMARY_SCHOOL_TARGETS,
) -> SchoolFeedingPlan:
    """Find least-cost local Home-Grown School Feeding meal meeting FAO/WFP RDA minimums."""
    if students <= 0 or school_days <= 0:
        raise ValueError("students and school_days must be strictly positive")

    # Decision variables x_j = units of 100g of commodity j per student meal
    n = len(foods)
    c = [f.price_usd_per_kg * 0.1 for f in foods]  # USD per 100g

    a_le: list[list[float]] = []
    b_le: list[float] = []
    a_ge: list[list[float]] = []
    b_ge: list[float] = []

    # Nutrient constraints
    a_ge.append([f.kcal_100g for f in foods])
    b_ge.append(target.min_kcal)
    a_le.append([f.kcal_100g for f in foods])
    b_le.append(target.max_kcal)

    a_ge.append([f.protein_g_100g for f in foods])
    b_ge.append(target.min_protein_g)
    a_ge.append([f.iron_mg_100g for f in foods])
    b_ge.append(target.min_iron_mg)
    a_ge.append([f.vit_a_ug_rae_100g for f in foods])
    b_ge.append(target.min_vit_a_ug_rae)
    a_ge.append([f.zinc_mg_100g for f in foods])
    b_ge.append(target.min_zinc_mg)

    # Palatability & portion bounds per commodity
    for j, f in enumerate(foods):
        if f.min_grams_per_meal > 0.0:
            row = [0.0] * n
            row[j] = 1.0
            a_ge.append(row)
            b_ge.append(f.min_grams_per_meal / 100.0)
        row_max = [0.0] * n
        row_max[j] = 1.0
        a_le.append(row_max)
        b_le.append(f.max_grams_per_meal / 100.0)

    sol = _solve_simplex_min(c, a_le, b_le, a_ge, b_ge)
    if sol is None:
        return SchoolFeedingPlan(
            feasible=False,
            students=students,
            school_days=school_days,
            ration_grams_per_student={},
            cost_usd_per_student_meal=0.0,
            total_term_budget_usd=0.0,
            kcal_per_meal=0.0,
            protein_g_per_meal=0.0,
            iron_mg_per_meal=0.0,
            vit_a_ug_per_meal=0.0,
            zinc_mg_per_meal=0.0,
            term_procurement_kg_by_commodity={},
            institutional_firewood_kg_term=0.0,
            improved_rocket_stove_firewood_saved_kg=0.0,
        )

    grams_map = {foods[j].key: round(sol[j] * 100.0, 1) for j in range(n) if sol[j] * 100.0 >= 0.5}
    cost_meal = sum(sol[j] * c[j] for j in range(n))
    total_meals = students * school_days
    proc_kg = {k: round((g * total_meals) / 1000.0, 1) for k, g in grams_map.items()}

    kcal = sum(sol[j] * foods[j].kcal_100g for j in range(n))
    prot = sum(sol[j] * foods[j].protein_g_100g for j in range(n))
    iron = sum(sol[j] * foods[j].iron_mg_100g for j in range(n))
    vita = sum(sol[j] * foods[j].vit_a_ug_rae_100g for j in range(n))
    zinc = sum(sol[j] * foods[j].zinc_mg_100g for j in range(n))

    # Institutional kitchen firewood: ~0.40 kg/meal on traditional three-stone vs ~0.18 kg on rocket stove
    trad_wood = total_meals * 0.40
    saved_wood = total_meals * (0.40 - 0.18)

    return SchoolFeedingPlan(
        feasible=True,
        students=students,
        school_days=school_days,
        ration_grams_per_student=grams_map,
        cost_usd_per_student_meal=round(cost_meal, 4),
        total_term_budget_usd=round(cost_meal * total_meals, 2),
        kcal_per_meal=round(kcal, 1),
        protein_g_per_meal=round(prot, 1),
        iron_mg_per_meal=round(iron, 2),
        vit_a_ug_per_meal=round(vita, 1),
        zinc_mg_per_meal=round(zinc, 2),
        term_procurement_kg_by_commodity=proc_kg,
        institutional_firewood_kg_term=round(trad_wood, 1),
        improved_rocket_stove_firewood_saved_kg=round(saved_wood, 1),
    )
