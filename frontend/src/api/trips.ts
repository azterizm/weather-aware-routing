import { http } from './client';
import type {
  CorridorForecast,
  CorridorRequest,
  PlaceOption,
  TripPlan,
  TripPlanRequest,
} from './types';

export async function searchPlaces(query: string, signal?: AbortSignal): Promise<PlaceOption[]> {
  const { data } = await http.get<{ results: PlaceOption[] }>('/geocode/', {
    params: { q: query },
    signal,
  });
  return data.results;
}

export async function planTrip(request: TripPlanRequest, signal?: AbortSignal): Promise<TripPlan> {
  const { data } = await http.post<TripPlan>('/trips/plan/', request, { signal });
  return data;
}

export async function fetchCorridorWeather(
  request: CorridorRequest,
  signal?: AbortSignal,
): Promise<CorridorForecast> {
  const { data } = await http.post<CorridorForecast>('/trips/corridor-weather/', request, {
    signal,
  });
  return data;
}
