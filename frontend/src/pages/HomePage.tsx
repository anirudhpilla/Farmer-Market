import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState, useTransition } from "react";
import { useSearchParams } from "react-router-dom";
import { CATEGORY_STALE_TIME, PRODUCT_STALE_TIME } from "../queryClient";
import { useDebouncedValue } from "../useDebouncedValue";

import { getCategories, getProducts } from "../api";
import { ProductCard } from "../components/ProductCard";

const PAGE_SIZE = 6;

export function HomePage() {
  const [params, setParams] = useSearchParams();
  const search = params.get("search") ?? "";
  const debouncedSearch = useDebouncedValue(search.trim());
  const categoryId = Number(params.get("category")) || undefined;
  const requestedPage = Number(params.get("page"));
  const page = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
  const [isTransitionPending, startTransition] = useTransition();
  const [filters, setFilters] = useState({
    search: debouncedSearch || undefined, categoryId, page, pageSize: PAGE_SIZE,
  });

  // Keep URL-controlled inputs immediate; apply the catalog query at lower priority.
  useEffect(() => {
    startTransition(() => {
      setFilters({ search: debouncedSearch || undefined, categoryId, page, pageSize: PAGE_SIZE });
    });
  }, [debouncedSearch, categoryId, page]);

  function setFilter(key: string, value: string) {
    setParams((current) => {
      if (value) current.set(key, value);
      else current.delete(key);
      if (key !== "page") current.delete("page");
      return current;
    }, { replace: true });
  }
  const { data: categories = [], isError: categoryError } = useQuery({
    queryKey: ["categories"],
    queryFn: ({ signal }) => getCategories(signal),
    staleTime: CATEGORY_STALE_TIME,
  });
  const { data: products, isPending: loading, isError: error, isFetching, isPlaceholderData } = useQuery({
    queryKey: ["products", filters],
    queryFn: ({ signal }) => getProducts(filters, signal),
    staleTime: PRODUCT_STALE_TIME,
    refetchInterval: 15_000,
    placeholderData: keepPreviousData,
  });
  // A transition tracks React rendering, not the HTTP request or debounce timer.
  const updating = isTransitionPending || isFetching ||
    search.trim() !== (filters.search ?? "") || categoryId !== filters.categoryId || page !== filters.page;

  return (
    <section className="catalog-page" aria-labelledby="page-title">
      <div className="catalog-heading">
        <h1 id="page-title">Fresh from nearby farms.</h1>
      </div>

      <div className="catalog-filters" aria-label="Product filters">
        <label>
          <span>Search products</span>
          <input
            type="search"
            maxLength={100}
            value={search}
            placeholder="Try tomatoes or rice"
            onChange={(event) => {
              setFilter("search", event.target.value);
            }}
          />
        </label>
        <label>
          <span>Category</span>
          <select
            value={categoryId ?? ""}
            onChange={(event) => {
              setFilter("category", event.target.value);
            }}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {categoryError && <p role="alert">Categories could not be loaded. You can still search products.</p>}
      {!loading && updating && <p role="status">Updating products…</p>}
      {loading && <p className="catalog-message" role="status">Loading products…</p>}
      {!loading && error && <p className="catalog-message catalog-message--error" role="alert">Products could not be loaded. Please try again.</p>}
      {!loading && !error && products?.items.length === 0 && (
        <p className="catalog-message">No products match these filters.</p>
      )}

      {!loading && !error && products && products.items.length > 0 && (
        <div className="catalog-results" aria-busy={updating}>
          <div className="result-summary">
            {products.total} {products.total === 1 ? "product" : "products"}
          </div>
          <div className="product-grid product-grid--scrollable">
            {products.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <nav className="pagination" aria-label="Product pages">
            <button
              type="button"
              disabled={updating || isPlaceholderData || products.page <= 1}
              onClick={() => {
                setFilter("page", String(page - 1));
              }}
            >
              Previous
            </button>
            <span>Page {products.page} of {products.total_pages}</span>
            <button
              type="button"
              disabled={updating || isPlaceholderData || products.page >= products.total_pages}
              onClick={() => {
                setFilter("page", String(page + 1));
              }}
            >
              Next
            </button>
          </nav>
        </div>
      )}
    </section>
  );
}
