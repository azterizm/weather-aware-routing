import { formatDuration, formatMiles, formatPounds, formatRate, formatWind } from './format';

describe('format utils', () => {
  it('formats durations', () => {
    expect(formatDuration(42_715)).toBe('11 h 52 min');
    expect(formatDuration(1_500)).toBe('25 min');
  });

  it('never rounds a weather value up across a threshold', () => {
    expect(formatWind(34.96)).toBe('34.9 mph');
    expect(formatRate(0.099)).toBe('0.09 in/hr');
    expect(formatRate(0.25)).toBe('0.25 in/hr');
  });

  it('formats distance and weight', () => {
    expect(formatMiles(1234.56)).toBe('1,234.6 mi');
    expect(formatPounds(42000)).toBe('42,000 lb');
  });
});
