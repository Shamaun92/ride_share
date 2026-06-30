import type { RideStatus, VehicleType } from "./types";

export const bdt = (poisha: number): string =>
  "৳" + (poisha / 100).toLocaleString("en-BD", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

export const bdtFromTaka = (taka: number | null | undefined): string =>
  taka == null ? "—" : "৳" + taka.toLocaleString("en-BD", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

export const surgeX = (bps: number): string => (bps / 10000).toFixed(2) + "×";

export const km = (n: number): string => n.toFixed(1) + " km";

export const coord = (lat: number, lng: number): string => `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

export const STATUS_LABEL: Record<RideStatus, string> = {
  scheduled: "Scheduled", requested: "Finding a driver", accepted: "Driver assigned",
  arrived: "Driver arrived", in_progress: "On the way", completed: "Completed",
  cancelled: "Cancelled", expired: "Expired",
};

export const VEHICLE_LABEL: Record<VehicleType, string> = { car: "Car", bike: "Bike", cng: "CNG" };

export const timeAgo = (iso: string): string => {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
};
