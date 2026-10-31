import type { LatLngTuple } from 'leaflet';

import {
  neighbourVertices,
  offsetLine,
  rightNormal,
  ROUTE_SPACING_PX,
  routeOffset,
} from './offset';

describe('routeOffset', () => {
  it('centres the routes on the road', () => {
    expect([0, 1, 2].map((i) => routeOffset(i, 3))).toEqual([
      -ROUTE_SPACING_PX,
      0,
      ROUTE_SPACING_PX,
    ]);
    expect([0, 1].map((i) => routeOffset(i, 2))).toEqual([
      -ROUTE_SPACING_PX / 2,
      ROUTE_SPACING_PX / 2,
    ]);
    expect(routeOffset(0, 1)).toBe(0);
  });
});

describe('neighbourVertices', () => {
  const line: LatLngTuple[] = [
    [35, -100],
    [35, -99],
    [36, -99],
  ];

  it('returns the vertices around the nearest one', () => {
    expect(neighbourVertices(line, [35.01, -99.02])).toEqual([
      [35, -100],
      [36, -99],
    ]);
  });

  it('clamps at the ends of the line', () => {
    expect(neighbourVertices(line, [35, -100])).toEqual([
      [35, -100],
      [35, -99],
    ]);
    expect(neighbourVertices(line, [36, -99])).toEqual([
      [35, -99],
      [36, -99],
    ]);
  });

  it('needs at least 2 vertices', () => {
    expect(neighbourVertices([[35, -100]], [35, -100])).toBeNull();
  });
});

describe('offsetLine', () => {
  it('uses the right-hand side of travel in screen space', () => {
    // Travelling east on screen, right is down (+y).
    expect(rightNormal({ x: 0, y: 0 }, { x: 10, y: 0 })).toEqual({ x: -0, y: 1 });
    expect(rightNormal({ x: 0, y: 0 }, { x: 0, y: 0 })).toBeNull();
  });

  it('shifts a straight line parallel to itself', () => {
    const line = offsetLine(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 20, y: 0 },
      ],
      6,
    );
    expect(line.map((p) => p.y)).toEqual([6, 6, 6]);
    expect(line.map((p) => p.x)).toEqual([0, 10, 20]);
  });

  it('keeps the offset distance from both legs of a right-angle corner', () => {
    const [, corner] = offsetLine(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 10, y: 10 },
      ],
      4,
    );
    // East then south: the right-hand side is inside the corner.
    expect(corner!.x).toBeCloseTo(6);
    expect(corner!.y).toBeCloseTo(4);
  });

  it('caps the spike on a hairpin turn', () => {
    const [, tip] = offsetLine(
      [
        { x: 0, y: 0 },
        { x: 10, y: 0 },
        { x: 0, y: 0.5 },
      ],
      6,
    );
    expect(Math.hypot(tip!.x - 10, tip!.y)).toBeLessThanOrEqual(12 + 1e-9);
  });

  it('leaves the line unchanged without an offset', () => {
    const points = [
      { x: 0, y: 0 },
      { x: 5, y: 5 },
    ];
    expect(offsetLine(points, 0)).toBe(points);
  });
});
