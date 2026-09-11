import { useState } from "react";
import { Link } from "react-router-dom";

import { getApiError } from "../api";
import type { CartItem } from "../api";
import { useCart } from "../cart";
import { ProductImage } from "../components/ProductImage";
import { formatPrice } from "../currency";

type CartRowProps = {
  item: CartItem;
  updateItem: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
};

function CartRow({ item, updateItem, removeItem }: CartRowProps) {
  const [quantity, setQuantity] = useState(String(item.quantity));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (requestError) {
      setError(getApiError(requestError, "The cart could not be updated."));
    } finally {
      setBusy(false);
    }
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
        {error && <span className="form-error" role="alert">{error}</span>}
      </div>
      <div className="cart-row__quantity">
        <label>
          <span>Quantity</span>
          <input
            type="number"
            min="1"
            max="1000000"
            value={quantity}
            disabled={busy || item.issue === "unavailable"}
            onChange={(event) => setQuantity(event.target.value)}
          />
        </label>
        <button
          type="button"
          disabled={busy || !validQuantity || Number(quantity) === item.quantity}
          onClick={() => void run(() => updateItem(item.id, Number(quantity)))}
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
  const { cart, ready, error, updateItem, removeItem } = useCart();

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
      <div className="cart-layout">
        <div className="cart-items">
          {cart.items.map((item) => (
            <CartRow
              key={`${item.id}-${item.quantity}-${item.issue}`}
              item={item}
              updateItem={updateItem}
              removeItem={removeItem}
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
            className={`button-link${hasIssues ? " button-link--disabled" : ""}`}
            to={hasIssues ? "/cart" : "/checkout"}
            aria-disabled={hasIssues}
            onClick={(event) => {
              if (hasIssues) event.preventDefault();
            }}
          >
            Review checkout
          </Link>
        </aside>
      </div>
    </section>
  );
}
