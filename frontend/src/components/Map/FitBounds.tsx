import L, { type LatLngTuple } from 'leaflet';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

const OVERLAY_HEIGHT_PX = 150;

/** Fits the map to the given lines whenever they change (i.e. for each new plan). */
export function FitBounds({ lines }: { lines: LatLngTuple[][] }) {
  const map = useMap();
  useEffect(() => {
    const points = lines.flat();
    if (points.length > 0) {
      // Extra bottom padding keeps the routes clear of the slider/legend overlay.
      map.fitBounds(L.latLngBounds(points), {
        paddingTopLeft: [32, 32],
        paddingBottomRight: [32, OVERLAY_HEIGHT_PX],
      });
    }
  }, [map, lines]);
  return null;
}
