import axios from "axios";

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
