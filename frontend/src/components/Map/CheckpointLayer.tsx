import { memo } from 'react';
import { CircleMarker, Tooltip } from 'react-leaflet';

import type { Checkpoint, RouteOption } from '../../api/types';
import { formatDateTime, formatRate, formatWind } from '../../utils/format';
import { RISK_META, describeRiskCause } from '../../utils/risk';

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
  selected: boolean;
  onSelect: (routeId: string) => void;
}

/** Checkpoints of one route, coloured by risk. Selected-route markers are larger. */
export const RouteCheckpoints = memo(function RouteCheckpoints({
  route,
  selected,
  onSelect,
}: RouteCheckpointsProps) {
  return (
    <>
      {route.checkpoints.map((checkpoint) => (
        <CircleMarker
          key={checkpoint.index}
          center={[checkpoint.lat, checkpoint.lon]}
          radius={selected ? 6 : 4}
          pathOptions={{
            color: '#ffffff',
            weight: selected ? 2 : 1,
            fillColor: RISK_META[checkpoint.risk].color,
            fillOpacity: selected ? 1 : 0.75,
          }}
          eventHandlers={{ click: () => onSelect(route.id) }}
        >
          <Tooltip>
            <CheckpointTooltip route={route} checkpoint={checkpoint} />
          </Tooltip>
        </CircleMarker>
      ))}
    </>
  );
});
