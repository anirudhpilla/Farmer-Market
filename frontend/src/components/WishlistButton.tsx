import { useState } from "react";

import { useAuth } from "../auth";
import { useWishlist } from "../wishlist";

export function WishlistButton({ productId }: { productId: number }) {
  const { hasProduct, ready, toggleProduct } = useWishlist();
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const saved = hasProduct(productId);

  async function toggle() {
    if (busy) return;
    setBusy(true);
    setFailed(false);
    try {
      await toggleProduct(productId);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (user) return null;

  return (
    <button
      className={`wishlist-button${saved ? " wishlist-button--saved" : ""}`}
      type="button"
      aria-pressed={saved}
      aria-label={saved ? "Remove from wishlist" : "Add to wishlist"}
      title={saved ? "Remove from wishlist" : "Add to wishlist"}
      disabled={!ready || busy}
      onClick={() => void toggle()}
    >
      <span aria-hidden="true">{saved ? "♥" : "♡"}</span>
      <span>{failed ? "Try again" : saved ? "Wishlisted" : "Wishlist"}</span>
    </button>
  );
}
