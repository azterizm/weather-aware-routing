import type { TileErrorEvent } from 'leaflet';

/** TomTom tiles through our API, which keeps the TomTom key on the server. */
export const PRIMARY_TILE_URL = '/api/tiles/{z}/{x}/{y}.png';
/** OpenStreetMap tiles, loaded directly for any tile the primary source fails to serve. */
export const FALLBACK_TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.tomtom.com">TomTom</a>, &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
export const MAX_TILE_ZOOM = 18;

export function fallbackTileUrl(coords: { x: number; y: number; z: number }): string {
  return FALLBACK_TILE_URL.replace('{z}', String(coords.z))
    .replace('{x}', String(coords.x))
    .replace('{y}', String(coords.y));
}

/**
 * Reloads a failed primary tile from OpenStreetMap, once per tile. Leaflet marks the tile as
 * loaded when the fallback image arrives.
 */
export function handleTileError(event: TileErrorEvent): void {
  const tile = event.tile as HTMLImageElement;
  if (tile.dataset.fallback) return;
  tile.dataset.fallback = 'true';
  tile.src = fallbackTileUrl(event.coords);
}
