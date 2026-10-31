import { useQuery } from '@tanstack/react-query';

import { planTrip } from '../api/trips';
import type { TripPlanRequest } from '../api/types';

/** Plans the submitted trip. Re-submitting identical inputs is served from the query cache. */
export function useTripPlan(request: TripPlanRequest | null) {
  return useQuery({
    queryKey: ['trip-plan', request],
    queryFn: ({ signal }) => planTrip(request as TripPlanRequest, signal),
    enabled: request !== null,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
