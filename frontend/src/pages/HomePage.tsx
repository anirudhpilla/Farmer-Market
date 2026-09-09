import { useEffect, useState, useTransition } from "react";

import { getCategories, getProducts } from "../api";
import type { Category, ProductPage } from "../api";
import { ProductCard } from "../components/ProductCard";

const PAGE_SIZE = 6;

export function HomePage() {
  const [search, setSearch] = useState("");
  const [querySearch, setQuerySearch] = useState("");
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<ProductPage | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setQuerySearch(search.trim());
      setPage(1);
    }, 180);
    return () => window.clearTimeout(timeoutId);
  }, [search]);

  useEffect(() => {
    const controller = new AbortController();
    getCategories(controller.signal)
      .then((data) => {
        if (data && data.length > 0) {
          setCategories(data);
        }
      })
      .catch(() => {
        // Keep fallback categories if request fails
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setIsFetching(true);

    getProducts(
      {
        search: querySearch || undefined,
        categoryId,
        page,
        pageSize: PAGE_SIZE,
      },
      controller.signal,
    )
      .then((result) => {
        startTransition(() => {
          setProducts(result);
          setError(null);
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          startTransition(() => {
            setProducts(null);
            setError("We could not load products. Please try again.");
          });
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsFetching(false);
          setInitialLoading(false);
        }
      });

    return () => controller.abort();
  }, [categoryId, querySearch, page]);

  const isTransitioning = isPending || isFetching;

  return (
    <section aria-label="Products catalog">
      <div className="catalog-filters" aria-label="Product filters">
        <label>
          <span>Search products</span>
          <input
            type="search"
            value={search}
            placeholder="Try tomatoes or rice"
            onChange={(event) => {
              setSearch(event.target.value);
            }}
          />
        </label>
        <label>
          <span>Category</span>
          <select
            value={categoryId ?? ""}
            onChange={(event) => {
              const val = event.target.value ? Number(event.target.value) : undefined;
              setCategoryId(val);
              setPage(1);
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

      {initialLoading && <p className="catalog-message" role="status">Loading products…</p>}
      {!initialLoading && error && <p className="catalog-message catalog-message--error">{error}</p>}
      {!initialLoading && !error && products?.items.length === 0 && (
        <p className="catalog-message">No products match these filters.</p>
      )}

      {!initialLoading && !error && products && products.items.length > 0 && (
        <div className={`catalog-content ${isTransitioning ? "catalog-content--pending" : ""}`}>
          <div className="result-summary">
            <span>{products.total} {products.total === 1 ? "product" : "products"}</span>
            {isTransitioning && <span className="updating-badge">Updating…</span>}
          </div>
          <div className="product-grid">
            {products.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <nav className="pagination" aria-label="Product pages">
            <button
              type="button"
              disabled={products.page <= 1 || isTransitioning}
              onClick={() => {
                setPage((prev) => Math.max(1, prev - 1));
              }}
            >
              Previous
            </button>
            <span>Page {products.page} of {products.total_pages}</span>
            <button
              type="button"
              disabled={products.page >= products.total_pages || isTransitioning}
              onClick={() => {
                setPage((prev) => prev + 1);
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

