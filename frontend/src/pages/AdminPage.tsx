import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  deleteAdminProduct,
  getAdminProducts,
  getApiError,
  setAdminProductStatus,
  setAdminProductStock,
} from "../api";
import type { AdminProduct, AdminProductPage } from "../api";
import { useAuth } from "../auth";
import { formatPrice } from "../currency";

type ProductRowProps = {
  product: AdminProduct;
  onChanged: () => void;
  onError: (message: string) => void;
};

function ProductRow({ product, onChanged, onError }: ProductRowProps) {
  const [stock, setStock] = useState(String(product.available_quantity));
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    onError("");
    try {
      await action();
      onChanged();
    } catch (error) {
      onError(getApiError(error, "The product could not be updated."));
    } finally {
      setBusy(false);
    }
  }

  function removeProduct() {
    if (!window.confirm(`Delete ${product.name}? This hides it from normal lists.`)) return;
    void run(() => deleteAdminProduct(product.id));
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
              void run(() => setAdminProductStock(product.id, Number(stock), product.version))
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
  const { user, logout } = useAuth();
  const [page, setPage] = useState(1);
  const [reloadKey, setReloadKey] = useState(0);
  const [products, setProducts] = useState<AdminProductPage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    getAdminProducts(page, controller.signal)
      .then((result) => {
        setProducts(result);
        setError("");
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "Products could not be loaded."));
        }
      });
    return () => controller.abort();
  }, [page, reloadKey]);

  function reloadProducts() {
    setReloadKey((current) => current + 1);
  }

  return (
    <section className="admin-products">
      <div className="admin-heading">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Products</h1>
          <p>Signed in as {user?.email}</p>
        </div>
        <div className="admin-heading__actions">
          <Link className="button-link" to="/admin/products/new">Add product</Link>
          <button type="button" onClick={() => void logout()}>Sign out</button>
        </div>
      </div>

      {error && <p className="catalog-message catalog-message--error" role="alert">{error}</p>}
      {!products && !error && <p className="catalog-message">Loading products…</p>}
      {products?.items.length === 0 && <p className="catalog-message">No products yet.</p>}

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
                    onError={setError}
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
