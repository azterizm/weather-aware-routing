import { Box, LinearProgress, Slider, Typography } from '@mui/material';

import { formatDateTime } from '../../utils/format';

interface Props {
  hours: string[] | undefined;
  value: number;
  onChange: (hourIndex: number) => void;
  loading: boolean;
  error: string | null;
}

const MARKS = [0, 12, 24, 36, 48].map((hour) => ({ value: hour, label: `${hour} h` }));

/** 0-48 hour slider for the corridor heatmap; hour 0 is the departure hour. */
export function ForecastSlider({ hours, value, onChange, loading, error }: Props) {
  const current = hours?.[value];
  return (
    <Box sx={{ minWidth: 0, flex: '1 1 320px' }}>
      <Typography variant="subtitle2" component="h2">
        Corridor weather risk
        {current && (
          <Typography component="span" variant="body2" color="text.secondary">
            {' '}
            at {formatDateTime(current)}, {value} h after departure
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
          />
        </Box>
      )}
    </Box>
  );
}
