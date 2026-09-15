import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  addWishlistItem,
  ensureGuestSession,
  getWishlist,
  removeWishlistItem,
} from "./api";
import type { Wishlist } from "./api";
import { useAuth } from "./auth";

type WishlistContextValue = {
  wishlist: Wishlist;
  ready: boolean;
  error: string;
  hasProduct: (productId: number) => boolean;
  toggleProduct: (productId: number) => Promise<void>;
};

const emptyWishlist: Wishlist = { items: [], item_count: 0 };
const WishlistContext = createContext<WishlistContextValue | null>(null);

export function WishlistProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();

  if (authLoading) {
    return (
      <WishlistContext.Provider value={{
        wishlist: emptyWishlist,
        ready: false,
        error: "",
        hasProduct: () => false,
        toggleProduct: async () => undefined,
      }}>
        {children}
      </WishlistContext.Provider>
    );
  }

  if (user) {
    return (
      <WishlistContext.Provider value={{
        wishlist: emptyWishlist,
        ready: true,
        error: "",
        hasProduct: () => false,
        toggleProduct: async () => undefined,
      }}>
        {children}
      </WishlistContext.Provider>
    );
  }

  return <GuestWishlistProvider>{children}</GuestWishlistProvider>;
}

function GuestWishlistProvider({ children }: { children: React.ReactNode }) {
  const [wishlist, setWishlist] = useState(emptyWishlist);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    ensureGuestSession()
      .then(() => getWishlist())
      .then((result) => {
        if (active) {
          setWishlist(result);
          setError("");
        }
      })
      .catch(() => {
        if (active) setError("The wishlist could not be loaded.");
      })
      .finally(() => {
        if (active) setReady(true);
      });

    return () => {
      active = false;
    };
  }, []);

  const productIds = useMemo(
    () => new Set(wishlist.items.map((product) => product.id)),
    [wishlist.items],
  );

  const hasProduct = useCallback(
    (productId: number) => productIds.has(productId),
    [productIds],
  );

  const toggleProduct = useCallback(async (productId: number) => {
    setError("");
    try {
      const result = productIds.has(productId)
        ? await removeWishlistItem(productId)
        : await addWishlistItem(productId);
      setWishlist(result);
    } catch (requestError) {
      setError("The wishlist could not be updated.");
      throw requestError;
    }
  }, [productIds]);

  const value = useMemo(
    () => ({ wishlist, ready, error, hasProduct, toggleProduct }),
    [error, hasProduct, ready, toggleProduct, wishlist],
  );

  return <WishlistContext.Provider value={value}>{children}</WishlistContext.Provider>;
}

// Kept with the provider because this is the only wishlist-specific hook.
// eslint-disable-next-line react-refresh/only-export-components
export function useWishlist() {
  const context = useContext(WishlistContext);
  if (!context) throw new Error("useWishlist must be used inside WishlistProvider");
  return context;
}
