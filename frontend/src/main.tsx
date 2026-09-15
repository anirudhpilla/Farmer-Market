import { lazy, StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./queryClient";

import { AppLayout } from "./AppLayout";
import { AuthProvider, RequireAdmin } from "./auth";
import { CartProvider } from "./cart";
import { CartPage } from "./pages/CartPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { HomePage } from "./pages/HomePage";
import { GuestOrdersPage } from "./pages/GuestOrdersPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OrderConfirmationPage } from "./pages/OrderConfirmationPage";
import { ProductDetailsPage } from "./pages/ProductDetailsPage";
import { WishlistPage } from "./pages/WishlistPage";
import { WishlistProvider } from "./wishlist";
import "./styles.css";

const AdminPage = lazy(() => import("./pages/AdminPage").then((module) => ({ default: module.AdminPage })));

const AdminOrdersPage = lazy(() => import("./pages/AdminOrdersPage").then((module) => ({ default: module.AdminOrdersPage })));

const AdminProductFormPage = lazy(() => import("./pages/AdminProductFormPage").then((module) => ({ default: module.AdminProductFormPage })));

const LoginPage = lazy(() => import("./pages/LoginPage").then((module) => ({ default: module.LoginPage })));

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "products/:productId", element: <ProductDetailsPage /> },
      { path: "wishlist", element: <WishlistPage /> },
      { path: "cart", element: <CartPage /> },
      { path: "checkout", element: <CheckoutPage /> },
      { path: "orders", element: <GuestOrdersPage /> },
      { path: "orders/:orderId", element: <OrderConfirmationPage /> },
      { path: "admin/login", element: <LoginPage /> },
      {
        element: <RequireAdmin />,
        children: [
          { path: "admin", element: <AdminPage /> },
          { path: "admin/products/new", element: <AdminProductFormPage /> },
          { path: "admin/products/:productId/edit", element: <AdminProductFormPage /> },
          { path: "admin/orders", element: <AdminOrdersPage /> },
          { path: "admin/orders/:orderId", element: <AdminOrdersPage /> },
        ],
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error("Root element was not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <CartProvider>
          <WishlistProvider>
            <RouterProvider router={router} />
          </WishlistProvider>
        </CartProvider>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
