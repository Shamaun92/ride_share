// Typed fetch client for the Shohojatri backend.
import type {
  AdminMetrics, NotificationList, PromoQuoteResult, Ride, RideReceipt,
  RideRequestCreate, RideRequestResult, SurgeQuote, TokenPair, User,
  WalletStatement,
} from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";
export const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? "ws://localhost:8000/api/v1/ws";

const ACCESS_KEY = "shj.access";
const REFRESH_KEY = "shj.refresh";

export const tokenStore = {
  get access() { return typeof window === "undefined" ? null : localStorage.getItem(ACCESS_KEY); },
  get refresh() { return typeof window === "undefined" ? null : localStorage.getItem(REFRESH_KEY); },
  set(pair: TokenPair) {
    localStorage.setItem(ACCESS_KEY, pair.access_token);
    localStorage.setItem(REFRESH_KEY, pair.refresh_token);
  },
  clear() { localStorage.removeItem(ACCESS_KEY); localStorage.removeItem(REFRESH_KEY); },
};

export class ApiError extends Error {
  constructor(public status: number, public detail: string) { super(detail); }
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length && typeof d[0] === "object" && d[0] && "msg" in d[0])
      return String((d[0] as { msg: unknown }).msg);
  }
  return fallback;
}

async function raw<T>(path: string, init: RequestInit, auth: boolean): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (auth && tokenStore.access) headers.set("Authorization", `Bearer ${tokenStore.access}`);
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detailOf(body, res.statusText));
  return body as T;
}

async function refresh(): Promise<boolean> {
  const rt = tokenStore.refresh;
  if (!rt) return false;
  try {
    const pair = await raw<TokenPair>("/auth/refresh", { method: "POST", body: JSON.stringify({ refresh_token: rt }) }, false);
    tokenStore.set(pair);
    return true;
  } catch {
    tokenStore.clear();
    return false;
  }
}

// Authenticated request with a single transparent token refresh on 401.
async function authed<T>(path: string, init: RequestInit = {}): Promise<T> {
  try {
    return await raw<T>(path, init, true);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && (await refresh())) {
      return raw<T>(path, init, true);
    }
    throw e;
  }
}

const J = (b: unknown) => JSON.stringify(b);

export const api = {
  // auth
  login: (identifier: string, password: string) =>
    raw<TokenPair>("/auth/login", { method: "POST", body: J({ identifier, password }) }, false),
  registerRider: (b: { email: string; phone: string; full_name: string; password: string }) =>
    raw<User>("/auth/register", { method: "POST", body: J(b) }, false),
  me: () => authed<User>("/users/me"),

  // rides
  requestRide: (b: RideRequestCreate) => authed<RideRequestResult>("/rides", { method: "POST", body: J(b) }),
  getRide: (id: string) => authed<Ride>(`/rides/${id}`),
  listRides: () => authed<Ride[]>("/rides"),
  cancelRide: (id: string, reason?: string) =>
    authed<Ride>(`/rides/${id}/cancel`, { method: "POST", body: J({ reason: reason ?? null }) }),
  receipt: (id: string) => authed<RideReceipt>(`/rides/${id}/receipt`),
  rate: (id: string, score: number, comment?: string) =>
    authed<RatingResponse>(`/rides/${id}/rate`, { method: "POST", body: J({ score, comment: comment ?? null }) }),

  // pricing / promo
  surge: (lat: number, lng: number) => authed<SurgeQuote>(`/pricing/surge?lat=${lat}&lng=${lng}`),
  quotePromo: (code: string, fare_poisha: number) =>
    authed<PromoQuoteResult>("/promos/quote", { method: "POST", body: J({ code, fare_poisha }) }),

  // wallet
  wallet: () => authed<WalletStatement>("/wallet"),
  topup: (amount_bdt: number) => authed<{ balance_poisha: number; balance_bdt: number }>("/wallet/topup", { method: "POST", body: J({ amount_bdt }) }),

  // notifications
  notifications: () => authed<NotificationList>("/notifications"),
  markAllRead: () => authed<{ marked_read: number }>("/notifications/read-all", { method: "POST" }),

  // admin
  metrics: () => authed<AdminMetrics>("/admin/metrics"),
};

type RatingResponse = { id: string; score: number };
