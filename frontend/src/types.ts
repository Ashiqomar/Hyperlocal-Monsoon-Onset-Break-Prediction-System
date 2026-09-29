// Mirrors the backend Pydantic models in backend/app/schemas/. Keep in sync.

export type Crop =
  "soybean" | "cotton" | "tur" | "sugarcane" | "jowar" | "bajra" | "onion" | "grapes" | "paddy" | "nachni";

export const MODELED_CROPS = ["cotton", "soybean", "paddy"] as const satisfies readonly Crop[];

export interface Panchayat {
  id: string;
  name: string;
  block_id: string;
  block_name: string;
  district: string;
  lat: number;
  lon: number;
  soil_type: string;
  irrigation_type: string;
  primary_crop: Crop;
}

// --- /forecast ---
export interface WeeklyForecast {
  week: number;
  lead_days_start: number;
  lead_days_end: number;
  start_date: string;
  end_date: string;
  rainfall_mm: { p10: number; p50: number; p90: number };
  dry_spell_probability: number;
  heavy_rain_probability: number;
}

export interface ForecastResponse {
  panchayat: Panchayat;
  issued_on: string;
  model: string;
  ensemble_members: number;
  synthetic: boolean;
  definitions: {
    dry_day_threshold_mm: number;
    dry_spell_min_days: number;
    heavy_rain_threshold_mm: number;
  };
  weeks: WeeklyForecast[];
}

// --- /twin ---
export type Scenario = "normal" | "dry" | "wet" | "false_onset";

export interface ScenarioOutcome {
  scenario: Scenario;
  label: string;
  description: string;
  probability: number;
  yield_impact_pct: number;
  expected_yield_q_per_ha: number;
  cost_impact_inr_per_ha: number;
  expected_cost_inr_per_ha: number;
  expected_revenue_inr_per_ha: number;
  expected_profit_inr_per_ha: number;
  profit_p10_inr_per_ha: number;
  downside_risk_inr_per_ha: number;
}

export interface TwinResponse {
  panchayat: Panchayat;
  issued_on: string;
  forecast_model: string;
  ensemble_members: number;
  synthetic: boolean;
  economics: {
    crop: Crop;
    normal_yield_q_per_ha: number;
    price_inr_per_q: number;
    base_cost_inr_per_ha: number;
  };
  summary: {
    baseline_profit_inr_per_ha: number;
    expected_profit_inr_per_ha: number;
    expected_change_inr_per_ha: number;
    most_likely_scenario: Scenario;
  };
  scenarios: ScenarioOutcome[];
}

// --- /decision ---
export type Action = "SOW" | "WAIT" | "SPRAY" | "REASSESS";

export interface ActionLoss {
  action: Action;
  description: string;
  expected_loss_inr_per_ha: number;
  rank: number;
  by_scenario: {
    scenario: Scenario;
    probability: number;
    cost_if_wrong_inr_per_ha: number;
    expected_loss_inr_per_ha: number;
  }[];
}

export interface DecisionResponse {
  panchayat: Panchayat;
  crop: Crop;
  issued_on: string;
  synthetic: boolean;
  recommendation: {
    action: Action;
    confidence: number;
    confidence_basis: string;
    rationale: string;
  };
  crop_suitability: {
    score: number;
    rating: "high" | "moderate" | "low";
    soil_score: number;
    water_score: number;
    soil_type: string;
    irrigation_type: string;
    season_normal_rainfall_mm: number;
    crop_water_range_mm: [number, number];
  };
  escalation: Escalation;
  expected_loss_table: ActionLoss[];
}

// --- Escalation / review ---
export type DecisionStatus = "auto_approved" | "needs_officer_review" | "approved" | "overridden";

export interface EscalationReason {
  code: "low_confidence" | "high_impact_cost";
  message: string;
}

export interface OfficerReview {
  status: "approved" | "overridden";
  override_action: Action | null;
  note: string | null;
  reviewed_at: string;
}

export interface Escalation {
  needs_officer_review: boolean;
  reasons: EscalationReason[];
  status: DecisionStatus;
  /** Officer's override if any, else the recommendation. */
  final_action: Action;
  review_id: string | null;
  review: OfficerReview | null;
}

export interface ReviewItem {
  id: string;
  panchayat: Panchayat;
  crop: Crop;
  issued_on: string;
  recommended_action: Action;
  confidence: number;
  expected_loss_inr_per_ha: number;
  reasons: EscalationReason[];
  status: DecisionStatus;
  final_action: Action;
  review: OfficerReview | null;
}

export interface DecisionSummary {
  panchayat: Panchayat;
  crop: Crop;
  modeled: boolean;
  /** Final action (officer override if any). */
  action: Action | null;
  status: DecisionStatus | null;
  confidence: number | null;
  suitability_score: number | null;
}

// --- /notify ---
export interface NotifyMessage {
  panchayat_id: string;
  crop: Crop;
  channel: "whatsapp";
  language: string;
  /** WhatsApp formatting: *bold*, _italic_. */
  text: string;
  char_count: number;
  decision_status: DecisionStatus | null;
  final_action: Action | null;
  farmer_url: string;
  translations: { language: string; language_name: string; status: "pending"; text: string | null }[];
  can_send: boolean;
  blocked_reason: string | null;
}

export interface NotifyResult {
  message: NotifyMessage;
  delivery: { channel: "whatsapp"; provider: "log"; status: "logged"; logged_at: string };
}

// --- /feedback ---
export type FarmerAction = "sowed" | "waited" | "sprayed" | "nothing";

export interface FeedbackIn {
  panchayat_id: string;
  rain_occurred: boolean;
  action_taken: FarmerAction;
  note?: string | null;
}

export interface FeedbackEntry {
  id: number;
  panchayat_id: string;
  panchayat_name: string;
  block_name: string;
  crop: Crop;
  submitted_at: string;
  rain_occurred: boolean;
  action_taken: FarmerAction;
  note: string | null;
  /** Final action shown when the report was submitted. */
  advised_action: Action | null;
  advice_status: DecisionStatus | null;
  model_action: Action | null;
  model_confidence: number | null;
  decision_issued_on: string | null;
  followed_advice: boolean | null;
}
