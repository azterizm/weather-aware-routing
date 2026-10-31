import { Alert, AlertTitle, Stack } from '@mui/material';

import type { TripPlan } from '../../api/types';
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
      {plan.routes.map((route) => (
        <RouteSummaryCard
          key={route.id}
          route={route}
          intervalMiles={plan.checkpoint_interval_miles}
          recommended={route.id === plan.recommended_route_id}
          selected={route.id === selectedRouteId}
          onSelect={onSelectRoute}
        />
      ))}
    </Stack>
  );
}
