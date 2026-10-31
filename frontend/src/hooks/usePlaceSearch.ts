import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { searchPlaces } from '../api/trips';
import { useDebouncedValue } from './useDebouncedValue';

export const MIN_QUERY_LENGTH = 3;
const DEBOUNCE_MS = 350;

export function usePlaceSearch(input: string) {
  const query = useDebouncedValue(input.trim(), DEBOUNCE_MS);
  const enabled = query.length >= MIN_QUERY_LENGTH;
  return useQuery({
    queryKey: ['geocode', query.toLowerCase()],
    queryFn: ({ signal }) => searchPlaces(query, signal),
    enabled,
    staleTime: 60 * 60 * 1000,
    placeholderData: keepPreviousData,
    retry: false,
  });
}
