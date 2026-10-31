import type { LatLngBoundsExpression } from 'leaflet';
import { memo, useMemo } from 'react';
import { Rectangle, Tooltip } from 'react-leaflet';

import type { CorridorForecast } from '../../api/types';
import { formatRate, formatWind } from '../../utils/format';
import { RISK_META, riskFromScore } from '../../utils/risk';

interface CellProps {
  bounds: LatLngBoundsExpression;
  risk: number;
  wind: number | null;
  rain: number | null;
  snow: number | null;
}

const HeatCell = memo(function HeatCell({ bounds, risk, wind, rain, snow }: CellProps) {
  const level = riskFromScore(risk);
  // Low recedes toward the map so elevated risk stands out.
  const fillOpacity = level === 'LOW' ? 0.18 : level === 'UNKNOWN' ? 0.25 : 0.55;
  return (
    <Rectangle
      bounds={bounds}
      pathOptions={{ stroke: false, fillColor: RISK_META[level].color, fillOpacity }}
    >
      <Tooltip sticky>
        <strong>{RISK_META[level].label} risk</strong>
        {wind !== null && rain !== null && snow !== null && (
          <>
            <br />
            Wind {formatWind(wind)}, rain {formatRate(rain)}, snow {formatRate(snow)}
          </>
        )}
      </Tooltip>
    </Rectangle>
  );
});

interface Props {
  forecast: CorridorForecast;
  hourIndex: number;
}

/** Corridor risk cells for one forecast hour. */
export const HeatmapLayer = memo(function HeatmapLayer({ forecast, hourIndex }: Props) {
  const bounds = useMemo(() => {
    const half = forecast.cell_size_deg / 2;
    return forecast.cells.map(([lat, lon]): LatLngBoundsExpression => [
      [lat - half, lon - half],
      [lat + half, lon + half],
    ]);
  }, [forecast]);
  const risk = forecast.risk[hourIndex] ?? [];
  const wind = forecast.wind_mph[hourIndex] ?? [];
  const rain = forecast.rain_in_hr[hourIndex] ?? [];
  const snow = forecast.snow_in_hr[hourIndex] ?? [];
  return (
    <>
      {bounds.map((cellBounds, i) => (
        <HeatCell
          key={i}
          bounds={cellBounds}
          risk={risk[i] ?? -1}
          wind={wind[i] ?? null}
          rain={rain[i] ?? null}
          snow={snow[i] ?? null}
        />
      ))}
    </>
  );
});
