import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  addCartItem,
  ensureGuestSession,
  getCart,
  removeCartItem,
  updateCartItem,
} from "./api";
import type { Cart } from "./api";
import { useAuth } from "./auth";

type CartContextValue = {
  cart: Cart | null;
  ready: boolean;
  error: string;
  addItem: (productId: number, quantity: number) => Promise<void>;
  updateItem: (itemId: number, quantity: number) => Promise<void>;
  removeItem: (itemId: number) => Promise<void>;
  reloadCart: () => Promise<Cart>;
};

const CartContext = createContext<CartContextValue | null>(null);

export function CartProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [cart, setCart] = useState<Cart | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (authLoading || user) return;
    let active = true;

    ensureGuestSession()
      .then(() => active ? getCart() : null)
      .then((result) => {
        if (active) {
          setCart(result);
          setError("");
        }
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
  }, [authLoading, user]);

  const addItem = useCallback(async (productId: number, quantity: number) => {
    if (user) await ensureGuestSession();
    setCart(await addCartItem(productId, quantity));
  }, [user]);

  const updateItem = useCallback(async (itemId: number, quantity: number) => {
    setCart(await updateCartItem(itemId, quantity));
  }, []);

  const removeItem = useCallback(async (itemId: number) => {
    setCart(await removeCartItem(itemId));
  }, []);

  const reloadCart = useCallback(async () => {
    const result = await getCart();
    setCart(result);
    return result;
  }, []);

  const cartReady = !authLoading && (Boolean(user) || ready);
  const value = useMemo(() => ({ cart, ready: cartReady, error, addItem, updateItem, removeItem, reloadCart }), [cart, cartReady, error, addItem, updateItem, removeItem, reloadCart]);

  return (
    <CartContext.Provider
      value={value}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside CartProvider");
  return context;
}
