import { Link } from "react-router-dom";

import { ProductCard } from "../components/ProductCard";
import { useWishlist } from "../wishlist";

export function WishlistPage() {
  const { wishlist, ready, error } = useWishlist();

  return (
    <section className="wishlist-page">
      <h1>Wishlist</h1>
      {!ready && <p className="catalog-message" role="status">Loading wishlist…</p>}
      {error && <p className="catalog-message catalog-message--error" role="alert">{error}</p>}
      {ready && wishlist.items.length === 0 && (
        <p className="catalog-message">
          Your wishlist is empty. <Link to="/">Browse products</Link>
        </p>
      )}
      {ready && wishlist.items.length > 0 && (
        <>
          <p>{wishlist.item_count} {wishlist.item_count === 1 ? "product" : "products"}</p>
          <div className="product-grid product-grid--scrollable">
            {wishlist.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
