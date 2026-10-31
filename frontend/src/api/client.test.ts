import { AxiosError, AxiosHeaders, CanceledError } from 'axios';

import { ApiError, flattenFieldErrors, toApiError } from './client';

function axiosError(status: number | undefined, data: unknown, code?: string) {
  const config = { headers: new AxiosHeaders() };
  const response =
    status === undefined ? undefined : { status, data, statusText: '', headers: {}, config };
  return new AxiosError('failed', code, config, undefined, response);
}

describe('toApiError', () => {
  it('uses the backend error body', () => {
    const error = toApiError(
      axiosError(400, {
        detail: 'Please correct the highlighted fields.',
        code: 'invalid',
        fields: { load_weight_lbs: ['Ensure this value is less than or equal to 80000.'] },
      }),
    );
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(400);
    expect((error as ApiError).fields).toEqual({
      load_weight_lbs: 'Ensure this value is less than or equal to 80000.',
    });
  });

  it('maps upstream failures with their message', () => {
    const error = toApiError(
      axiosError(503, {
        detail: 'The routing provider is unavailable.',
        code: 'upstream_unavailable',
      }),
    ) as ApiError;
    expect(error.message).toBe('The routing provider is unavailable.');
    expect(error.code).toBe('upstream_unavailable');
  });

  it('maps timeouts and network failures', () => {
    expect((toApiError(axiosError(undefined, null, 'ECONNABORTED')) as ApiError).code).toBe(
      'timeout',
    );
    expect((toApiError(axiosError(undefined, null)) as ApiError).code).toBe('network');
  });

  it('passes cancellations through untouched', () => {
    const cancel = new CanceledError();
    expect(toApiError(cancel)).toBe(cancel);
  });
});

describe('flattenFieldErrors', () => {
  it('keeps the first message per top-level field, including nested ones', () => {
    expect(
      flattenFieldErrors({
        origin: { lat: ['Ensure this value is less than or equal to 90.'] },
        departure_time: ['Departure time cannot be in the past.', 'second'],
      }),
    ).toEqual({
      origin: 'Ensure this value is less than or equal to 90.',
      departure_time: 'Departure time cannot be in the past.',
    });
  });
});
