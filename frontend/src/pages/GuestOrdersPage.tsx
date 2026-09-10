import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ensureGuestSession, getApiError, getGuestOrders } from "../api";
import type { OrderPage } from "../api";
import { formatPrice } from "../currency";

export function GuestOrdersPage() {
  const [page, setPage] = useState(1);
  const [orders, setOrders] = useState<OrderPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function loadOrders() {
      try {
        await ensureGuestSession();
        if (controller.signal.aborted) return;
        const result = await getGuestOrders(page, controller.signal);
        if (!controller.signal.aborted) {
          setOrders(result);
          setError("");
        }
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "Your orders could not be loaded."));
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void loadOrders();
    return () => controller.abort();
  }, [page, reloadKey]);

  function changePage(nextPage: number) {
    setLoading(true);
    setPage(nextPage);
  }

  return (
    <section className="checkout-page">
      <h1>Your orders</h1>
      <p>Orders placed in this browser. Clearing cookies or using another browser will hide this history.</p>
      {loading ? (
        <p className="catalog-message" role="status">Loading orders…</p>
      ) : error ? (
        <div className="catalog-message">
          <p className="form-error" role="alert">{error}</p>
          <button type="button" onClick={() => {
            setLoading(true);
            setReloadKey((current) => current + 1);
          }}>Try again</button>
        </div>
      ) : orders && (
        <>
          {orders.items.length === 0 ? (
            <p>No orders yet. <Link to="/">Browse products</Link></p>
          ) : (
            <div className="order-list">
              {orders.items.map((order) => (
                <Link className="order-list__row" to={`/orders/${order.id}`} key={order.id}>
                  <strong>Order #{order.id}</strong>
                  <span>{new Date(order.created_at).toLocaleString()}</span>
                  <span>{order.item_count} items</span>
                  <strong>{formatPrice(order.grand_total)}</strong>
                </Link>
              ))}
            </div>
          )}
          {orders.total_pages > 1 && (
            <nav className="pagination" aria-label="Your order pages">
              <button type="button" disabled={page <= 1} onClick={() => changePage(page - 1)}>
                Previous
              </button>
              <span>Page {page} of {orders.total_pages}</span>
              <button type="button" disabled={page >= orders.total_pages} onClick={() => changePage(page + 1)}>
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}
