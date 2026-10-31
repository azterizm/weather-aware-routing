import { Alert, AlertTitle, Stack, Typography } from '@mui/material';

import type { TripPlan } from '../../api/types';
import { formatDateTime, formatPounds } from '../../utils/format';
import { RouteSummaryCard } from './RouteSummaryCard';

interface Props {
  plan: TripPlan;
  selectedRouteId: string;
  onSelectRoute: (routeId: string) => void;
}

export function RouteSummaries({ plan, selectedRouteId, onSelectRoute }: Props) {
  const recommended = plan.routes.find((route) => route.id === plan.recommended_route_id);
  return (
    <Stack spacing={1.5} component="section" aria-label="Route options">
      {recommended && (
        <Alert severity="success" variant="outlined">
          <AlertTitle>{recommended.label} is recommended</AlertTitle>
          {plan.recommendation_reason}
        </Alert>
      )}
      {plan.warnings.map((warning) => (
        <Alert key={warning} severity="warning">
          {warning}
        </Alert>
      ))}
      <Typography variant="body2" color="text.secondary">
        Weather is sampled every {plan.checkpoint_interval_miles} mi at each checkpoint&apos;s
        arrival time. The trip departs {formatDateTime(plan.departure_time)} with a{' '}
        {formatPounds(plan.load_weight_lbs)} load. Routes are ranked by fewest No Travel, Severe and
        High miles, then average risk, then travel time.
      </Typography>
      {plan.routes.map((route) => (
        <RouteSummaryCard
          key={route.id}
          route={route}
          recommended={route.id === plan.recommended_route_id}
          selected={route.id === selectedRouteId}
          onSelect={onSelectRoute}
        />
      ))}
    </Stack>
  );
}
