/**
 * Side-by-side drawing for routes that share a road. Each route is shifted a fixed number of
 * screen pixels to the right of its direction of travel, so overlapping routes show as parallel
 * lines. Checkpoint dots get the same shift so they stay on their own route's line.
 */
import {
  createElementObject,
  createPathComponent,
  extendContext,
  updateCircle,
} from '@react-leaflet/core';
import L, { type LatLngExpression, type LatLngTuple } from 'leaflet';
import type { ReactNode } from 'react';

/** Pixels between the centre lines of neighbouring routes. */
export const ROUTE_SPACING_PX = 6;
/** Projected lines are simplified to this tolerance before offsetting, so tiny zigzags
 * at low zoom cannot fold the offset line into loops. */
const SIMPLIFY_PX = 1.5;
/** Caps the corner extension on sharp turns, as a multiple of the offset. */
const MITER_LIMIT = 2;

/** Pixel offset for route `index` of `count`, centred on the road. */
export function routeOffset(index: number, count: number): number {
  return (index - (count - 1) / 2) * ROUTE_SPACING_PX;
}

interface Vec {
  x: number;
  y: number;
}

/** Unit normal to the right of travel from `a` to `b` in screen space (y points down). */
export function rightNormal(a: Vec, b: Vec): Vec | null {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = Math.hypot(dx, dy);
  return length === 0 ? null : { x: -dy / length, y: dx / length };
}

/** Offsets a screen-space line by `distance` px to the right, with capped miter joins. */
export function offsetLine(points: Vec[], distance: number): Vec[] {
  if (points.length < 2 || distance === 0) return points;
  const normals = points.slice(1).map((p, i) => rightNormal(points[i]!, p));
  return points.map((p, i) => {
    const before = normals[i - 1] ?? null;
    const after = normals[i] ?? null;
    const n1 = before ?? after;
    const n2 = after ?? before;
    if (!n1 || !n2) return p;
    const mx = n1.x + n2.x;
    const my = n1.y + n2.y;
    const mLength = Math.hypot(mx, my);
    if (mLength < 1e-9) return { x: p.x + n2.x * distance, y: p.y + n2.y * distance };
    const ux = mx / mLength;
    const uy = my / mLength;
    const scale = Math.min(distance / (ux * n2.x + uy * n2.y), MITER_LIMIT * Math.abs(distance));
    return { x: p.x + ux * scale, y: p.y + uy * scale };
  });
}

/** The route vertices just before and after the vertex nearest to `point`. */
export function neighbourVertices(
  line: LatLngTuple[],
  point: LatLngTuple,
): [LatLngTuple, LatLngTuple] | null {
  if (line.length < 2) return null;
  let nearest = 0;
  let best = Infinity;
  for (let i = 0; i < line.length; i++) {
    const [lat, lon] = line[i]!;
    const d = (lat - point[0]) ** 2 + (lon - point[1]) ** 2;
    if (d < best) {
      best = d;
      nearest = i;
    }
  }
  const before = line[Math.max(0, nearest - 1)]!;
  const after = line[Math.min(line.length - 1, nearest + 1)]!;
  return [before, after];
}

// --- Leaflet layers ----------------------------------------------------------------------

type ProjectedPolyline = L.Polyline & {
  _map: L.Map;
  options: L.PolylineOptions & { offset?: number };
};

function projectWithOffset(
  this: ProjectedPolyline,
  latlngs: L.LatLng[] | L.LatLng[][],
  result: L.Point[][],
  projectedBounds: L.Bounds,
): void {
  if (!(latlngs[0] instanceof L.LatLng)) {
    for (const ring of latlngs as L.LatLng[][]) {
      projectWithOffset.call(this, ring, result, projectedBounds);
    }
    return;
  }
  const projected = (latlngs as L.LatLng[]).map((ll) => {
    const point = this._map.latLngToLayerPoint(ll);
    projectedBounds.extend(point);
    return point;
  });
  const offset = this.options.offset ?? 0;
  const simplified = offset ? L.LineUtil.simplify(projected, SIMPLIFY_PX) : projected;
  result.push(offsetLine(simplified, offset).map((p) => L.point(p.x, p.y)));
}

const OffsetPolylineClass = L.Polyline.extend({
  _projectLatlngs: projectWithOffset,
}) as unknown as new (
  positions: LatLngExpression[],
  options: L.PolylineOptions & { offset?: number },
) => L.Polyline;

interface MarkerOffsetOptions extends L.CircleMarkerOptions {
  offset?: number;
  /** Route vertices around the marker; their direction sets which side the offset goes. */
  direction?: [LatLngTuple, LatLngTuple] | null;
}

const OffsetCircleMarkerClass = L.CircleMarker.extend({
  _project(
    this: L.CircleMarker & {
      _point: L.Point;
      _map: L.Map;
      options: MarkerOffsetOptions;
      _updateBounds(): void;
    },
  ) {
    const center = this._map.latLngToLayerPoint(this.getLatLng());
    const { offset, direction } = this.options;
    this._point = center;
    if (offset && direction) {
      const normal = rightNormal(
        this._map.latLngToLayerPoint(direction[0]),
        this._map.latLngToLayerPoint(direction[1]),
      );
      if (normal) this._point = L.point(center.x + normal.x * offset, center.y + normal.y * offset);
    }
    this._updateBounds();
  },
}) as unknown as new (center: LatLngExpression, options: MarkerOffsetOptions) => L.CircleMarker;

// --- react-leaflet components ------------------------------------------------------------

export interface OffsetPolylineProps {
  positions: LatLngExpression[];
  offset: number;
  /** Set by react-leaflet from the enclosing <Pane>. */
  pane?: string;
  pathOptions?: L.PathOptions;
  eventHandlers?: L.LeafletEventHandlerFnMap;
  children?: ReactNode;
}

/** A react-leaflet Polyline drawn `offset` px to the right of its direction of travel. */
export const OffsetPolyline = createPathComponent<L.Polyline, OffsetPolylineProps>(
  function createOffsetPolyline({ positions, offset, pane, pathOptions }, ctx) {
    const line = new OffsetPolylineClass(positions, {
      ...pathOptions,
      ...(pane ? { pane } : {}),
      offset,
    });
    return createElementObject(line, extendContext(ctx, { overlayContainer: line }));
  },
  function updateOffsetPolyline(line, props, prevProps) {
    if (props.positions !== prevProps.positions) line.setLatLngs(props.positions);
    if (props.offset !== prevProps.offset) {
      Object.assign(line.options, { offset: props.offset });
      line.redraw(); // re-projects, applying the new offset
    }
  },
);

export interface OffsetCircleMarkerProps extends MarkerOffsetOptions {
  center: LatLngExpression;
  children?: ReactNode;
  eventHandlers?: L.LeafletEventHandlerFnMap;
  pathOptions?: L.PathOptions;
}

/** A react-leaflet CircleMarker drawn with the same offset as its route. */
export const OffsetCircleMarker = createPathComponent<L.CircleMarker, OffsetCircleMarkerProps>(
  function createOffsetCircleMarker(props, ctx) {
    const { center, offset, direction, pane, pathOptions } = props;
    const marker = new OffsetCircleMarkerClass(center, {
      ...pathOptions,
      // react-leaflet supplies the enclosing <Pane> here; without it the dots land under routes.
      ...(pane ? { pane } : {}),
      radius: props.radius,
      offset,
      direction,
    });
    return createElementObject(marker, extendContext(ctx, { overlayContainer: marker }));
  },
  function updateOffsetCircleMarker(marker, props, prevProps) {
    updateCircle(marker, props, prevProps);
    if (props.offset !== prevProps.offset || props.direction !== prevProps.direction) {
      Object.assign(marker.options, { offset: props.offset, direction: props.direction });
      marker.redraw(); // re-projects, applying the new offset
    }
  },
);
