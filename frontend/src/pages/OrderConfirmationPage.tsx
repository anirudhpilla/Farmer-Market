import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiError, getOrder } from "../api";
import type { Order } from "../api";
import { formatPrice } from "../currency";

export function OrderConfirmationPage() {
  const orderId = Number(useParams().orderId);
  const validOrderId = Number.isInteger(orderId) && orderId > 0;
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    if (!validOrderId) return () => controller.abort();
    getOrder(orderId, controller.signal)
      .then(setOrder)
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "Order not found."));
        }
      });
    return () => controller.abort();
  }, [orderId, validOrderId]);

  if (!validOrderId) return <p className="catalog-message catalog-message--error">Order not found.</p>;
  if (error) return <p className="catalog-message catalog-message--error">{error}</p>;
  if (!order) return <p className="catalog-message">Loading order…</p>;

  return (
    <section className="checkout-page">
      <Link className="back-link" to="/orders">← Your orders</Link>
      <p className="eyebrow">Order confirmed</p>
      <h1>Thank you for your order.</h1>
      <p>Order #{order.id} · {new Date(order.created_at).toLocaleString()}</p>
      <div className="checkout-card">
        {order.items.map((item) => (
          <div className="checkout-line" key={item.id}>
            <span>{item.product_name} × {item.quantity}</span>
            <strong>{formatPrice(item.line_total)}</strong>
          </div>
        ))}
        <div className="checkout-line checkout-total">
          <span>Total</span><strong>{formatPrice(order.grand_total)}</strong>
        </div>
      </div>
      <Link className="button-link" to="/">Continue shopping</Link>
    </section>
  );
}
