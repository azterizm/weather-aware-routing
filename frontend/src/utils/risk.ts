import type { Checkpoint, RiskLevel, RiskOrUnknown } from '../api/types';

export const RISK_LEVELS: readonly RiskLevel[] = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL'];
export const RISK_KEYS: readonly RiskOrUnknown[] = [...RISK_LEVELS, 'UNKNOWN'];

/**
 * One-hue ordinal ramp (OKLCH hue ~35, lightness falling with severity) so the order reads
 * by lightness even without colour vision; validated with the dataviz ordinal checks.
 * Colour is always paired with a text label.
 */
export const RISK_META: Record<RiskOrUnknown, { label: string; color: string }> = {
  LOW: { label: 'Low', color: '#f09c7c' },
  MODERATE: { label: 'Moderate', color: '#e16c48' },
  HIGH: { label: 'High', color: '#c83d22' },
  SEVERE: { label: 'Severe', color: '#a01916' },
  NO_TRAVEL: { label: 'No Travel', color: '#6f0d13' },
  UNKNOWN: { label: 'Unknown', color: '#8a8f98' },
};

export function riskFromScore(score: number): RiskOrUnknown {
  return RISK_LEVELS[score] ?? 'UNKNOWN';
}

export function riskLabel(level: RiskOrUnknown | null): string {
  return level ? RISK_META[level].label : 'Unknown';
}

const LOAD_RULE_TEXT: Record<string, string> = {
  wind_45_54_load_over_30000: 'wind of 45 to 54 mph with a load over 30,000 lb',
  wind_35_44_load_over_40000: 'wind of 35 to 44 mph with a load over 40,000 lb',
};

function joinWithAnd(items: string[]): string {
  return items.length > 1 ? `${items.slice(0, -1).join(', ')} and ${items.at(-1)}` : items.join('');
}

/** One sentence on why a checkpoint has its level, such as "Risk level is Severe, set by rain." */
export function describeRiskCause(checkpoint: Checkpoint): string {
  const { factors, risk } = checkpoint;
  if (!factors || risk === 'UNKNOWN') return 'The forecast is unavailable for this hour.';
  if (risk === 'LOW') return 'Risk level is Low. Every condition is below its threshold.';
  const causes: string[] = [];
  if (factors.wind === risk) {
    causes.push((factors.load_rule && LOAD_RULE_TEXT[factors.load_rule]) || 'wind');
  }
  if (factors.rain === risk) causes.push('rain');
  if (factors.snow === risk) causes.push('snow');
  return `Risk level is ${RISK_META[risk].label}, set by ${joinWithAnd(causes)}.`;
}
