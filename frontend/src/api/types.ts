/** Types mirroring the Django REST API contract (see README "API"). */

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL';
export type RiskOrUnknown = RiskLevel | 'UNKNOWN';

export interface PlaceOption {
  label: string;
  lat: number;
  lon: number;
}

export interface Weather {
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface RiskFactors {
  wind: RiskLevel;
  rain: RiskLevel;
  snow: RiskLevel;
  load_rule: string | null;
}

export interface Checkpoint {
  index: number;
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  weather: Weather | null;
  risk: RiskOrUnknown;
  factors: RiskFactors | null;
}

export interface RouteSummary {
  miles_by_risk: Record<RiskOrUnknown, number>;
  average_risk: number | null;
  max_risk: RiskLevel | null;
}

export interface RouteOption {
  id: string;
  label: string;
  distance_miles: number;
  duration_seconds: number;
  departure_time: string;
  arrival_time: string;
  /** Google encoded polyline, precision 5. */
  geometry: string;
  summary: RouteSummary;
  checkpoints: Checkpoint[];
}

export interface TripPlan {
  departure_time: string;
  load_weight_lbs: number;
  checkpoint_interval_miles: number;
  recommended_route_id: string;
  recommendation_reason: string;
  warnings: string[];
  routes: RouteOption[];
}

export interface TripPlanRequest {
  origin: PlaceOption;
  destination: PlaceOption;
  departure_time: string;
  load_weight_lbs: number;
}

export interface CorridorRequest {
  routes: string[];
  start_time: string;
  load_weight_lbs: number;
}

export interface CorridorForecast {
  /** 49 hourly UTC timestamps: departure hour + 0..48 h. */
  hours: string[];
  cell_size_deg: number;
  /** [lat, lon] cell centres. */
  cells: [number, number][];
  /** [hour][cell] risk score 0-4, or -1 when unknown. */
  risk: number[][];
  wind_mph: (number | null)[][];
  rain_in_hr: (number | null)[][];
  snow_in_hr: (number | null)[][];
}

export interface ApiErrorBody {
  detail: string;
  code: string;
  fields?: Record<string, unknown>;
}
