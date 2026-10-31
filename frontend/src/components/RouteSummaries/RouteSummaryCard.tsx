import InfoOutlined from '@mui/icons-material/InfoOutlined';
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  Chip,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import { memo } from 'react';

import type { RouteOption } from '../../api/types';
import { formatDateTime, formatDuration, formatMiles } from '../../utils/format';
import { RISK_META, riskLabel } from '../../utils/risk';
import { RiskMilesBar } from './RiskMilesBar';
import { RISK_INFO } from './riskInfo';

interface Props {
  route: RouteOption;
  /** Checkpoint spacing in miles, the same for every route in the plan. */
  intervalMiles: number;
  recommended: boolean;
  selected: boolean;
  onSelect: (routeId: string) => void;
}

function Stat({ label, value, info }: { label: string; value: string; info?: string }) {
  return (
    <Box>
      <Typography
        variant="caption"
        color="text.secondary"
        component="div"
        sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}
      >
        {label}
        {info && (
          // A labelled icon, not a button: the whole card is already a button.
          <Tooltip title={info} enterTouchDelay={0}>
            <Box component="span" role="img" sx={{ display: 'inline-flex', cursor: 'help' }}>
              <InfoOutlined sx={{ fontSize: 14 }} />
            </Box>
          </Tooltip>
        )}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        {value}
      </Typography>
    </Box>
  );
}

export const RouteSummaryCard = memo(function RouteSummaryCard({
  route,
  intervalMiles,
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
            <Stat
              label="No Travel miles"
              value={formatMiles(miles.NO_TRAVEL)}
              info={RISK_INFO.NO_TRAVEL}
            />
            <Stat label="Severe miles" value={formatMiles(miles.SEVERE)} info={RISK_INFO.SEVERE} />
            <Stat label="High miles" value={formatMiles(miles.HIGH)} info={RISK_INFO.HIGH} />
            <Stat
              label="Average risk"
              info={RISK_INFO.AVERAGE}
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
            <Stat
              label="Checkpoints"
              value={`${route.checkpoints.length}, every ${intervalMiles} mi`}
            />
          </Box>
          <RiskMilesBar milesByRisk={miles} />
        </CardContent>
      </CardActionArea>
    </Card>
  );
});
