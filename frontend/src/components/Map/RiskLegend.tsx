import { Box, Stack, Typography } from '@mui/material';

import { formatPounds } from '../../utils/format';
import { RISK_KEYS, RISK_META } from '../../utils/risk';

export function RiskLegend({ loadLbs }: { loadLbs: number | undefined }) {
  return (
    <Box component="section" aria-label="Risk legend" sx={{ flex: '0 1 auto' }}>
      <Stack direction="row" sx={{ flexWrap: 'wrap', columnGap: 1.25, rowGap: 0.5 }}>
        {RISK_KEYS.map((key) => (
          <Stack key={key} direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
            <Box
              sx={{ width: 12, height: 12, borderRadius: '2px', bgcolor: RISK_META[key].color }}
            />
            <Typography variant="caption">{RISK_META[key].label}</Typography>
          </Stack>
        ))}
      </Stack>
      {loadLbs !== undefined && (
        <Typography variant="caption" color="text.secondary">
          Risk for a {formatPounds(loadLbs)} load (wind, rain, snow and load rules)
        </Typography>
      )}
    </Box>
  );
}
