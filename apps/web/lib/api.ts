import type {
  AdminOrder,
  ImageUpload,
  Listing,
  Order,
  PriceEstimate,
  RecommendationResponse,
  Textbook,
  TokenResponse,
  User,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const API_BASE_URL = API_BASE;

/** Resolve a relative `/media/...` path returned by the API. */
export function resolveAssetUrl(path?: string | null): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return new URL(path, API_BASE).toString();
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (typeof options.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "请求失败，请稍后再试。";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the generic error when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("cbl_token");
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const value = localStorage.getItem("cbl_user");
  if (!value) return null;
  try {
    return JSON.parse(value) as User;
  } catch {
    return null;
  }
}

export function storeSession(session: TokenResponse): void {
  localStorage.setItem("cbl_token", session.access_token);
  localStorage.setItem("cbl_user", JSON.stringify(session.user));
  window.dispatchEvent(new Event("cbl-session"));
}

export function clearSession(): void {
  localStorage.removeItem("cbl_token");
  localStorage.removeItem("cbl_user");
  window.dispatchEvent(new Event("cbl-session"));
}

export const api = {
  textbooks: (query = "") =>
    request<Textbook[]>(`/textbooks${query ? `?q=${encodeURIComponent(query)}` : ""}`),
  listings: (query = "", courseCode = "") => {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (courseCode) params.set("course_code", courseCode);
    return request<Listing[]>(`/listings${params.size ? `?${params}` : ""}`);
  },
  recommendations: (seedTextbookId?: string) => {
    const params = new URLSearchParams({ limit: "6" });
    if (seedTextbookId) params.set("seed_textbook_id", seedTextbookId);
    return request<RecommendationResponse>(`/recommendations?${params}`);
  },
  estimatePrice: (payload: {
    new_price: number;
    condition_grade: number;
    category: string;
    demand_factor: number;
    has_notes: boolean;
    edition_current: boolean;
  }) =>
    request<PriceEstimate>("/pricing/estimate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  register: (email: string, displayName: string, password: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, display_name: displayName, password }),
    }),
  me: (token: string) => request<User>("/auth/me", {}, token),
  uploadListingImage: (token: string, file: File) => {
    const body = new FormData();
    body.set("file", file);
    return request<ImageUpload>("/listings/images", { method: "POST", body }, token);
  },
  createListing: (
    token: string,
    payload: {
      textbook_id: string;
      condition_grade: number;
      asking_price: number;
      note: string;
      image_url?: string | null;
    },
  ) =>
    request<Listing>(
      "/listings",
      { method: "POST", body: JSON.stringify(payload) },
      token,
    ),
  createOrder: (token: string, listingId: string, idempotencyKey: string) =>
    request<Order>(
      "/orders",
      {
        method: "POST",
        body: JSON.stringify({
          listing_id: listingId,
          idempotency_key: idempotencyKey,
        }),
      },
      token,
    ),
  payOrder: (token: string, orderId: string) =>
    request<Order>(`/orders/${orderId}/pay`, { method: "POST" }, token),
  completeOrder: (token: string, orderId: string) =>
    request<Order>(`/orders/${orderId}/complete`, { method: "POST" }, token),
  cancelOrder: (token: string, orderId: string) =>
    request<Order>(`/orders/${orderId}/cancel`, { method: "POST" }, token),
  orders: (token: string) => request<Order[]>("/orders", {}, token),
  adminMetrics: (token: string) =>
    request<{ textbooks: number; active_listings: number; completed_orders: number }>(
      "/admin/metrics",
      {},
      token,
    ),
  adminListings: (token: string, status = "") => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    return request<Listing[]>(
      `/admin/listings${params.size ? `?${params}` : ""}`,
      {},
      token,
    );
  },
  adminOrders: (token: string, status = "") => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    return request<AdminOrder[]>(
      `/admin/orders${params.size ? `?${params}` : ""}`,
      {},
      token,
    );
  },
  moderateListing: (
    token: string,
    listingId: string,
    status: "active" | "removed",
    reason = "",
  ) =>
    request<{ id: string; status: string }>(
      `/admin/listings/${listingId}`,
      { method: "PATCH", body: JSON.stringify({ status, reason }) },
      token,
    ),
  refundOrder: (token: string, orderId: string, reason: string) =>
    request<Order>(
      `/admin/orders/${orderId}/refund`,
      { method: "POST", body: JSON.stringify({ reason }) },
      token,
    ),
};
