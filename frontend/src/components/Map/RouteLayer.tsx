import L, { type LatLngTuple } from 'leaflet';
import { memo, useMemo } from 'react';
import { Tooltip } from 'react-leaflet';

import type { RouteOption } from '../../api/types';
import { ROUTE_COLORS } from '../../theme';
import { formatDateTime, formatDuration, formatMiles } from '../../utils/format';
import { OffsetPolyline, routeOffset } from './offset';

interface Props {
  routes: RouteOption[];
  positions: Map<string, LatLngTuple[]>;
  selectedRouteId: string;
  recommendedRouteId: string;
  onSelect: (routeId: string) => void;
}

function RouteTooltip({ route, recommended }: { route: RouteOption; recommended: boolean }) {
  const miles = route.summary.miles_by_risk;
  const average = route.summary.average_risk;
  return (
    <div>
      <strong>
        {route.label}
        {recommended ? ', recommended' : ''}
      </strong>
      <br />
      {formatMiles(route.distance_miles)}, {formatDuration(route.duration_seconds)}, arrives{' '}
      {formatDateTime(route.arrival_time)}
      <br />
      {formatMiles(miles.NO_TRAVEL)} at No Travel, {formatMiles(miles.SEVERE)} at Severe,{' '}
      {formatMiles(miles.HIGH)} at High
      <br />
      Average risk {average === null ? 'unknown' : `${average.toFixed(2)} of 4`}
    </div>
  );
}

export const RouteLayer = memo(function RouteLayer({
  routes,
  positions,
  selectedRouteId,
  recommendedRouteId,
  onSelect,
}: Props) {
  // A wider hit tolerance makes thin route lines easy to click.
  const renderer = useMemo(() => L.canvas({ tolerance: 6 }), []);
  // Draw the selected route last so it sits on top.
  const ordered = routes
    .map((route, index) => ({ route, offset: routeOffset(index, routes.length) }))
    .sort(
      (a, b) => Number(a.route.id === selectedRouteId) - Number(b.route.id === selectedRouteId),
    );
  return (
    <>
      {ordered.map(({ route, offset }) => {
        const selected = route.id === selectedRouteId;
        return (
          <OffsetPolyline
            key={route.id}
            positions={positions.get(route.id) ?? []}
            offset={offset}
            pathOptions={{
              renderer,
              color: selected ? ROUTE_COLORS.selected : ROUTE_COLORS.other,
              weight: selected ? 6 : 4,
              opacity: selected ? 0.95 : 0.65,
            }}
            eventHandlers={{ click: () => onSelect(route.id) }}
          >
            <Tooltip sticky>
              <RouteTooltip route={route} recommended={route.id === recommendedRouteId} />
            </Tooltip>
          </OffsetPolyline>
        );
      })}
    </>
  );
});
