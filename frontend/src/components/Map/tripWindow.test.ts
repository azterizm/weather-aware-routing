import { tripWindow } from './tripWindow';

const hours = Array.from({ length: 49 }, (_, h) =>
  new Date(Date.UTC(2026, 10, 1, 12 + h)).toISOString(),
);

describe('tripWindow', () => {
  it('places departure and arrival on the 48-hour slider', () => {
    // Departs 12:45, arrives 00:45 the next day: 0.75 h to 12.75 h after the first hour.
    const window = tripWindow(hours, '2026-11-01T12:45:00Z', '2026-11-02T00:45:00Z');
    expect(window?.startPercent).toBeCloseTo((0.75 / 48) * 100);
    expect(window?.endPercent).toBeCloseTo((12.75 / 48) * 100);
  });

  it('clamps a trip longer than the slider', () => {
    const window = tripWindow(hours, '2026-11-01T12:00:00Z', '2026-11-04T00:00:00Z');
    expect(window?.endPercent).toBe(100);
  });

  it('returns null without forecast hours', () => {
    expect(tripWindow([], '2026-11-01T12:00:00Z', '2026-11-01T18:00:00Z')).toBeNull();
  });
});
