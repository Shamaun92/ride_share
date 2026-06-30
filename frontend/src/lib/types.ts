// Mirrors the backend JSON schemas (snake_case as sent over the wire).

export type UserRole = "rider" | "driver" | "admin";
export type VehicleType = "car" | "bike" | "cng";
export type PaymentMethod = "cash" | "wallet";
export type RideStatus =
  | "scheduled" | "requested" | "accepted" | "arrived"
  | "in_progress" | "completed" | "cancelled" | "expired";

export interface TokenPair { access_token: string; refresh_token: string; token_type: string; }

export interface User {
  id: string; email: string; phone: string; full_name: string;
  role: UserRole; is_active: boolean;
}

export interface VehicleSummary {
  vehicle_type: VehicleType; make: string; model: string; color: string; license_plate: string;
}
export interface DriverSummary {
  driver_id: string; full_name: string; rating_avg: number;
  current_lat: number | null; current_lng: number | null; vehicle: VehicleSummary | null;
}

export interface Ride {
  id: string; rider_id: string; driver_id: string | null;
  status: RideStatus; vehicle_type: VehicleType; payment_method: PaymentMethod;
  pickup_lat: number; pickup_lng: number; pickup_address: string;
  dropoff_lat: number; dropoff_lng: number; dropoff_address: string;
  distance_km: number; estimated_fare: number | null; final_fare: number | null;
  discount_poisha: number; surge_bps: number; is_shared: boolean;
  scheduled_for: string | null;
  cancelled_by: string | null; cancellation_reason: string | null;
  accepted_at: string | null; arrived_at: string | null; started_at: string | null;
  completed_at: string | null; cancelled_at: string | null; created_at: string;
  driver: DriverSummary | null;
}
export interface RideRequestResult { ride: Ride; drivers_notified: number; }

export interface RideRequestCreate {
  pickup_lat: number; pickup_lng: number; pickup_address: string;
  dropoff_lat: number; dropoff_lng: number; dropoff_address: string;
  vehicle_type: VehicleType; payment_method: PaymentMethod;
  scheduled_for?: string | null; promo_code?: string | null; shared?: boolean;
}

export interface Wallet { id: string; balance_poisha: number; balance_bdt: number; currency: string; }
export interface LedgerEntry { id: string; account: string; amount_poisha: number; amount_bdt: number; created_at: string; }
export interface WalletStatement { wallet: Wallet; entries: LedgerEntry[]; }

export interface PaymentRead {
  id: string; ride_id: string; method: PaymentMethod; status: string;
  amount_poisha: number; commission_poisha: number; driver_earnings_poisha: number;
  breakdown: Record<string, number | string> | null; created_at: string;
}
export interface RatingRead { id: string; ride_id: string; rater_role: string; score: number; comment: string | null; created_at: string; }
export interface RideReceipt { ride_id: string; distance_km: number; final_fare_bdt: number | null; payment: PaymentRead | null; my_rating: RatingRead | null; }

export interface Notification {
  id: string; kind: string; title: string; body: string;
  data: Record<string, unknown> | null; ride_id: string | null; is_read: boolean; created_at: string;
}
export interface NotificationList { unread: number; items: Notification[]; }

export interface SurgeQuote { surge_bps: number; surge_multiplier: number; }
export interface PromoQuoteResult { code: string; discount_poisha: number; discount_bdt: number; fare_after_poisha: number; }

export interface AdminMetrics {
  rides_by_status: Record<string, number>; total_rides: number;
  platform_revenue_poisha: number; promo_expense_poisha: number;
  active_drivers: number; total_users: number;
}

// WebSocket envelope
export type WsEventType = "snapshot" | "location" | "ride_status" | "notification" | "pong" | "error";
export interface WsEvent<T = Record<string, unknown>> { type: WsEventType; data: T; ts: string; }
