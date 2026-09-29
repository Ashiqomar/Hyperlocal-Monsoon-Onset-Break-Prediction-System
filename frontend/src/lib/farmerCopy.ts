/**
 * Plain-language wording for the farmer screen. All farmer-facing text lives
 * here so it can be reviewed with extension staff and translated (e.g. Marathi)
 * in one place. Avoid jargon: no "scenario", "probability", "expected loss".
 */

import type { Action, DecisionResponse, ForecastResponse, Scenario } from "../types";
import { humanize } from "./format";

const HA_PER_ACRE = 0.4047;

export function greeting(now = new Date()): string {
  const h = now.getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export const cropName = (crop: string) => humanize(crop).toLowerCase();

interface ActionCopy {
  tone: "go" | "wait" | "caution" | "check";
  headline: (crop: string) => string;
  body: (crop: string) => string;
  /** Short, concrete things to do. */
  steps: string[];
}

export const ACTION_COPY: Record<Action, ActionCopy> = {
  SOW: {
    tone: "go",
    headline: (crop) => `Good time to sow your ${crop}`,
    body: () => "The rains look steady enough. You can go ahead and sow this week.",
    steps: ["Sow when the soil is moist, after a good rain", "Use treated seed"],
  },
  WAIT: {
    tone: "wait",
    headline: () => "Wait before sowing",
    body: () => "Hold off sowing for 1–2 weeks, until the rains are steady and the soil is moist.",
    steps: ["Keep seed and fertiliser ready", "Sow after good rain on 2–3 days in a row"],
  },
  SPRAY: {
    tone: "caution",
    headline: (crop) => `Sow, but protect your ${crop}`,
    body: () => "Wet weather is likely in the coming weeks. It brings pests and disease, so plan a protective spray.",
    steps: [
      "Spray only on a dry day, when no rain is expected for a few hours",
      "Ask your Krishi Sahayak which spray to use",
      "Make channels so water does not stand in the field",
    ],
  },
  REASSESS: {
    tone: "check",
    headline: () => "Wait a few days, then check again",
    body: () => "The weather is unclear right now. Don’t spend money on sowing yet. Check this app again next week.",
    steps: ["Keep seed and fertiliser ready", "Open this app again in a week"],
  },
};

/** "4 in 10". Rounds to the nearest tenth but never shows 0 or 10 for real chances. */
export function chanceInTen(p: number): string {
  const n = Math.min(9, Math.max(1, Math.round(p * 10)));
  if (p < 0.05) return "very low";
  if (p > 0.95) return "almost certain";
  return `${n} in 10`;
}

export function rainWords(mm: number): string {
  if (mm < 5) return "very little rain";
  if (mm < 25) return "light rain";
  if (mm < 75) return "moderate rain";
  if (mm < 150) return "heavy rain";
  return "very heavy rain";
}

const RISK_WORDS: Record<Exclude<Scenario, "normal">, string> = {
  dry: "too little rain over the next month",
  wet: "too much rain over the next month",
  false_onset: "rain starting, then stopping for 10 days or more, so young plants may dry out",
};

export function certaintyWords(confidence: number): { label: string; detail: string } {
  if (confidence >= 0.6) return { label: "Fairly sure", detail: "Most weather signs point the same way." };
  if (confidence >= 0.4)
    return { label: "Somewhat sure", detail: "Weather signs are mixed, so check again next week." };
  return { label: "Not very sure", detail: "The weather is hard to predict right now. Check again next week." };
}

export function landWords(rating: DecisionResponse["crop_suitability"]["rating"], crop: string, soil: string) {
  const s = humanize(soil).toLowerCase();
  if (rating === "high") return `Your ${s} soil and usual rainfall suit ${crop} well.`;
  if (rating === "moderate") return `Your ${s} soil and usual rainfall suit ${crop} fairly well.`;
  return `Your ${s} soil and usual rainfall are not a good match for ${crop}. Ask your Krishi Sahayak about other crops.`;
}

export interface WhyPoint {
  title: string;
  text: string;
}

/** The "Why?" list. Keeps "how sure" and "your land" as separate points. */
export function whyPoints(decision: DecisionResponse, forecast: ForecastResponse | null): WhyPoint[] {
  const points: WhyPoint[] = [];
  const crop = cropName(decision.crop);

  if (forecast) {
    const w1 = forecast.weeks[0];
    points.push({
      title: "This week’s rain",
      text:
        `Expect ${rainWords(w1.rainfall_mm.p50)} (about ${Math.round(w1.rainfall_mm.p50)} mm). ` +
        `Chance of 5 or more dry days in a row: ${chanceInTen(w1.dry_spell_probability)}.`,
    });
  }

  const status = decision.escalation.status;
  if (status === "overridden") {
    // The model's worry, money and certainty explain the model's own pick, which the
    // officer replaced; showing them next to the officer's action would contradict it.
    points.push({
      title: "Checked by your officer",
      text: "Your agriculture officer looked at local conditions and changed this advice.",
    });
  } else {
    const risks = decision.expected_loss_table[0].by_scenario.filter((s) => s.scenario !== "normal");
    const top = risks.reduce((a, b) => (b.probability > a.probability ? b : a));
    points.push({
      title: "Biggest worry",
      text: `${capitalise(RISK_WORDS[top.scenario as Exclude<Scenario, "normal">])}. Chance: ${chanceInTen(top.probability)}.`,
    });

    const ranked = [...decision.expected_loss_table].sort((a, b) => a.rank - b.rank);
    const [best, next] = ranked;
    const savedPerAcre =
      Math.round(((next.expected_loss_inr_per_ha - best.expected_loss_inr_per_ha) * HA_PER_ACRE) / 50) * 50;
    if (savedPerAcre >= 50) {
      points.push({
        title: "Money",
        text: `On average this should save you about ₹${savedPerAcre.toLocaleString("en-IN")} per acre compared with the next best choice (${ACTION_COPY[next.action].headline(crop).toLowerCase()}).`,
      });
    }

    const sure = certaintyWords(decision.recommendation.confidence);
    points.push({ title: `How sure are we? ${sure.label}`, text: sure.detail });

    if (status === "approved") {
      points.push({
        title: "Checked by your officer",
        text: "Your agriculture officer has checked and agreed with this advice.",
      });
    }
  }

  points.push({
    title: "About your land",
    text: landWords(decision.crop_suitability.rating, crop, decision.crop_suitability.soil_type),
  });

  return points;
}

const capitalise = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
