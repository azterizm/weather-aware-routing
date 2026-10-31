import { Box, Paper } from '@mui/material';
import { useDeferredValue, useMemo, useState } from 'react';
import {
  CircleMarker,
  LayerGroup,
  LayersControl,
  MapContainer,
  Pane,
  TileLayer,
  Tooltip,
} from 'react-leaflet';

import type { CorridorForecast, PlaceOption, TripPlan } from '../../api/types';
import { decodePolyline } from '../../utils/polyline';
import { RouteCheckpoints } from './CheckpointLayer';
import { FitBounds } from './FitBounds';
import { ForecastSlider } from './ForecastSlider';
import { HeatmapLayer } from './HeatmapLayer';
import { CHECKPOINT_PANE, CHECKPOINT_PANE_Z, HEATMAP_PANE, HEATMAP_PANE_Z } from './panes';
import { RiskLegend } from './RiskLegend';
import { RouteLayer } from './RouteLayer';

const US_CENTER: [number, number] = [39.5, -98.35];

interface Props {
  plan: TripPlan | undefined;
  endpoints: { origin: PlaceOption; destination: PlaceOption } | undefined;
  corridor: { data: CorridorForecast | undefined; loading: boolean; error: string | null };
  selectedRouteId: string | undefined;
  onSelectRoute: (routeId: string) => void;
}

export default function TripMap({
  plan,
  endpoints,
  corridor,
  selectedRouteId,
  onSelectRoute,
}: Props) {
  // The slider resets to the departure hour for every new plan.
  const [slider, setSlider] = useState<{ plan: TripPlan | undefined; hour: number }>({
    plan: undefined,
    hour: 0,
  });
  const hour = slider.plan === plan ? slider.hour : 0;
  const heatmapHour = useDeferredValue(hour);

  const positions = useMemo(
    () => new Map(plan?.routes.map((route) => [route.id, decodePolyline(route.geometry)]) ?? []),
    [plan],
  );
  const lines = useMemo(() => [...positions.values()], [positions]);

  return (
    <Box
      role="region"
      aria-label="Route map"
      sx={{ position: 'relative', height: '100%', minHeight: 420 }}
    >
      <MapContainer
        center={US_CENTER}
        zoom={4}
        preferCanvas
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          maxZoom={18}
        />
        {/* Panes keep the heatmap under routes and checkpoints above them, whatever loads first. */}
        {corridor.data && (
          <LayersControl position="topright">
            <LayersControl.Overlay checked name="Weather risk heatmap">
              <Pane name={HEATMAP_PANE} style={{ zIndex: HEATMAP_PANE_Z }}>
                <LayerGroup>
                  <HeatmapLayer forecast={corridor.data} hourIndex={heatmapHour} />
                </LayerGroup>
              </Pane>
            </LayersControl.Overlay>
          </LayersControl>
        )}
        {plan && selectedRouteId && (
          <>
            <RouteLayer
              routes={plan.routes}
              positions={positions}
              selectedRouteId={selectedRouteId}
              recommendedRouteId={plan.recommended_route_id}
              onSelect={onSelectRoute}
            />
            <FitBounds lines={lines} />
          </>
        )}
        <Pane name={CHECKPOINT_PANE} style={{ zIndex: CHECKPOINT_PANE_Z }}>
          {plan &&
            selectedRouteId &&
            plan.routes.map((route) => (
              <RouteCheckpoints
                key={route.id}
                route={route}
                selected={route.id === selectedRouteId}
                onSelect={onSelectRoute}
              />
            ))}
          {endpoints &&
            (['origin', 'destination'] as const).map((kind) => (
              <CircleMarker
                key={kind}
                center={[endpoints[kind].lat, endpoints[kind].lon]}
                radius={8}
                pathOptions={{ color: '#111827', weight: 3, fillColor: '#ffffff', fillOpacity: 1 }}
              >
                <Tooltip>
                  {kind === 'origin' ? 'Origin' : 'Destination'} is {endpoints[kind].label}
                </Tooltip>
              </CircleMarker>
            ))}
        </Pane>
      </MapContainer>
      {plan && (
        <Paper
          elevation={3}
          sx={{
            position: 'absolute',
            left: 12,
            right: 12,
            bottom: 24,
            zIndex: 1000,
            px: 2,
            py: 1,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            columnGap: 3,
            rowGap: 1,
          }}
        >
          <ForecastSlider
            hours={corridor.data?.hours}
            value={hour}
            onChange={(next) => setSlider({ plan, hour: next })}
            loading={corridor.loading}
            error={corridor.error}
          />
          <RiskLegend loadLbs={plan.load_weight_lbs} />
        </Paper>
      )}
    </Box>
  );
}
