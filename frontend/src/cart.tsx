import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  addCartItem,
  ensureGuestSession,
  getCart,
  removeCartItem,
  updateCartItem,
} from "./api";
import type { Cart } from "./api";

type CartContextValue = {
  cart: Cart | null;
  ready: boolean;
  error: string;
  addItem: (productId: number, quantity: number) => Promise<void>;
  updateItem: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  reloadCart: () => Promise<void>;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<Cart | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    ensureGuestSession()
      .then(() => getCart())
      .then((result) => {
        if (active) setCart(result);
      })
      .catch(() => {
        if (active) setError("The shopping cart could not be loaded.");
      })
      .finally(() => {
        if (active) setReady(true);
      });

    return () => {
      active = false;
    };
  }, []);

  const addItem = useCallback(async (productId: number, quantity: number) => {
    setCart(await addCartItem(productId, quantity));
  }, []);

  const updateItem = useCallback(async (itemId: number, quantity: number) => {
    setCart(await updateCartItem(itemId, quantity));
  }, []);

  const removeItem = useCallback(async (itemId: number) => {
    setCart(await removeCartItem(itemId));
  }, []);

  const reloadCart = useCallback(async () => {
    setCart(await getCart());
  }, []);

  const value = useMemo(() => ({ cart, ready, error, addItem, updateItem, removeItem, reloadCart }), [cart, ready, error, addItem, updateItem, removeItem, reloadCart]);

  return (
    <CartContext.Provider
      value={value}
    >
      {children}
    </CartContext.Provider>
  );
}

// Kept with the small provider to avoid creating another one-function file.
// eslint-disable-next-line react-refresh/only-export-components
export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside CartProvider");
  return context;
}
