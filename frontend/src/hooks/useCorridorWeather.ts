import { useQuery } from '@tanstack/react-query';

import { fetchCorridorWeather } from '../api/trips';
import type { TripPlan } from '../api/types';

/** Corridor heatmap for 0-48 h after departure; loads after the plan so routes render first. */
export function useCorridorWeather(plan: TripPlan | undefined) {
  const request = plan
    ? {
        routes: plan.routes.map((route) => route.geometry),
        start_time: plan.departure_time,
        load_weight_lbs: plan.load_weight_lbs,
      }
    : null;
  return useQuery({
    queryKey: ['corridor-weather', request],
    queryFn: ({ signal }) => fetchCorridorWeather(request!, signal),
    enabled: request !== null,
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });
}
