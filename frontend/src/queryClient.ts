import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

// Public catalog data can be reused briefly; checkout still checks stock/prices on the server.
export const PRODUCT_STALE_TIME = 30_000;
export const CATEGORY_STALE_TIME = 5 * 60_000;

export function invalidateProducts() {
  void queryClient.invalidateQueries({ queryKey: ["products"] });
  void queryClient.invalidateQueries({ queryKey: ["product"] });
}
