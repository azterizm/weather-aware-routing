import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import type { RouteOption } from '../../api/types';
import { RouteSummaryCard } from './RouteSummaryCard';

const route: RouteOption = {
  id: 'route-2',
  label: 'Route B',
  distance_miles: 798.5,
  duration_seconds: 44_820,
  departure_time: '2026-11-01T02:00:00Z',
  arrival_time: '2026-11-01T14:27:00Z',
  geometry: '_p~iF~ps|U_ulLnnqC',
  summary: {
    miles_by_risk: { LOW: 700, MODERATE: 56, HIGH: 30, SEVERE: 12.5, NO_TRAVEL: 0, UNKNOWN: 0 },
    average_risk: 0.27,
    max_risk: 'SEVERE',
  },
  checkpoints: [],
};

describe('RouteSummaryCard', () => {
  it('shows the ranking criteria and recommendation', () => {
    render(<RouteSummaryCard route={route} recommended selected onSelect={() => {}} />);
    expect(screen.getByText('Route B')).toBeInTheDocument();
    expect(screen.getByText('Recommended')).toBeInTheDocument();
    expect(screen.getByText('798.5 mi')).toBeInTheDocument();
    expect(screen.getByText('12 h 27 min')).toBeInTheDocument();
    expect(screen.getByText('12.5 mi')).toBeInTheDocument();
    expect(screen.getByText('0.27 of 4')).toBeInTheDocument();
    expect(
      screen.getByRole('img', { name: /Miles by risk level\. Low 700 mi, Moderate 56 mi/ }),
    ).toBeInTheDocument();
    // Levels with no miles are left out of the bar legend.
    expect(screen.queryByText(/No Travel 0 mi/)).not.toBeInTheDocument();
  });

  it('selects the route on click', async () => {
    const onSelect = vi.fn();
    render(
      <RouteSummaryCard route={route} recommended={false} selected={false} onSelect={onSelect} />,
    );
    await userEvent.click(screen.getByRole('button', { pressed: false }));
    expect(onSelect).toHaveBeenCalledWith('route-2');
  });
});
