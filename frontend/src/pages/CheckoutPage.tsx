import { useRef, useState } from "react";
import axios from "axios";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { checkoutCart, getApiError } from "../api";
import { useCart } from "../cart";
import { formatPrice } from "../currency";

export function CheckoutPage() {
  const { cart, ready, reloadCart } = useCart();
  const navigate = useNavigate();
  const idempotencyKey = useRef(crypto.randomUUID());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!ready) return <p className="catalog-message">Loading checkout…</p>;
  if (!cart || cart.items.length === 0) return <Navigate to="/cart" replace />;

  const hasIssues = cart.items.some((item) => item.issue !== null);

  async function placeOrder() {
    if (!cart || hasIssues || submitting) return;
    if (!window.confirm(`Place this order for ${formatPrice(cart.grand_total)}? Stock and prices will be checked before confirmation.`)) return;
    setSubmitting(true);
    setError("");
    try {
      const order = await checkoutCart(cart, idempotencyKey.current);
      await reloadCart();
      navigate(`/orders/${order.id}`, { replace: true });
    } catch (requestError) {
      setError(getApiError(requestError, "The order could not be placed."));
      if (axios.isAxiosError(requestError) && requestError.response?.status === 409) {
        try {
          await reloadCart();
          setError(`${getApiError(requestError, "The cart changed.")} Return to the cart and click Update to review current quantities and prices.`);
        } catch {
          setError("The cart changed, but its latest details could not be loaded. Return to the cart and try Update again.");
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="checkout-page">
      <p className="eyebrow">Final review</p>
      <h1>Confirm your order</h1>
      <p>Stock and prices will be checked once more when you place the order.</p>
      <div className="checkout-card">
        {cart.items.map((item) => (
          <div className="checkout-line" key={item.id}>
            <span>{item.name} × {item.quantity}</span>
            <strong>{formatPrice(item.line_total)}</strong>
          </div>
        ))}
        <div className="checkout-line checkout-total">
          <span>Total</span><strong>{formatPrice(cart.grand_total)}</strong>
        </div>
      </div>
      {hasIssues && <p className="form-error">Return to the cart and resolve its warnings.</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions">
        <Link to="/cart">Back to cart</Link>
        <button type="button" disabled={submitting || hasIssues} onClick={() => void placeOrder()}>
          {submitting ? "Placing order…" : "Place order"}
        </button>
      </div>
    </section>
  );
}
