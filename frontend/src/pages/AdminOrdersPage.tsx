import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getAdminOrder, getAdminOrders, getApiError } from "../api";
import type { Order } from "../api";
import { formatPrice } from "../currency";

export function AdminOrdersPage() {
  const selectedId = Number(useParams().orderId);
  const [orders, setOrders] = useState<Order[]>([]);
  const [selected, setSelected] = useState<Order | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [loadedKey, setLoadedKey] = useState("");
  const [error, setError] = useState("");
  const detailRequested = Number.isInteger(selectedId) && selectedId > 0;
  const requestKey = detailRequested ? `order-${selectedId}` : `orders-${page}`;

  useEffect(() => {
    const controller = new AbortController();
    const request = detailRequested
      ? getAdminOrder(selectedId, controller.signal).then(setSelected)
      : getAdminOrders(page, controller.signal).then((result) => {
          setOrders(result.items);
          setTotalPages(result.total_pages);
        });

    request
      .then(() => {
        setError("");
        setLoadedKey(requestKey);
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "Orders could not be loaded."));
          setLoadedKey(requestKey);
        }
      });
    return () => controller.abort();
  }, [detailRequested, page, requestKey, selectedId]);

  if (loadedKey !== requestKey) return <p className="catalog-message">Loading orders…</p>;
  if (error) return <p className="catalog-message catalog-message--error">{error}</p>;

  if (selected) {
    return (
      <section>
        <Link to="/admin/orders">← All orders</Link>
        <p className="eyebrow">Admin</p>
        <h1>Order #{selected.id}</h1>
        <p>{new Date(selected.created_at).toLocaleString()}</p>
        <div className="checkout-card">
          {selected.items.map((item) => (
            <div className="checkout-line" key={item.id}>
              <span>{item.product_name} × {item.quantity}</span>
              <strong>{formatPrice(item.line_total)}</strong>
            </div>
          ))}
          <div className="checkout-line checkout-total">
            <span>Total</span><strong>{formatPrice(selected.grand_total)}</strong>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className="admin-heading">
        <div><p className="eyebrow">Admin</p><h1>Orders</h1></div>
        <Link to="/admin">Manage products</Link>
      </div>
      {orders.length === 0 ? (
        <p>No orders have been placed yet.</p>
      ) : (
        <div className="order-list">
          {orders.map((order) => (
            <Link className="order-list__row" to={`/admin/orders/${order.id}`} key={order.id}>
              <strong>Order #{order.id}</strong>
              <span>{new Date(order.created_at).toLocaleString()}</span>
              <span>{order.item_count} items</span>
              <strong>{formatPrice(order.grand_total)}</strong>
            </Link>
          ))}
        </div>
      )}
      {totalPages > 1 && (
        <div className="pagination" aria-label="Order pages">
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>
            Previous
          </button>
          <span>Page {page} of {totalPages}</span>
          <button type="button" disabled={page === totalPages} onClick={() => setPage(page + 1)}>
            Next
          </button>
        </div>
      )}
    </section>
  );
}
