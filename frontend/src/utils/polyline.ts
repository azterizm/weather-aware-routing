import polyline from '@mapbox/polyline';
import type { LatLngTuple } from 'leaflet';

/** Decode a Google encoded polyline (precision 5) into Leaflet [lat, lng] tuples. */
export function decodePolyline(encoded: string): LatLngTuple[] {
  return polyline.decode(encoded, 5) as LatLngTuple[];
}
