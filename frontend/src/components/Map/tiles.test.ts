import type { TileErrorEvent } from 'leaflet';

import { fallbackTileUrl, handleTileError } from './tiles';

function tileError(tile: HTMLImageElement): TileErrorEvent {
  return { tile, coords: { x: 7, y: 12, z: 5 } } as unknown as TileErrorEvent;
}

describe('map tile fallback', () => {
  it('builds the OpenStreetMap URL for the failed tile', () => {
    expect(fallbackTileUrl({ x: 7, y: 12, z: 5 })).toBe(
      'https://tile.openstreetmap.org/5/7/12.png',
    );
  });

  it('switches a failed tile to OpenStreetMap once', () => {
    const tile = document.createElement('img');
    tile.src = '/api/tiles/5/7/12.png';
    handleTileError(tileError(tile));
    expect(tile.src).toBe('https://tile.openstreetmap.org/5/7/12.png');

    // A failure of the fallback itself must not loop.
    tile.src = 'https://example.invalid/other.png';
    handleTileError(tileError(tile));
    expect(tile.src).toBe('https://example.invalid/other.png');
  });
});
