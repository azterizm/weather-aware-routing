import { createTheme } from '@mui/material/styles';

export const ROUTE_COLORS = {
  selected: '#1c5cab',
  other: '#6b7280',
} as const;

export const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: ROUTE_COLORS.selected },
    background: { default: '#f5f6f8', paper: '#ffffff' },
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    h1: { fontSize: '1.25rem', fontWeight: 600 },
  },
  components: {
    MuiCard: { defaultProps: { variant: 'outlined' } },
  },
});
