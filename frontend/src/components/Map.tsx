"use client";

// A self-contained live "dispatch map": projects lat/lng to an SVG viewport,
// draws the pickup→dropoff route and an animated driver ping. No tile/network
// dependency, so it always renders. (Swap for react-leaflet + OSM tiles to put
// it on real streets — the projection seam is isolated here.)

import { useMemo } from "react";
import type { LivePoint } from "@/lib/ws";

interface Pt { lat: number; lng: number; }
const W = 460, H = 300, PAD = 34;

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

export function DispatchMap({
  pickup, dropoff, driver, active,
}: { pickup: Pt; dropoff: Pt; driver: LivePoint | null; active: boolean }) {
  const proj = useMemo(
    () => project([pickup, dropoff, ...(driver ? [driver] : [])]),
    [pickup, dropoff, driver],
  );
  const a = proj(pickup), b = proj(dropoff);
  const d = driver ? proj(driver) : null;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full" role="img" aria-label="Live trip map">
      <rect width={W} height={H} fill="#0D1522" />
      <g className="console-grid" opacity={0.9}>
        <rect width={W} height={H} fill="transparent" />
      </g>

      {/* route */}
      <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#0FA3A3" strokeWidth={2.5}
            strokeDasharray="2 7" strokeLinecap="round" opacity={0.75} />

      {/* pickup */}
      <g>
        <circle cx={a.x} cy={a.y} r={6} fill="#16C172" />
        <circle cx={a.x} cy={a.y} r={6} fill="none" stroke="#16C172" strokeWidth={1.5} opacity={0.5} />
        <text x={a.x + 10} y={a.y + 4} fill="#9FB0C8" fontSize={10} fontFamily="var(--font-mono)">PICKUP</text>
      </g>

      {/* dropoff */}
      <g>
        <rect x={b.x - 5} y={b.y - 5} width={10} height={10} rx={2} fill="#F6A623" />
        <text x={b.x + 10} y={b.y + 4} fill="#9FB0C8" fontSize={10} fontFamily="var(--font-mono)">DROPOFF</text>
      </g>

      {/* driver ping */}
      {d && (
        <g style={{ transition: "transform 0.8s ease" }} transform={`translate(${d.x} ${d.y})`}>
          {active && <circle r={9} fill="#16C172" className="animate-ping2" style={{ transformBox: "fill-box", transformOrigin: "center" }} />}
          <circle r={6.5} fill="#ffffff" />
          <circle r={4} fill="#16C172" />
        </g>
      )}
    </svg>
  );
}
