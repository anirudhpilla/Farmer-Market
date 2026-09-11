import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getApiError, getProduct } from "../api";
import { useQuery } from "@tanstack/react-query";
import { PRODUCT_STALE_TIME } from "../queryClient";
import { useCart } from "../cart";
import { useAuth } from "../auth";
import { ProductImage } from "../components/ProductImage";
import { formatPrice } from "../currency";

export function ProductDetailsPage() {
  const { addItem, ready: cartReady } = useCart();
  const { user } = useAuth();
  const productId = Number(useParams().productId);
  const validId = Number.isInteger(productId) && productId > 0;
  const { data: product, isPending, isError } = useQuery({
    queryKey: ["product", productId],
    queryFn: ({ signal }) => getProduct(productId, signal),
    enabled: validId,
    staleTime: PRODUCT_STALE_TIME,
  });
  const [quantity, setQuantity] = useState("1");
  const [adding, setAdding] = useState(false);
  const [cartMessage, setCartMessage] = useState("");
  const [cartError, setCartError] = useState("");

  if (validId && isPending) return <p className="catalog-message" role="status">Loading product…</p>;

  if (!validId || isError || !product) {
    return (
      <section className="catalog-message catalog-message--error">
        <p>This product could not be found.</p>
        <Link to="/">Return to products</Link>
      </section>
    );
  }

  const inStock = product.available_quantity > 0;
  const selectedQuantity = Number(quantity);
  const validQuantity =
    quantity.trim() !== "" &&
    Number.isInteger(selectedQuantity) &&
    selectedQuantity >= 1 &&
    selectedQuantity <= product.available_quantity;

  async function addToCart(selectedProductId: number) {
    setAdding(true);
    setCartError("");
    setCartMessage("");
    try {
      await addItem(selectedProductId, selectedQuantity);
      setCartMessage("Added to your cart.");
    } catch (requestError) {
      setCartError(getApiError(requestError, "The product could not be added."));
    } finally {
      setAdding(false);
    }
  }

  return (
    <article className="product-details">
      <ProductImage className="product-details__image" src={product.image_url} alt={product.name} />
      <div className="product-details__content">
        <Link className="back-link" to="/">← Back to products</Link>
        <span className="category-label">{product.category.name}</span>
        <h1>{product.name}</h1>
        <p className="farmer-name">Grown by {product.farmer_name}</p>
        <p className="product-description">{product.description}</p>
        <strong className="price price--large">{formatPrice(product.price)}</strong>
        <span className={inStock ? "stock stock--available" : "stock stock--empty"}>
          {inStock ? `${product.available_quantity} available` : "Currently out of stock"}
        </span>
        {!user && (<div className="add-to-cart">
          <label>
            <span>Quantity</span>
            <input
              type="number"
              min="1"
              max={product.available_quantity}
              value={quantity}
              disabled={!inStock || adding}
              onChange={(event) => setQuantity(event.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={
              !cartReady ||
              !inStock ||
              adding ||
              !validQuantity
            }
            onClick={() => void addToCart(product.id)}
          >
            {adding ? "Adding…" : "Add to cart"}
          </button>
        </div>)}
        {cartMessage && <p className="cart-success" role="status">{cartMessage}</p>}
        {cartError && <p className="form-error" role="alert">{cartError}</p>}
      </div>
    </article>
  );
}
