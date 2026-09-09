import { useEffect, useState } from "react";

import { getCategories, getProducts } from "../api";
import type { Category, ProductPage } from "../api";
import { ProductCard } from "../components/ProductCard";

const PAGE_SIZE = 6;

export function HomePage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [products, setProducts] = useState<ProductPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedSearch(search.trim());
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [search]);

  useEffect(() => {
    const controller = new AbortController();
    getCategories(controller.signal)
      .then(setCategories)
      .catch(() => {
        if (!controller.signal.aborted) setCategories([]);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    getProducts(
      {
        search: debouncedSearch || undefined,
        categoryId,
        page,
        pageSize: PAGE_SIZE,
      },
      controller.signal,
    )
      .then((result) => {
        setProducts(result);
        setError(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setProducts(null);
          setError("We could not load products. Please try again.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [categoryId, debouncedSearch, page]);

  return (
    <section aria-labelledby="page-title">
      <div className="catalog-heading">
        <div>
          <p className="eyebrow">Local produce marketplace</p>
          <h1 id="page-title">Fresh from nearby farms.</h1>
        </div>
        <p>Browse seasonal produce and everyday essentials from local growers.</p>
      </div>

      <div className="catalog-filters" aria-label="Product filters">
        <label>
          <span>Search products</span>
          <input
            type="search"
            value={search}
            placeholder="Try tomatoes or rice"
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
              setLoading(true);
            }}
          />
        </label>
        <label>
          <span>Category</span>
          <select
            value={categoryId ?? ""}
            onChange={(event) => {
              setCategoryId(event.target.value ? Number(event.target.value) : undefined);
              setPage(1);
              setLoading(true);
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

      {loading && <p className="catalog-message" role="status">Loading products…</p>}
      {!loading && error && <p className="catalog-message catalog-message--error">{error}</p>}
      {!loading && !error && products?.items.length === 0 && (
        <p className="catalog-message">No products match these filters.</p>
      )}

      {!loading && !error && products && products.items.length > 0 && (
        <>
          <div className="result-summary">
            {products.total} {products.total === 1 ? "product" : "products"}
          </div>
          <div className="product-grid">
            {products.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <nav className="pagination" aria-label="Product pages">
            <button
              type="button"
              disabled={products.page <= 1}
              onClick={() => {
                setPage(page - 1);
                setLoading(true);
              }}
            >
              Previous
            </button>
            <span>Page {products.page} of {products.total_pages}</span>
            <button
              type="button"
              disabled={products.page >= products.total_pages}
              onClick={() => {
                setPage(page + 1);
                setLoading(true);
              }}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
