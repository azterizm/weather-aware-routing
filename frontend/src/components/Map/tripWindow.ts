const HOUR_MS = 3_600_000;

export interface TripWindow {
  /** Start and end of the trip as percentages of the slider span (0-100). */
  startPercent: number;
  endPercent: number;
}

/** Where a route's departure-to-arrival span falls on the forecast slider. */
export function tripWindow(
  hours: string[],
  departureIso: string,
  arrivalIso: string,
): TripWindow | null {
  const first = hours[0];
  const span = hours.length - 1;
  if (!first || span <= 0) return null;
  const start = Date.parse(first);
  const toPercent = (iso: string) =>
    Math.min(100, Math.max(0, ((Date.parse(iso) - start) / HOUR_MS / span) * 100));
  return { startPercent: toPercent(departureIso), endPercent: toPercent(arrivalIso) };
}
