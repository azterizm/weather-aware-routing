import dayjs from 'dayjs';

export const browserTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

function timeZoneAbbreviation(date: Date): string {
  const parts = new Intl.DateTimeFormat(undefined, { timeZoneName: 'short' }).formatToParts(date);
  return parts.find((part) => part.type === 'timeZoneName')?.value ?? '';
}

/** "Sat Nov 1, 2:35 PM CDT" in the browser's time zone. */
export function formatDateTime(iso: string): string {
  const date = dayjs(iso);
  return `${date.format('ddd MMM D, h:mm A')} ${timeZoneAbbreviation(date.toDate())}`.trim();
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours} h ${String(minutes).padStart(2, '0')} min` : `${minutes} min`;
}

export function formatMiles(miles: number): string {
  return `${miles.toLocaleString('en-US', { maximumFractionDigits: 1 })} mi`;
}

export function formatPounds(pounds: number): string {
  return `${pounds.toLocaleString('en-US', { maximumFractionDigits: 0 })} lb`;
}

/** Rounds down so a displayed value never crosses a risk threshold (thresholds use 2 decimals). */
function floorDecimals(value: number, digits: number): number {
  const scale = 10 ** digits;
  return Math.floor(value * scale + 1e-6) / scale;
}

export function formatRate(inchesPerHour: number): string {
  return `${floorDecimals(inchesPerHour, 2).toFixed(2)} in/hr`;
}

export function formatWind(mph: number): string {
  return `${floorDecimals(mph, 1).toFixed(1)} mph`;
}
