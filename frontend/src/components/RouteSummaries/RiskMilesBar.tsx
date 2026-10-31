import { Box, Stack, Tooltip, Typography } from '@mui/material';

import type { RiskOrUnknown } from '../../api/types';
import { formatMiles } from '../../utils/format';
import { RISK_KEYS, RISK_META } from '../../utils/risk';

interface Props {
  milesByRisk: Record<RiskOrUnknown, number>;
}

/** Stacked bar of route miles per risk level, with a labelled legend (colour is never alone). */
export function RiskMilesBar({ milesByRisk }: Props) {
  const total = RISK_KEYS.reduce((sum, key) => sum + (milesByRisk[key] ?? 0), 0);
  const parts = RISK_KEYS.filter((key) => (milesByRisk[key] ?? 0) > 0);
  const description = parts
    .map((key) => `${RISK_META[key].label} ${formatMiles(milesByRisk[key])}`)
    .join(', ');

  return (
    <Box>
      <Box
        role="img"
        aria-label={`Miles by risk level: ${description}`}
        sx={{ display: 'flex', gap: '2px', height: 12, borderRadius: '4px', overflow: 'hidden' }}
      >
        {parts.map((key) => {
          const miles = milesByRisk[key];
          const share = total > 0 ? (miles / total) * 100 : 0;
          return (
            <Tooltip
              key={key}
              title={`${RISK_META[key].label}: ${formatMiles(miles)} (${share.toFixed(0)}%)`}
            >
              <Box
                sx={{ flexGrow: miles, flexBasis: 0, minWidth: 4, bgcolor: RISK_META[key].color }}
              />
            </Tooltip>
          );
        })}
      </Box>
      <Stack direction="row" sx={{ flexWrap: 'wrap', columnGap: 1.5, rowGap: 0.25, mt: 0.75 }}>
        {parts.map((key) => (
          <Stack key={key} direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
            <Box
              sx={{ width: 10, height: 10, borderRadius: '2px', bgcolor: RISK_META[key].color }}
            />
            <Typography variant="caption" color="text.secondary">
              {RISK_META[key].label} {formatMiles(milesByRisk[key])}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
