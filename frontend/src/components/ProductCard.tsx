import { Link } from "react-router-dom";

import type { Product } from "../api";
import { formatPrice } from "../currency";
import { ProductImage } from "./ProductImage";

type ProductCardProps = {
  product: Product;
};

export function ProductCard({ product }: ProductCardProps) {
  const inStock = product.available_quantity > 0;

  return (
    <article className="product-card">
      <ProductImage
        className="product-card__image"
        src={product.image_url}
        alt={product.name}
        loading="lazy"
      />
      <div className="product-card__body">
        <span className="category-label">{product.category.name}</span>
        <h2>{product.name}</h2>
        <p className="farmer-name">By {product.farmer_name}</p>
        <div className="product-card__footer">
          <div>
            <strong className="price">{formatPrice(product.price)}</strong>
            <span className={inStock ? "stock stock--available" : "stock stock--empty"}>
              {inStock ? `${product.available_quantity} available` : "Out of stock"}
            </span>
          </div>
          <Link className="button-link button-link--small" to={`/products/${product.id}`}>
            View details
          </Link>
        </div>
      </div>
    </article>
  );
}
