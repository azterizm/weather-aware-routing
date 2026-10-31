import dayjs, { type Dayjs } from 'dayjs';

import type { PlaceOption } from '../../api/types';

export const MAX_LOAD_LBS = 80_000;
export const MAX_DAYS_AHEAD = 7;

type Field = 'origin' | 'destination' | 'departure_time' | 'load_weight_lbs';
export type FieldErrors = Partial<Record<Field, string>>;

export function validateTrip(values: {
  origin: PlaceOption | null;
  destination: PlaceOption | null;
  departure: Dayjs | null;
  load: string;
  now?: Dayjs;
}): FieldErrors {
  const now = values.now ?? dayjs();
  const errors: FieldErrors = {};
  if (!values.origin) errors.origin = 'Select an origin from the suggestions.';
  if (!values.destination) errors.destination = 'Select a destination from the suggestions.';
  if (
    values.origin &&
    values.destination &&
    values.origin.lat === values.destination.lat &&
    values.origin.lon === values.destination.lon
  ) {
    errors.destination = 'Destination must differ from the origin.';
  }
  if (!values.departure || !values.departure.isValid()) {
    errors.departure_time = 'Enter a valid departure date and time.';
  } else if (values.departure.isBefore(now.subtract(1, 'minute'))) {
    errors.departure_time = 'Departure cannot be in the past.';
  } else if (values.departure.isAfter(now.add(MAX_DAYS_AHEAD, 'day'))) {
    errors.departure_time = `Departure must be within the next ${MAX_DAYS_AHEAD} days.`;
  }
  const load = Number(values.load);
  if (values.load.trim() === '' || !Number.isFinite(load)) {
    errors.load_weight_lbs = 'Enter the load weight in pounds.';
  } else if (load < 1 || load > MAX_LOAD_LBS) {
    errors.load_weight_lbs = `Load must be between 1 and ${MAX_LOAD_LBS.toLocaleString('en-US')} lb.`;
  }
  return errors;
}
