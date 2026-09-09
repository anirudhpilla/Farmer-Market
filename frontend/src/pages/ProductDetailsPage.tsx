import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getProduct } from "../api";
import type { Product } from "../api";
import { ProductImage } from "../components/ProductImage";
import { formatPrice } from "../currency";

export function ProductDetailsPage() {
  const productId = Number(useParams().productId);
  const validId = Number.isInteger(productId) && productId > 0;
  const [result, setResult] = useState<{
    productId: number;
    product: Product | null;
    failed: boolean;
  } | null>(null);

  useEffect(() => {
    if (!validId) return;

    const controller = new AbortController();

    getProduct(productId, controller.signal)
      .then((product) => setResult({ productId, product, failed: false }))
      .catch(() => {
        if (!controller.signal.aborted) {
          setResult({ productId, product: null, failed: true });
        }
      });

    return () => controller.abort();
  }, [productId, validId]);

  const currentResult = result?.productId === productId ? result : null;
  const loading = validId && currentResult === null;
  const error = !validId || currentResult?.failed;
  const product = currentResult?.product;

  if (loading) return <p className="catalog-message" role="status">Loading product…</p>;

  if (error || !product) {
    return (
      <section className="catalog-message catalog-message--error">
        <p>This product could not be found.</p>
        <Link to="/">Return to products</Link>
      </section>
    );
  }

  const inStock = product.available_quantity > 0;

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
      </div>
    </article>
  );
}
