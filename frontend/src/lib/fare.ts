// Client-side fare projection mirroring the backend pricing engine, used only
// for a live pre-request estimate. The authoritative fare comes from the API.
import type { VehicleType } from "./types";

const BASE = 5000, PER_KM = 3000, PER_MIN = 200, BOOKING = 1000, MIN = 6000, SPEED = 20;
const VEHICLE_BPS: Record<VehicleType, number> = { bike: 6000, cng: 8000, car: 10000 };
const POOL_DISCOUNT_BPS = 2500;

export function estimatePoisha(distanceKm: number, vehicle: VehicleType, surgeBps: number, shared: boolean): number {
  const durationMin = (distanceKm / SPEED) * 60;
  const subtotal = BOOKING + BASE + Math.round(PER_KM * distanceKm) + Math.round(PER_MIN * durationMin);
  let total = Math.floor((Math.floor((subtotal * VEHICLE_BPS[vehicle]) / 10000) * surgeBps) / 10000);
  total = Math.max(total, MIN);
  if (shared) total = Math.floor((total * (10000 - POOL_DISCOUNT_BPS)) / 10000);
  return total;
}

// Haversine, km
export function distanceKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371, toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(bLat - aLat), dLng = toRad(bLng - aLng);
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(aLat)) * Math.cos(toRad(bLat)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
