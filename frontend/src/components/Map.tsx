"use client";

// A self-contained live map: projects lat/lng to an SVG viewport and draws a
// light, street-style basemap with a glowing pickup→dropoff route and an
// animated car marker. No tile/network dependency, so it always renders.
// (Swap for react-leaflet + OSM tiles to put it on real streets — the
// projection seam is isolated in `project()`.)

import { useMemo } from "react";
import type { LivePoint } from "@/lib/ws";

interface Pt { lat: number; lng: number; }
const W = 460, H = 320, PAD = 46;

function project(points: Pt[]) {
  const lats = points.map((p) => p.lat), lngs = points.map((p) => p.lng);
  let minLat = Math.min(...lats), maxLat = Math.max(...lats);
  let minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
  // Avoid zero-span when points coincide.
  const spanLat = Math.max(maxLat - minLat, 0.006), spanLng = Math.max(maxLng - minLng, 0.006);
  const cLat = (minLat + maxLat) / 2, cLng = (minLng + maxLng) / 2;
  minLat = cLat - spanLat / 2; maxLat = cLat + spanLat / 2;
  minLng = cLng - spanLng / 2; maxLng = cLng + spanLng / 2;
  return (p: Pt) => {
    const x = PAD + ((p.lng - minLng) / (maxLng - minLng)) * (W - 2 * PAD);
    const y = PAD + ((maxLat - p.lat) / (maxLat - minLat)) * (H - 2 * PAD); // invert lat
    return { x, y };
  };
}

// Streets are drawn from a fixed pseudo-grid so the basemap looks like a city
// without depending on the (variable) projected coordinates.
const V_STREETS = [40, 92, 150, 214, 286, 348, 410];
const H_STREETS = [46, 104, 168, 236, 292];
const BLOCKS = [
  { x: 96, y: 50, w: 50, h: 46 }, { x: 218, y: 50, w: 64, h: 50 },
  { x: 352, y: 108, w: 54, h: 58 }, { x: 44, y: 172, w: 44, h: 60 },
  { x: 154, y: 172, w: 56, h: 60 }, { x: 290, y: 240, w: 56, h: 46 },
];

export function DispatchMap({
  pickup, dropoff, driver, active,
}: { pickup: Pt; dropoff: Pt; driver: LivePoint | null; active: boolean }) {
  const proj = useMemo(
    () => project([pickup, dropoff, ...(driver ? [driver] : [])]),
    [pickup, dropoff, driver],
  );
  const a = proj(pickup), b = proj(dropoff);
  const d = driver ? proj(driver) : null;

  // Gentle curved route (quadratic bezier bowed perpendicular to the a→b line).
  const midX = (a.x + b.x) / 2, midY = (a.y + b.y) / 2;
  const dx = b.x - a.x, dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const cx = midX - (dy / len) * len * 0.16;
  const cy = midY + (dx / len) * len * 0.16;
  const routePath = `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice"
         className="h-full w-full" role="img" aria-label="Live trip map">
      <defs>
        <linearGradient id="mapfade" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#EEF2F7" />
          <stop offset="1" stopColor="#E4EAF1" />
        </linearGradient>
      </defs>

      {/* basemap */}
      <rect width={W} height={H} fill="url(#mapfade)" />

      {/* park + blocks for texture */}
      <rect x={300} y={44} width={96} height={54} rx={8} fill="#D6E7D8" opacity={0.8} />
      {BLOCKS.map((bl, i) => (
        <rect key={i} x={bl.x} y={bl.y} width={bl.w} height={bl.h} rx={7} fill="#DDE3EC" opacity={0.75} />
      ))}

      {/* streets */}
      <g stroke="#D6DCE6" strokeLinecap="round">
        {V_STREETS.map((x) => <line key={`v${x}`} x1={x} y1={0} x2={x} y2={H} strokeWidth={x === 214 ? 7 : 3} opacity={x === 214 ? 0.9 : 0.7} />)}
        {H_STREETS.map((y) => <line key={`h${y}`} x1={0} y1={y} x2={W} y2={y} strokeWidth={y === 168 ? 7 : 3} opacity={y === 168 ? 0.9 : 0.7} />)}
      </g>
      {/* street centre-lines on the avenues */}
      <g stroke="#EEF2F7" strokeWidth={1.5} strokeDasharray="5 6">
        <line x1={214} y1={0} x2={214} y2={H} />
        <line x1={0} y1={168} x2={W} y2={168} />
      </g>

      {/* route: soft glow under a solid line */}
      <path d={routePath} fill="none" stroke="#0EA5A5" strokeWidth={9} strokeLinecap="round" opacity={0.18} />
      <path d={routePath} fill="none" stroke="#0B1220" strokeWidth={3.5} strokeLinecap="round" />

      {/* pickup — filled dot with ring */}
      <g>
        <circle cx={a.x} cy={a.y} r={9} fill="#fff" style={{ filter: "drop-shadow(0 2px 4px rgba(11,18,32,0.25))" }} />
        <circle cx={a.x} cy={a.y} r={5.5} fill="#0EA5A5" />
        <MapChip x={a.x} y={a.y} text="Pickup" />
      </g>

      {/* dropoff — location pin */}
      <g transform={`translate(${b.x} ${b.y})`}>
        <path d="M0 2 C -7 2 -11 -3.5 -11 -9 C -11 -15 -6 -19 0 -19 C 6 -19 11 -15 11 -9 C 11 -3.5 7 2 0 2 Z"
              fill="#0B1220" style={{ filter: "drop-shadow(0 3px 5px rgba(11,18,32,0.3))" }} />
        <circle cx={0} cy={-9.5} r={4} fill="#F59E0B" />
        <MapChip x={0} y={4} text="Drop-off" />
      </g>

      {/* driver — car marker */}
      {d && (
        <g style={{ transition: "transform 0.9s cubic-bezier(0.4,0,0.2,1)" }} transform={`translate(${d.x} ${d.y})`}>
          {active && <circle r={16} fill="#12B981" className="animate-ping2" style={{ transformBox: "fill-box", transformOrigin: "center" }} />}
          <circle r={12} fill="#0B1220" style={{ filter: "drop-shadow(0 3px 6px rgba(11,18,32,0.4))" }} />
          <circle r={12} fill="none" stroke="#12B981" strokeWidth={2} />
          {/* simple car glyph */}
          <g transform="translate(-7 -6)" fill="#fff">
            <path d="M1 7 L2.4 3.2 C2.7 2.4 3.2 2 4 2 L10 2 C10.8 2 11.3 2.4 11.6 3.2 L13 7 L13 10.5 C13 10.8 12.8 11 12.5 11 L11.5 11 C11.2 11 11 10.8 11 10.5 L11 10 L3 10 L3 10.5 C3 10.8 2.8 11 2.5 11 L1.5 11 C1.2 11 1 10.8 1 10.5 Z" />
            <circle cx="3.6" cy="7.4" r="1.1" fill="#0B1220" />
            <circle cx="10.4" cy="7.4" r="1.1" fill="#0B1220" />
          </g>
        </g>
      )}
    </svg>
  );
}

function MapChip({ x, y, text }: { x: number; y: number; text: string }) {
  const w = text.length * 6.2 + 14;
  return (
    <g transform={`translate(${x} ${y})`}>
      <rect x={-w / 2} y={10} width={w} height={18} rx={9} fill="#0B1220" opacity={0.92} />
      <text x={0} y={22.5} textAnchor="middle" fill="#fff" fontSize={10}
            fontFamily="var(--font-mono)" letterSpacing="0.3">{text}</text>
    </g>
  );
}
