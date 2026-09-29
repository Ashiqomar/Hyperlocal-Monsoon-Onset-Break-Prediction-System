"""Decision layer: turns twin scenarios into an expected-loss table per action.

For each action a and scenario s, L(a, s) is the per-hectare loss vs a normal
season if s happens after choosing a ("cost if wrong"). Expected loss is
sum_s P(s) * L(a, s), and the recommendation is the action with the lowest.

Two scores are reported and deliberately kept apart:
- recommendation.confidence: how strongly *this forecast* supports the action.
- crop_suitability.score: long-term agronomic fit of the crop to the panchayat,
  from soil, irrigation and climatology. It never looks at the forecast.
"""

from app.data.crop_suitability import IRRIGATION_DEFICIT_COVER, SOIL_FIT, WATER_RANGE_MM
from app.models import Block
from app.schemas.decision import (
    Action,
    DecisionStatus,
    Escalation,
    EscalationReason,
    ActionLoss,
    CropSuitability,
    DecisionResponse,
    Recommendation,
    ScenarioLoss,
)
from app.schemas.geo import IrrigationType, SoilType
from app.schemas.twin import Scenario, TwinResponse
from app.services.review import review_id

N, D, W, F = Scenario.NORMAL, Scenario.DRY, Scenario.WET, Scenario.FALSE_ONSET
COMMIT_ACTIONS = (Action.SOW, Action.WAIT, Action.SPRAY)

# --- Decision coefficients (illustrative) ---------------------------------
# Yield lost to sowing ~1-2 weeks late, as a share of normal-season revenue.
WAIT_DELAY_LOSS = 0.10
# Waiting avoids failed germination in a dry spell (part of a dry season's loss)
# and all of a false onset's re-sowing losses, but does little against a wet
# season, which the later-sown crop still faces.
WAIT_DRY_MITIGATION = 0.4
WAIT_WET_MITIGATION = 0.1
# One prophylactic fungicide + insecticide round, per ha.
SPRAY_COST_INR = 2_500
# Share of wet-season losses (pests, fungal disease) a timely spray prevents.
SPRAY_WET_MITIGATION = 0.4
# REASSESS = hold for one week and re-run on the next forecast.
REASSESS_DELAY_LOSS = 0.04
# Chance the next forecast identifies the right action; otherwise you fall
# back on today's best commitment.
REASSESS_ACCURACY = 0.7

MONSOON_DAYS = 122  # Jun-Sep

# --- Escalation to officer review ------------------------------------------
# Same cut-off the farmer screen calls "not very sure".
LOW_CONFIDENCE = 0.4
# High impact: a scenario with at least this probability in which the
# recommended action would lose at least this share of a normal season's profit.
HIGH_IMPACT_MIN_PROBABILITY = 0.2
HIGH_IMPACT_PROFIT_SHARE = 1.0

ACTION_TEXT: dict[Action, str] = {
    Action.SOW: "Sow now",
    Action.WAIT: "Delay sowing 1-2 weeks until rains are established",
    Action.SPRAY: "Sow and apply protective spray against wet-spell pests and disease",
    Action.REASSESS: "Hold for one week and decide on the next forecast",
}


def loss_matrix(twin: TwinResponse) -> dict[Action, dict[Scenario, float]]:
    """Cost-if-wrong per action and scenario, built from the twin's scenario economics."""
    econ = twin.economics
    normal_revenue = econ.normal_yield_q_per_ha * econ.price_inr_per_q
    baseline = twin.summary.baseline_profit_inr_per_ha
    # What sowing now loses vs a normal season in each scenario (0 for Normal).
    shortfall = {s.scenario: max(0.0, baseline - s.expected_profit_inr_per_ha) for s in twin.scenarios}
    delay = WAIT_DELAY_LOSS * normal_revenue

    L: dict[Action, dict[Scenario, float]] = {
        Action.SOW: dict(shortfall),
        Action.SPRAY: {
            s: shortfall[s] * (1 - SPRAY_WET_MITIGATION if s == W else 1) + SPRAY_COST_INR for s in Scenario
        },
        Action.WAIT: {
            N: delay,
            D: delay + (1 - WAIT_DRY_MITIGATION) * shortfall[D],
            W: delay + (1 - WAIT_WET_MITIGATION) * shortfall[W],
            F: delay,
        },
    }

    probs = scenario_probabilities(twin)
    best_commit = min(COMMIT_ACTIONS, key=lambda a: _expected(L[a], probs))
    L[Action.REASSESS] = {
        s: REASSESS_DELAY_LOSS * normal_revenue
        + REASSESS_ACCURACY * min(L[a][s] for a in COMMIT_ACTIONS)
        + (1 - REASSESS_ACCURACY) * L[best_commit][s]
        for s in Scenario
    }
    return L


def scenario_probabilities(twin: TwinResponse) -> dict[Scenario, float]:
    return {s.scenario: s.probability for s in twin.scenarios}


def _expected(losses: dict[Scenario, float], probs: dict[Scenario, float]) -> float:
    return sum(probs[s] * losses[s] for s in Scenario)


def _no_regret_probability(action: Action, L: dict[Action, dict[Scenario, float]], probs: dict[Scenario, float]) -> float:
    """Probability that `action` turns out to be the best commitment once the scenario is known."""
    return sum(probs[s] for s in Scenario if L[action][s] <= min(L[a][s] for a in COMMIT_ACTIONS))


def recommend(
    L: dict[Action, dict[Scenario, float]], probs: dict[Scenario, float], expected: dict[Action, float]
) -> Recommendation:
    action = min(Action, key=expected.__getitem__)
    top_risk = max((s for s in Scenario if s != N), key=probs.__getitem__)
    risk_text = f"main risk is {top_risk.value.replace('_', ' ')} ({probs[top_risk]:.0%})"

    if action == Action.REASSESS:
        best_commit = min(COMMIT_ACTIONS, key=expected.__getitem__)
        confidence = 1 - _no_regret_probability(best_commit, L, probs)
        basis = f"Share of forecast outcomes in which committing now (to {best_commit}) would be the wrong call"
        rationale = (
            f"No commitment is clearly best: {best_commit} is the best option today but is right in only "
            f"{1 - confidence:.0%} of outcomes; {risk_text}. Waiting a week for the next forecast has "
            f"the lowest expected loss."
        )
    else:
        confidence = _no_regret_probability(action, L, probs)
        basis = "Share of forecast outcomes in which this action turns out to be the best commitment"
        rationale = f"{action} has the lowest expected loss (₹{expected[action]:,.0f}/ha); {risk_text}."

    return Recommendation(
        action=action, confidence=round(confidence, 2), confidence_basis=basis, rationale=rationale
    )


def crop_suitability(twin: TwinResponse, block: Block) -> CropSuitability:
    crop = twin.economics.crop
    soil = SoilType(twin.panchayat.soil_type)
    irrigation = IrrigationType(twin.panchayat.irrigation_type)

    soil_fit = SOIL_FIT[crop][soil]

    season_mm = MONSOON_DAYS * block.rain_day_prob * block.rain_day_mean_mm
    lo, hi = WATER_RANGE_MM[crop]
    if season_mm < lo:
        # Linear from 0 at 40% of the lower bound up to 1 at the lower bound;
        # irrigation makes up part of the deficit.
        rain_fit = max(0.0, (season_mm - 0.4 * lo) / (0.6 * lo))
        water_fit = rain_fit + (1 - rain_fit) * IRRIGATION_DEFICIT_COVER[irrigation]
    elif season_mm > hi:
        # Excess rain (waterlogging, disease); irrigation doesn't help.
        water_fit = max(0.1, 1 - (season_mm - hi) / hi)
    else:
        water_fit = 1.0

    score = round(100 * (0.5 * soil_fit + 0.5 * water_fit))
    rating = "high" if score >= 70 else "moderate" if score >= 40 else "low"
    return CropSuitability(
        score=score,
        rating=rating,
        soil_score=round(100 * soil_fit),
        water_score=round(100 * water_fit),
        soil_type=soil,
        irrigation_type=irrigation,
        season_normal_rainfall_mm=round(season_mm),
        crop_water_range_mm=(lo, hi),
    )


def build_decision(twin: TwinResponse, block: Block) -> DecisionResponse:
    L = loss_matrix(twin)
    probs = scenario_probabilities(twin)
    expected = {a: _expected(L[a], probs) for a in Action}
    ranked = sorted(Action, key=expected.__getitem__)

    table = [
        ActionLoss(
            action=a,
            description=ACTION_TEXT[a],
            expected_loss_inr_per_ha=round(expected[a]),
            rank=ranked.index(a) + 1,
            by_scenario=[
                ScenarioLoss(
                    scenario=s,
                    probability=probs[s],
                    cost_if_wrong_inr_per_ha=round(L[a][s]),
                    expected_loss_inr_per_ha=round(probs[s] * L[a][s]),
                )
                for s in Scenario
            ],
        )
        for a in Action
    ]

    recommendation = recommend(L, probs, expected)
    rec_row = next(r for r in table if r.action == recommendation.action)
    reasons = escalation_reasons(recommendation, rec_row, twin.summary.baseline_profit_inr_per_ha)

    return DecisionResponse(
        panchayat=twin.panchayat,
        crop=twin.economics.crop,
        issued_on=twin.issued_on,
        recommendation=recommendation,
        crop_suitability=crop_suitability(twin, block),
        escalation=Escalation(
            needs_officer_review=bool(reasons),
            reasons=reasons,
            status=DecisionStatus.NEEDS_OFFICER_REVIEW if reasons else DecisionStatus.AUTO_APPROVED,
            final_action=recommendation.action,
            review_id=review_id(twin.panchayat.id, twin.economics.crop, twin.issued_on) if reasons else None,
        ),
        expected_loss_table=table,
    )


def escalation_reasons(rec: Recommendation, rec_row: ActionLoss, baseline_profit: float) -> list[EscalationReason]:
    """Rules that send a decision to an officer before it reaches farmers."""
    reasons: list[EscalationReason] = []

    if rec.confidence < LOW_CONFIDENCE:
        reasons.append(
            EscalationReason(
                code="low_confidence",
                message=f"Confidence {rec.confidence:.0%} is below {LOW_CONFIDENCE:.0%}",
            )
        )

    # Worst loss among scenarios that are reasonably likely.
    likely = [s for s in rec_row.by_scenario if s.probability >= HIGH_IMPACT_MIN_PROBABILITY]
    worst = max(likely, key=lambda s: s.cost_if_wrong_inr_per_ha, default=None)
    if worst and baseline_profit > 0 and worst.cost_if_wrong_inr_per_ha >= HIGH_IMPACT_PROFIT_SHARE * baseline_profit:
        reasons.append(
            EscalationReason(
                code="high_impact_cost",
                message=(
                    f"{worst.probability:.0%} chance ({worst.scenario.value.replace('_', ' ')}) of losing "
                    f"₹{worst.cost_if_wrong_inr_per_ha:,}/ha, at least a normal season's profit "
                    f"(₹{round(baseline_profit):,}/ha)"
                ),
            )
        )
    return reasons
