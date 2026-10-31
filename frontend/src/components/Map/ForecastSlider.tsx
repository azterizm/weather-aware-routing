import { Box, LinearProgress, Slider, Typography } from '@mui/material';

import { ROUTE_COLORS } from '../../theme';
import { formatDateTime } from '../../utils/format';
import type { TripWindow } from './tripWindow';

interface Props {
  hours: string[] | undefined;
  value: number;
  onChange: (hourIndex: number) => void;
  loading: boolean;
  error: string | null;
  /** The selected route's time on the road, shaded on the slider rail. */
  trip: TripWindow | null;
}

const OFF_TRIP_COLOR = '#d5d8dd';

function railBackground(trip: TripWindow | null): string {
  if (!trip) return OFF_TRIP_COLOR;
  const { startPercent: start, endPercent: end } = trip;
  return `linear-gradient(to right, ${OFF_TRIP_COLOR} ${start}%, ${ROUTE_COLORS.selected} ${start}%, ${ROUTE_COLORS.selected} ${end}%, ${OFF_TRIP_COLOR} ${end}%)`;
}

const MARKS = [0, 12, 24, 36, 48].map((hour) => ({ value: hour, label: `${hour} h` }));

/** 0-48 hour slider for the corridor heatmap; hour 0 is the departure hour. */
export function ForecastSlider({ hours, value, onChange, loading, error, trip }: Props) {
  const current = hours?.[value];
  return (
    <Box sx={{ minWidth: 0, flex: '1 1 320px' }}>
      <Typography variant="subtitle2" component="h2">
        Corridor weather risk
        {current && (
          <Typography component="span" variant="body2" color="text.secondary">
            {' '}
            at {formatDateTime(current)}
          </Typography>
        )}
      </Typography>
      {loading && !hours && (
        <Box sx={{ py: 1 }}>
          <LinearProgress aria-label="Loading corridor forecast" />
          <Typography variant="caption" color="text.secondary">
            Loading corridor forecast…
          </Typography>
        </Box>
      )}
      {error && !hours && (
        <Typography variant="body2" color="error" sx={{ py: 1 }}>
          The corridor forecast is unavailable. {error}
        </Typography>
      )}
      {hours && (
        <Box sx={{ px: 1.5 }}>
          <Slider
            aria-label="Forecast hour after departure"
            value={value}
            min={0}
            max={hours.length - 1}
            step={1}
            marks={MARKS}
            getAriaValueText={(hour) => `${hour} hours after departure`}
            onChange={(_, next) => onChange(next as number)}
            size="small"
            // No filled track: the rail shading shows the trip, not the slider position.
            track={false}
            sx={{
              '& .MuiSlider-rail': { height: 6, opacity: 1, background: railBackground(trip) },
            }}
          />
        </Box>
      )}
    </Box>
  );
}
