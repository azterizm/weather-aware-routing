import { Autocomplete, CircularProgress, TextField } from '@mui/material';
import { useState } from 'react';

import type { PlaceOption } from '../../api/types';
import { MIN_QUERY_LENGTH, usePlaceSearch } from '../../hooks/usePlaceSearch';

interface Props {
  label: string;
  value: PlaceOption | null;
  onChange: (value: PlaceOption | null) => void;
  error?: string;
  disabled?: boolean;
}

const optionKey = (option: PlaceOption) => `${option.label}|${option.lat}|${option.lon}`;

/** Place picker backed by the geocoding API; a suggestion must be selected. */
export function PlaceAutocomplete({ label, value, onChange, error, disabled }: Props) {
  const [input, setInput] = useState(value?.label ?? '');
  const search = usePlaceSearch(input);
  const tooShort = input.trim().length < MIN_QUERY_LENGTH;
  const options = tooShort ? [] : (search.data ?? []);

  return (
    <Autocomplete
      value={value}
      onChange={(_, next) => onChange(next)}
      inputValue={input}
      onInputChange={(_, next) => setInput(next)}
      options={
        value && !options.some((o) => optionKey(o) === optionKey(value))
          ? [value, ...options]
          : options
      }
      filterOptions={(x) => x}
      getOptionLabel={(option) => option.label}
      getOptionKey={optionKey}
      isOptionEqualToValue={(a, b) => optionKey(a) === optionKey(b)}
      loading={search.isFetching}
      noOptionsText={
        tooShort
          ? `Type at least ${MIN_QUERY_LENGTH} characters`
          : search.isError
            ? 'Place search is unavailable'
            : 'No places found'
      }
      disabled={disabled}
      autoComplete
      includeInputInList
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          required
          error={Boolean(error)}
          helperText={error ?? ' '}
          slotProps={{
            ...params.slotProps,
            input: {
              ...params.slotProps.input,
              endAdornment: (
                <>
                  {search.isFetching ? <CircularProgress color="inherit" size={18} /> : null}
                  {params.slotProps.input.endAdornment}
                </>
              ),
            },
          }}
        />
      )}
    />
  );
}
