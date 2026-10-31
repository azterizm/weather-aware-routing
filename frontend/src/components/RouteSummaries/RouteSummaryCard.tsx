import { Box, Card, CardActionArea, CardContent, Chip, Stack, Typography } from '@mui/material';
import { memo } from 'react';

import type { RouteOption } from '../../api/types';
import { formatDateTime, formatDuration, formatMiles } from '../../utils/format';
import { RISK_META, riskLabel } from '../../utils/risk';
import { RiskMilesBar } from './RiskMilesBar';

interface Props {
  route: RouteOption;
  recommended: boolean;
  selected: boolean;
  onSelect: (routeId: string) => void;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" component="div">
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {value}
      </Typography>
    </Box>
  );
}

export const RouteSummaryCard = memo(function RouteSummaryCard({
  route,
  recommended,
  selected,
  onSelect,
}: Props) {
  const { summary } = route;
  const miles = summary.miles_by_risk;
  return (
    <Card
      sx={{
        borderColor: selected ? 'primary.main' : 'divider',
        borderWidth: 2,
      }}
    >
      <CardActionArea onClick={() => onSelect(route.id)} aria-pressed={selected}>
        <CardContent sx={{ py: 1.5 }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1 }}>
            <Typography variant="subtitle1" component="h3" sx={{ fontWeight: 600 }}>
              {route.label}
            </Typography>
            {recommended && <Chip label="Recommended" color="primary" size="small" />}
            {selected && !recommended && <Chip label="Selected" variant="outlined" size="small" />}
          </Stack>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
              gap: 1,
              mb: 1.25,
            }}
          >
            <Stat label="Distance" value={formatMiles(route.distance_miles)} />
            <Stat label="Travel time" value={formatDuration(route.duration_seconds)} />
            <Stat label="Arrival" value={formatDateTime(route.arrival_time)} />
            <Stat label="No Travel" value={formatMiles(miles.NO_TRAVEL)} />
            <Stat label="Severe" value={formatMiles(miles.SEVERE)} />
            <Stat label="High" value={formatMiles(miles.HIGH)} />
            <Stat
              label="Average risk"
              value={
                summary.average_risk === null
                  ? 'Unknown'
                  : `${summary.average_risk.toFixed(2)} of 4`
              }
            />
            <Box>
              <Typography variant="caption" color="text.secondary" component="div">
                Max risk
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
                {summary.max_risk && (
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: '2px',
                      bgcolor: RISK_META[summary.max_risk].color,
                    }}
                  />
                )}
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {riskLabel(summary.max_risk)}
                </Typography>
              </Stack>
            </Box>
            <Stat label="Checkpoints" value={String(route.checkpoints.length)} />
          </Box>
          <RiskMilesBar milesByRisk={miles} />
        </CardContent>
      </CardActionArea>
    </Card>
  );
});
