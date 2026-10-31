import dayjs from 'dayjs';

import { validateTrip } from './validation';

const now = dayjs('2026-11-01T12:00:00Z');
const dallas = { label: 'Dallas, TX', lat: 32.78, lon: -96.8 };
const denver = { label: 'Denver, CO', lat: 39.74, lon: -104.99 };
const valid = {
  origin: dallas,
  destination: denver,
  departure: now.add(1, 'hour'),
  load: '42000',
  now,
};

describe('validateTrip', () => {
  it('accepts a complete trip', () => {
    expect(validateTrip(valid)).toEqual({});
  });

  it('requires places picked from suggestions', () => {
    const errors = validateTrip({ ...valid, origin: null, destination: null });
    expect(errors.origin).toBeDefined();
    expect(errors.destination).toBeDefined();
  });

  it('rejects identical origin and destination', () => {
    expect(validateTrip({ ...valid, destination: dallas }).destination).toMatch(/differ/);
  });

  it('bounds the departure time', () => {
    expect(validateTrip({ ...valid, departure: now.subtract(1, 'hour') }).departure_time).toMatch(
      /past/,
    );
    expect(validateTrip({ ...valid, departure: now.add(8, 'day') }).departure_time).toMatch(
      /7 days/,
    );
  });

  it.each(['', 'abc', '0', '80001'])('rejects load %j', (load) => {
    expect(validateTrip({ ...valid, load }).load_weight_lbs).toBeDefined();
  });

  it.each(['1', '80000', '30000.5'])('accepts load %j', (load) => {
    expect(validateTrip({ ...valid, load }).load_weight_lbs).toBeUndefined();
  });
});
