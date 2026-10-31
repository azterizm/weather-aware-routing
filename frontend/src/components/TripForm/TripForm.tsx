import { Button, InputAdornment, Stack, TextField } from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import dayjs, { type Dayjs } from 'dayjs';
import { type FormEvent, useState } from 'react';

import type { PlaceOption, TripPlanRequest } from '../../api/types';
import { browserTimeZone } from '../../utils/format';
import { PlaceAutocomplete } from './PlaceAutocomplete';
import { type FieldErrors, MAX_DAYS_AHEAD, MAX_LOAD_LBS, validateTrip } from './validation';

interface Props {
  onSubmit: (request: TripPlanRequest) => void;
  submitting: boolean;
  /** Field errors returned by the API for the last submission. */
  serverErrors?: FieldErrors;
}

function defaultDeparture(): Dayjs {
  // Next quarter hour, at least 15 minutes from now.
  const soon = dayjs().add(15, 'minute');
  return soon
    .minute(Math.ceil(soon.minute() / 15) * 15)
    .second(0)
    .millisecond(0);
}

export function TripForm({ onSubmit, submitting, serverErrors = {} }: Props) {
  const [origin, setOrigin] = useState<PlaceOption | null>(null);
  const [destination, setDestination] = useState<PlaceOption | null>(null);
  const [departure, setDeparture] = useState<Dayjs | null>(defaultDeparture);
  const [load, setLoad] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitted, setSubmitted] = useState(false);

  const shownErrors = { ...serverErrors, ...errors };

  function revalidate(next: Partial<Parameters<typeof validateTrip>[0]>) {
    if (submitted) setErrors(validateTrip({ origin, destination, departure, load, ...next }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    const found = validateTrip({ origin, destination, departure, load });
    setErrors(found);
    if (Object.keys(found).length > 0 || !origin || !destination || !departure) return;
    onSubmit({
      origin,
      destination,
      departure_time: departure.toISOString(),
      load_weight_lbs: Number(load),
    });
  }

  return (
    <Stack
      component="form"
      spacing={1}
      onSubmit={handleSubmit}
      noValidate
      aria-label="Trip details"
    >
      <PlaceAutocomplete
        label="Origin"
        value={origin}
        onChange={(value) => {
          setOrigin(value);
          revalidate({ origin: value });
        }}
        error={shownErrors.origin}
      />
      <PlaceAutocomplete
        label="Destination"
        value={destination}
        onChange={(value) => {
          setDestination(value);
          revalidate({ destination: value });
        }}
        error={shownErrors.destination}
      />
      <DateTimePicker
        label="Departure"
        value={departure}
        onChange={(value) => {
          setDeparture(value);
          revalidate({ departure: value });
        }}
        disablePast
        maxDateTime={dayjs().add(MAX_DAYS_AHEAD, 'day')}
        slotProps={{
          textField: {
            required: true,
            error: Boolean(shownErrors.departure_time),
            helperText: shownErrors.departure_time ?? `Time zone: ${browserTimeZone}`,
          },
        }}
      />
      <TextField
        label="Load weight"
        value={load}
        onChange={(event) => {
          setLoad(event.target.value);
          revalidate({ load: event.target.value });
        }}
        required
        type="number"
        error={Boolean(shownErrors.load_weight_lbs)}
        helperText={shownErrors.load_weight_lbs ?? ' '}
        slotProps={{
          input: { endAdornment: <InputAdornment position="end">lb</InputAdornment> },
          htmlInput: { min: 1, max: MAX_LOAD_LBS, step: 100, inputMode: 'numeric' },
        }}
      />
      <Button type="submit" variant="contained" size="large" loading={submitting}>
        Find routes
      </Button>
    </Stack>
  );
}
