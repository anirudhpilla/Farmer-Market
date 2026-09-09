import axios from "axios";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

export type Category = {
  id: number;
  name: string;
};

export type Product = {
  id: number;
  name: string;
  category: Category;
  farmer_name: string;
  description: string;
  price: string;
  available_quantity: number;
  image_url: string;
};

export type ProductPage = {
  items: Product[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type AdminProduct = Product & {
  status: "active" | "inactive";
  version: number;
};

export type AdminProductPage = {
  items: AdminProduct[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type ProductInput = {
  name: string;
  category_id: number;
  farmer_name: string;
  description: string;
  price: string;
  available_quantity: number;
  image_url: string;
  status: "active" | "inactive";
};

export type ProductEditInput = Omit<ProductInput, "available_quantity" | "status">;

export type AdminUser = {
  id: number;
  email: string;
  role: "admin";
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AdminUser;
};

type ProductFilters = {
  search?: string;
  categoryId?: number;
  page: number;
  pageSize: number;
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1",
  timeout: 10_000,
  withCredentials: true,
});

let accessToken: string | null = null;
let refreshRequest: Promise<AuthResponse> | null = null;
let authExpiredHandler: (() => void) | null = null;

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  return config;
});

function csrfHeader() {
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrf_token="));

  return cookie ? { "X-CSRF-Token": decodeURIComponent(cookie.split("=")[1]) } : {};
}

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function onAuthExpired(handler: () => void) {
  authExpiredHandler = handler;
  return () => {
    if (authExpiredHandler === handler) authExpiredHandler = null;
  };
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>("/auth/login", { email, password });
  setAccessToken(response.data.access_token);
  return response.data;
}

export function refreshSession(): Promise<AuthResponse> {
  if (!refreshRequest) {
    refreshRequest = api
      .post<AuthResponse>("/auth/refresh", null, { headers: csrfHeader() })
      .then((response) => {
        setAccessToken(response.data.access_token);
        return response.data;
      })
      .finally(() => {
        refreshRequest = null;
      });
  }
  return refreshRequest;
}

type RetriedRequest = InternalAxiosRequestConfig & {
  refreshAttempted?: boolean;
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const request = error.config as RetriedRequest | undefined;
    const isAuthRequest = request?.url?.startsWith("/auth/");

    if (error.response?.status !== 401 || !request || request.refreshAttempted || isAuthRequest) {
      return Promise.reject(error);
    }

    request.refreshAttempted = true;
    try {
      await refreshSession();
      return api(request);
    } catch {
      setAccessToken(null);
      authExpiredHandler?.();
      return Promise.reject(error);
    }
  },
);

export async function logout(): Promise<void> {
  await api.post("/auth/logout", null, { headers: csrfHeader() });
  setAccessToken(null);
}

export function getApiError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
  }
  return fallback;
}

export async function getCategories(signal?: AbortSignal): Promise<Category[]> {
  const response = await api.get<Category[]>("/categories", { signal });
  return response.data;
}

export async function getProducts(
  filters: ProductFilters,
  signal?: AbortSignal,
): Promise<ProductPage> {
  const response = await api.get<ProductPage>("/products", {
    signal,
    params: {
      search: filters.search,
      category_id: filters.categoryId,
      page: filters.page,
      page_size: filters.pageSize,
    },
  });
  return response.data;
}

export async function getProduct(
  productId: number,
  signal?: AbortSignal,
): Promise<Product> {
  const response = await api.get<Product>(`/products/${productId}`, { signal });
  return response.data;
}

export async function getAdminProducts(
  page: number,
  signal?: AbortSignal,
): Promise<AdminProductPage> {
  const response = await api.get<AdminProductPage>("/admin/products", {
    signal,
    params: { page, page_size: 20 },
  });
  return response.data;
}

export async function getAdminProduct(
  productId: number,
  signal?: AbortSignal,
): Promise<AdminProduct> {
  const response = await api.get<AdminProduct>(`/admin/products/${productId}`, { signal });
  return response.data;
}

export async function createAdminProduct(body: ProductInput): Promise<AdminProduct> {
  const response = await api.post<AdminProduct>("/admin/products", body);
  return response.data;
}

export async function editAdminProduct(
  productId: number,
  body: ProductEditInput,
): Promise<AdminProduct> {
  const response = await api.patch<AdminProduct>(`/admin/products/${productId}`, body);
  return response.data;
}

export async function setAdminProductStatus(
  productId: number,
  status: "active" | "inactive",
): Promise<AdminProduct> {
  const response = await api.patch<AdminProduct>(`/admin/products/${productId}/status`, { status });
  return response.data;
}

export async function setAdminProductStock(
  productId: number,
  availableQuantity: number,
  expectedVersion: number,
): Promise<AdminProduct> {
  const response = await api.patch<AdminProduct>(`/admin/products/${productId}/stock`, {
    available_quantity: availableQuantity,
    expected_version: expectedVersion,
  });
  return response.data;
}

export async function deleteAdminProduct(productId: number): Promise<void> {
  await api.delete(`/admin/products/${productId}`);
}
