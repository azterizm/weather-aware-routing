import axios, { type AxiosError } from 'axios';

import type { ApiErrorBody } from './types';

/** A failed API call, normalised from the backend's `{detail, code, fields}` error body. */
export class ApiError extends Error {
  readonly status: number | undefined;
  readonly code: string;
  readonly fields: Record<string, string>;

  constructor(message: string, code: string, status?: number, fields: Record<string, string> = {}) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

/** Flatten DRF field errors (`{origin: {lat: ["..."]}}`) to the first message per top-level field. */
export function flattenFieldErrors(
  fields: Record<string, unknown> | undefined,
): Record<string, string> {
  const first = (value: unknown): string | undefined => {
    if (typeof value === 'string') return value;
    if (Array.isArray(value)) return value.map(first).find(Boolean);
    if (value && typeof value === 'object') return Object.values(value).map(first).find(Boolean);
    return undefined;
  };
  const result: Record<string, string> = {};
  for (const [field, value] of Object.entries(fields ?? {})) {
    const message = first(value);
    if (message) result[field] = message;
  }
  return result;
}

export function toApiError(error: unknown): unknown {
  if (axios.isCancel(error) || !axios.isAxiosError(error)) return error;
  const axiosError = error as AxiosError<Partial<ApiErrorBody>>;
  const response = axiosError.response;
  if (response?.data && typeof response.data.detail === 'string') {
    return new ApiError(
      response.data.detail,
      response.data.code ?? 'error',
      response.status,
      flattenFieldErrors(response.data.fields),
    );
  }
  if (axiosError.code === 'ECONNABORTED' || axiosError.code === 'ETIMEDOUT') {
    return new ApiError('The server took too long to respond. Please try again.', 'timeout');
  }
  if (response) {
    return new ApiError(
      `The server returned an unexpected error with status ${response.status}.`,
      'server_error',
      response.status,
    );
  }
  return new ApiError('Cannot reach the server. Check your connection and try again.', 'network');
}

export const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { Accept: 'application/json' },
});

http.interceptors.response.use(undefined, (error: unknown) => Promise.reject(toApiError(error)));

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
