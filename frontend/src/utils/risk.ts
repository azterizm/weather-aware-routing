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
  return level ? RISK_META[level].label : '—';
}

const LOAD_RULE_TEXT: Record<string, string> = {
  wind_45_54_load_over_30000: 'wind 45–54 mph with load over 30,000 lb',
  wind_35_44_load_over_40000: 'wind 35–44 mph with load over 40,000 lb',
};

/** Why a checkpoint has its level, e.g. "Wind (wind 35–44 mph with load over 40,000 lb)". */
export function describeRiskCause(checkpoint: Checkpoint): string {
  const { factors, risk } = checkpoint;
  if (!factors || risk === 'UNKNOWN') return 'Forecast unavailable';
  if (risk === 'LOW') return 'All conditions below thresholds';
  const causes: string[] = [];
  if (factors.wind === risk) {
    const rule = factors.load_rule ? LOAD_RULE_TEXT[factors.load_rule] : undefined;
    causes.push(rule ? `Wind (${rule})` : 'Wind');
  }
  if (factors.rain === risk) causes.push('Rain');
  if (factors.snow === risk) causes.push('Snow');
  return causes.join(', ');
}
