import type { LatLngTuple } from 'leaflet';
import { memo, useMemo } from 'react';
import { Tooltip } from 'react-leaflet';

import type { Checkpoint, RouteOption } from '../../api/types';
import { formatDateTime, formatRate, formatWind } from '../../utils/format';
import { RISK_META, describeRiskCause } from '../../utils/risk';
import { neighbourVertices, OffsetCircleMarker } from './offset';

function CheckpointTooltip({ route, checkpoint }: { route: RouteOption; checkpoint: Checkpoint }) {
  const { weather } = checkpoint;
  return (
    <div>
      <strong>
        {route.label}, mile {checkpoint.mile.toFixed(1)}
      </strong>
      , checkpoint {checkpoint.index + 1} of {route.checkpoints.length}
      <br />
      Arrives {formatDateTime(checkpoint.eta)}
      <br />
      {weather
        ? `Wind ${formatWind(weather.wind_mph)}, rain ${formatRate(weather.rain_in_hr)}, snow ${formatRate(weather.snow_in_hr)}`
        : 'No forecast for this hour'}
      <br />
      <strong>{describeRiskCause(checkpoint)}</strong>
    </div>
  );
}

interface RouteCheckpointsProps {
  route: RouteOption;
  /** The route's decoded line and sideways pixel offset, shared with its polyline. */
  line: LatLngTuple[];
  offset: number;
  selected: boolean;
  onSelect: (routeId: string) => void;
}

/** Checkpoints of one route, coloured by risk. Selected-route markers are larger. */
export const RouteCheckpoints = memo(function RouteCheckpoints({
  route,
  line,
  offset,
  selected,
  onSelect,
}: RouteCheckpointsProps) {
  const directions = useMemo(
    () => route.checkpoints.map((cp) => neighbourVertices(line, [cp.lat, cp.lon])),
    [route, line],
  );
  return (
    <>
      {route.checkpoints.map((checkpoint) => (
        <OffsetCircleMarker
          key={checkpoint.index}
          center={[checkpoint.lat, checkpoint.lon]}
          offset={offset}
          direction={directions[checkpoint.index] ?? null}
          radius={selected ? 6 : 4}
          pathOptions={{
            color: '#ffffff',
            weight: selected ? 2 : 1,
            fillColor: RISK_META[checkpoint.risk].color,
            fillOpacity: selected ? 1 : 0.75,
          }}
          eventHandlers={{ click: () => onSelect(route.id) }}
        >
          {/* react-leaflet would otherwise put the tooltip in the checkpoint pane, under the dots. */}
          <Tooltip pane="tooltipPane">
            <CheckpointTooltip route={route} checkpoint={checkpoint} />
          </Tooltip>
        </OffsetCircleMarker>
      ))}
    </>
  );
});
