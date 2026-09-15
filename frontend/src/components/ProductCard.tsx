import { memo } from "react";
import { Link } from "react-router-dom";

import type { Product } from "../api";
import { formatPrice } from "../currency";
import { ProductImage } from "./ProductImage";
import { WishlistButton } from "./WishlistButton";

type ProductCardProps = {
  product: Product;
};

export const ProductCard = memo(function ProductCard({ product }: ProductCardProps) {
  const inStock = product.available_quantity > 0;

  return (
    <article className="product-card">
      <Link className="product-card__main" to={`/products/${product.id}`}>
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
              {product.regular_price && Number(product.regular_price) > Number(product.price) && (
                <del className="regular-price">{formatPrice(product.regular_price)}</del>
              )}
              <strong className="price">{formatPrice(product.price)}</strong>
              <span className={inStock ? "stock stock--available" : "stock stock--empty"}>
                {inStock ? `${product.available_quantity} available` : "Out of stock"}
              </span>
            </div>
            <span className="button-link button-link--small">View details</span>
          </div>
        </div>
      </Link>
      <div className="product-card__wishlist"><WishlistButton productId={product.id} /></div>
    </article>
  );
});
