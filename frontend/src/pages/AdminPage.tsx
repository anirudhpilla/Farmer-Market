import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CATEGORY_STALE_TIME } from "../queryClient";
import { useDebouncedValue } from "../useDebouncedValue";
import { Link, useLocation } from "react-router-dom";

import {
  deleteAdminProduct,
  getAdminProducts,
  getCategories,
  getApiError,
  setAdminProductStatus,
  setAdminProductStock,
} from "../api";
import type { AdminProduct, AdminProductPage } from "../api";
import { formatPrice } from "../currency";

type ProductRowProps = {
  product: AdminProduct;
  onChanged: (message: string) => void;
  onError: (message: string) => void;
};

function ProductRow({ product, onChanged, onError }: ProductRowProps) {
  const [stock, setStock] = useState(String(product.available_quantity));
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, message: string, confirmation: string) {
    if (busy || !window.confirm(confirmation)) return;
    setBusy(true);
    onError("");
    try {
      await action();
      onChanged(message);
    } catch (error) {
      onError(getApiError(error, "The product could not be updated."));
    } finally {
      setBusy(false);
    }
  }

  function removeProduct() {
    void run(
      () => deleteAdminProduct(product.id),
      `${product.name} deleted.`,
      `Delete ${product.name}? This hides it from the catalog and admin product list.`,
    );
  }

  return (
    <tr>
      <td>
        <strong>{product.name}</strong>
        <small>{product.category.name}</small>
      </td>
      <td>{formatPrice(product.price)}</td>
      <td>
        <span className={`status-badge status-badge--${product.status}`}>{product.status}</span>
      </td>
      <td>
        <div className="stock-editor">
          <input
            aria-label={`Stock for ${product.name}`}
            type="number"
            min="0"
            max="1000000"
            value={stock}
            disabled={busy}
            onChange={(event) => setStock(event.target.value)}
          />
          <button
            type="button"
            disabled={busy || stock === "" || !Number.isInteger(Number(stock)) || Number(stock) < 0}
            onClick={() =>
              void run(
                () => setAdminProductStock(product.id, Number(stock), product.version),
                `Stock saved for ${product.name}.`,
                `Change stock for ${product.name} from ${product.available_quantity} to ${Number(stock)}?`,
              )
            }
          >
            Save
          </button>
        </div>
      </td>
      <td>
        <div className="row-actions">
          <Link to={`/admin/products/${product.id}/edit`}>Edit</Link>
          <button
            type="button"
            disabled={busy}
            onClick={() =>
              void run(() =>
                setAdminProductStatus(
                  product.id,
                  product.status === "active" ? "inactive" : "active",
                ),
                `${product.name} ${product.status === "active" ? "deactivated" : "activated"}.`,
                product.status === "active"
                  ? `Deactivate ${product.name}? Customers will no longer see it in the catalog.`
                  : `Activate ${product.name}? It will be visible to customers.`,
              )
            }
          >
            {product.status === "active" ? "Deactivate" : "Activate"}
          </button>
          <button className="danger-button" type="button" disabled={busy} onClick={removeProduct}>
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

export function AdminPage() {
  const location = useLocation();
  const [message, setMessage] = useState<string>(location.state?.message ?? "");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim());
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const { data: categories = [], isError: categoryError } = useQuery({
    queryKey: ["categories"],
    queryFn: ({ signal }) => getCategories(signal),
    staleTime: CATEGORY_STALE_TIME,
  });
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [products, setProducts] = useState<AdminProductPage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getAdminProducts({ page, pageSize: 20, search: debouncedSearch || undefined, categoryId }, controller.signal)
      .then((result) => {
        setProducts(result);
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "Products could not be loaded."));
        }
      });
    return () => controller.abort();
  }, [page, reloadKey, debouncedSearch, categoryId]);

  function reloadProducts(success: string) {
    setMessage(success);
    setPage(1);
    setReloadKey((current) => current + 1);
  }

  return (
    <section className="admin-products">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Products</h1>
        </div>
        <div className="admin-heading__actions">
          <Link className="button-link" to="/admin/products/new">Add product</Link>
        </div>
      </div>

      <div className="catalog-filters" aria-label="Admin product filters">
        <label>
          <span>Search products</span>
          <input type="search" maxLength={100} value={search} placeholder="Search by name"
            onChange={(event) => { setSearch(event.target.value); setPage(1); }} />
        </label>
        <label>
          <span>Category</span>
          <select value={categoryId ?? ""}
            onChange={(event) => { setCategoryId(Number(event.target.value) || undefined); setPage(1); }}>
            <option value="">All categories</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
        </label>
      </div>
      {categoryError && <p role="alert">Categories could not be loaded.</p>}
      {message && <p className="cart-success" role="status">{message}</p>}
      {error && <p className="catalog-message catalog-message--error" role="alert">{error}</p>}
      {!products && !error && <p className="catalog-message">Loading products…</p>}
      {products?.items.length === 0 && <p className="catalog-message">No products match these filters.</p>}

      {products && products.items.length > 0 && (
        <>
          <p className="result-summary">{products.total} products</p>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Price</th>
                  <th>Status</th>
                  <th>Stock</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.items.map((product) => (
                  <ProductRow
                    key={`${product.id}-${product.version}`}
                    product={product}
                    onChanged={reloadProducts}
                    onError={(text) => { setError(text); setMessage(""); if (text) setReloadKey((current) => current + 1); }}
                  />
                ))}
              </tbody>
            </table>
          </div>
          {products.total_pages > 1 && (
            <nav className="pagination" aria-label="Admin product pages">
              <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span>Page {products.page} of {products.total_pages}</span>
              <button
                type="button"
                disabled={page >= products.total_pages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
