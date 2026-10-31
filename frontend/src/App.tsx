import { Alert, AppBar, Box, Skeleton, Stack, Toolbar, Typography } from '@mui/material';
import { lazy, Suspense, useCallback, useState } from 'react';

import { ApiError, errorMessage } from './api/client';
import type { TripPlan, TripPlanRequest } from './api/types';
import { RouteSummaries } from './components/RouteSummaries/RouteSummaries';
import { TripForm } from './components/TripForm/TripForm';
import type { FieldErrors } from './components/TripForm/validation';
import { useCorridorWeather } from './hooks/useCorridorWeather';
import { useTripPlan } from './hooks/useTripPlan';

// Leaflet is the heaviest dependency; loading it separately gets the form on screen sooner.
const TripMap = lazy(() => import('./components/Map/TripMap'));

export default function App() {
  const [request, setRequest] = useState<TripPlanRequest | null>(null);
  const plan = useTripPlan(request);
  const corridor = useCorridorWeather(plan.data);

  // Selection resets to the recommended route whenever a new plan arrives.
  const [selection, setSelection] = useState<{ plan: TripPlan | undefined; routeId: string }>({
    plan: undefined,
    routeId: '',
  });
  const selectedRouteId =
    plan.data && selection.plan === plan.data ? selection.routeId : plan.data?.recommended_route_id;
  const selectRoute = useCallback(
    (routeId: string) => setSelection({ plan: plan.data, routeId }),
    [plan.data],
  );

  const serverErrors: FieldErrors = plan.error instanceof ApiError ? plan.error.fields : {};

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100dvh' }}>
      <AppBar position="static" elevation={0}>
        <Toolbar variant="dense">
          <Typography variant="h1" component="h1">
            Weather-Aware Truck Routing
          </Typography>
        </Toolbar>
      </AppBar>
      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
        }}
      >
        <Box
          component="aside"
          sx={{
            width: { md: 440 },
            flexShrink: 0,
            overflowY: { md: 'auto' },
            p: 2,
            borderRight: { md: 1 },
            borderColor: { md: 'divider' },
            bgcolor: 'background.paper',
          }}
        >
          <Stack spacing={2}>
            <TripForm
              onSubmit={setRequest}
              submitting={plan.isFetching}
              serverErrors={serverErrors}
            />
            {plan.isError && <Alert severity="error">{errorMessage(plan.error)}</Alert>}
            {plan.isFetching && (
              <Typography variant="body2" color="text.secondary" role="status">
                Finding routes and sampling the weather along each one…
              </Typography>
            )}
            {!request && (
              <Typography variant="body2" color="text.secondary">
                Enter a trip to compare 3 truck routes by weather risk and travel time.
              </Typography>
            )}
            {plan.data && selectedRouteId && !plan.isFetching && (
              <RouteSummaries
                plan={plan.data}
                selectedRouteId={selectedRouteId}
                onSelectRoute={selectRoute}
              />
            )}
          </Stack>
        </Box>
        <Box component="main" sx={{ flex: 1, minHeight: { xs: '75vh', md: 0 } }}>
          <Suspense fallback={<Skeleton variant="rectangular" height="100%" />}>
            <TripMap
              plan={plan.data}
              endpoints={
                request ? { origin: request.origin, destination: request.destination } : undefined
              }
              corridor={{
                data: corridor.data,
                loading: corridor.isFetching,
                error: corridor.isError ? errorMessage(corridor.error) : null,
              }}
              selectedRouteId={selectedRouteId}
              onSelectRoute={selectRoute}
            />
          </Suspense>
        </Box>
      </Box>
    </Box>
  );
}
