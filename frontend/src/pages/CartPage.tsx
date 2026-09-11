import { useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";

import { getApiError } from "../api";
import type { Cart, CartItem } from "../api";
import { useCart } from "../cart";
import { ProductImage } from "../components/ProductImage";
import { formatPrice } from "../currency";

type CartRowProps = {
  item: CartItem;
  updateItem: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  reloadCart: () => Promise<Cart>;
  onFeedback: (feedback: { message: string; error: boolean }) => void;
  busy: boolean;
  onBusyChange: (busy: boolean) => void;
};

function CartRow({ item, updateItem, removeItem, reloadCart, onFeedback, busy, onBusyChange }: CartRowProps) {
  const [quantity, setQuantity] = useState(String(item.quantity));

  async function run(action: () => Promise<void>) {
    if (busy) return;
    onBusyChange(true);
    onFeedback({ message: "", error: false });
    try {
      await action();
    } catch (requestError) {
      onFeedback({ message: getApiError(requestError, "The cart could not be updated. Please try again."), error: true });
    } finally {
      onBusyChange(false);
    }
  }

  async function saveQuantity() {
    const requested = Number(quantity);
    let accepted = Math.min(requested, item.available_quantity);
    try {
      await updateItem(item.id, accepted);
    } catch (requestError) {
      if (!axios.isAxiosError(requestError) || requestError.response?.status !== 409) throw requestError;

      const latestCart = await reloadCart();
      const latestItem = latestCart.items.find((line) => line.id === item.id);
      if (!latestItem || latestItem.issue === "unavailable" || latestItem.available_quantity <= 0 || accepted <= latestItem.available_quantity) {
        throw requestError;
      }
      accepted = latestItem.available_quantity;
      await updateItem(item.id, accepted);
    }
    setQuantity(String(accepted));
    onFeedback({
      message: accepted < requested
        ? `Only ${accepted} units of ${item.name} are available. Quantity reduced to ${accepted} and totals updated.`
        : `${item.name} updated with the current price.`,
      error: false,
    });
  }

  const validQuantity = Number.isInteger(Number(quantity)) && Number(quantity) > 0;

  return (
    <article className="cart-row">
      <ProductImage src={item.image_url} alt="" />
      <div className="cart-row__details">
        <Link to={`/products/${item.product_id}`}><strong>{item.name}</strong></Link>
        <span>{formatPrice(item.unit_price)} each</span>
        {item.issue === "unavailable" && <span className="form-error">No longer available</span>}
        {item.issue === "insufficient_stock" && (
          <span className="form-error">Only {item.available_quantity} currently available</span>
        )}
      </div>
      <div className="cart-row__quantity">
        <label>
          <span>Quantity</span>
          <input
            type="number"
            min="1"
            max={item.available_quantity}
            value={quantity}
            disabled={busy || item.issue === "unavailable" || item.available_quantity === 0}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy || !validQuantity || item.issue === "unavailable" || item.available_quantity === 0}
          onClick={() => void run(saveQuantity)}
        >
          Update
        </button>
      </div>
      <strong className="cart-row__total">{formatPrice(item.line_total)}</strong>
      <button className="link-button" type="button" disabled={busy} onClick={() => void run(() => removeItem(item.id))}>
        Remove
      </button>
    </article>
  );
}

export function CartPage() {
  const { cart, ready, error, updateItem, removeItem, reloadCart } = useCart();
  const [feedback, setFeedback] = useState({ message: "", error: false });
  const [busy, setBusy] = useState(false);

  if (!ready) return <p className="catalog-message">Loading cart…</p>;
  if (error) return <p className="catalog-message catalog-message--error">{error}</p>;
  if (!cart || cart.items.length === 0) {
    return (
      <section className="empty-cart">
        <h1>Your cart is empty.</h1>
        <Link className="button-link" to="/">Browse products</Link>
      </section>
    );
  }

  const hasIssues = cart.items.some((item) => item.issue !== null);

  return (
    <section className="cart-page">
      <h1>Shopping cart</h1>
      {feedback.message && (
        <p className={feedback.error ? "form-error" : "cart-success"} role={feedback.error ? "alert" : "status"}>
          {feedback.message}
        </p>
      )}
      <div className="cart-layout">
        <div className="cart-items">
          {cart.items.map((item) => (
            <CartRow
              key={`${item.id}-${item.quantity}-${item.issue}-${item.available_quantity}-${item.unit_price}`}
              item={item}
              updateItem={updateItem}
              removeItem={removeItem}
              reloadCart={reloadCart}
              onFeedback={setFeedback}
              busy={busy}
              onBusyChange={setBusy}
            />
          ))}
        </div>
        <aside className="cart-summary">
          <h2>Summary</h2>
          <div><span>Items</span><span>{cart.item_count}</span></div>
          <div className="cart-summary__total">
            <span>Total</span><strong>{formatPrice(cart.grand_total)}</strong>
          </div>
          {hasIssues && <p className="form-error">Resolve unavailable or low-stock items first.</p>}
          <Link
            className={`button-link${hasIssues || busy ? " button-link--disabled" : ""}`}
            to={hasIssues || busy ? "/cart" : "/checkout"}
            aria-disabled={hasIssues || busy}
            onClick={(event) => {
              if (hasIssues || busy) event.preventDefault();
            }}
          >
            Review checkout
          </Link>
        </aside>
      </div>
    </section>
  );
}
