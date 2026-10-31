import type { Checkpoint } from '../api/types';
import { describeRiskCause, riskFromScore, RISK_META } from './risk';

const base: Checkpoint = {
  index: 0,
  mile: 0,
  lat: 0,
  lon: 0,
  eta: '2026-11-01T12:00:00Z',
  weather: { wind_mph: 38, rain_in_hr: 0, snow_in_hr: 0 },
  risk: 'SEVERE',
  factors: { wind: 'SEVERE', rain: 'LOW', snow: 'LOW', load_rule: 'wind_35_44_load_over_40000' },
};

describe('risk utils', () => {
  it('maps scores to levels, with -1 as unknown', () => {
    expect(riskFromScore(0)).toBe('LOW');
    expect(riskFromScore(4)).toBe('NO_TRAVEL');
    expect(riskFromScore(-1)).toBe('UNKNOWN');
  });

  it('explains a load-adjusted wind level', () => {
    expect(describeRiskCause(base)).toBe(
      'Risk level is Severe, set by wind of 35 to 44 mph with a load over 40,000 lb.',
    );
  });

  it('lists every factor at the overall level', () => {
    const checkpoint: Checkpoint = {
      ...base,
      risk: 'HIGH',
      factors: { wind: 'HIGH', rain: 'HIGH', snow: 'LOW', load_rule: null },
    };
    expect(describeRiskCause(checkpoint)).toBe('Risk level is High, set by wind and rain.');
  });

  it('handles low and unknown checkpoints', () => {
    expect(describeRiskCause({ ...base, risk: 'LOW' })).toBe(
      'Risk level is Low. Every condition is below its threshold.',
    );
    expect(describeRiskCause({ ...base, risk: 'UNKNOWN', factors: null })).toBe(
      'The forecast is unavailable for this hour.',
    );
  });

  it('gets darker with severity (ordinal ramp)', () => {
    const luminance = (hex: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
    };
    const levels = ['LOW', 'MODERATE', 'HIGH', 'SEVERE', 'NO_TRAVEL'] as const;
    const values = levels.map((level) => luminance(RISK_META[level].color));
    expect([...values].sort((a, b) => b - a)).toEqual(values);
  });
});
