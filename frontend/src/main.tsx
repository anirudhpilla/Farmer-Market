import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "./AppLayout";
import { AuthProvider, RequireAdmin } from "./auth";
import { CartProvider } from "./cart";
import { AdminPage } from "./pages/AdminPage";
import { AdminOrdersPage } from "./pages/AdminOrdersPage";
import { AdminProductFormPage } from "./pages/AdminProductFormPage";
import { CartPage } from "./pages/CartPage";
import { CheckoutPage } from "./pages/CheckoutPage";
import { HomePage } from "./pages/HomePage";
import { GuestOrdersPage } from "./pages/GuestOrdersPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { OrderConfirmationPage } from "./pages/OrderConfirmationPage";
import { ProductDetailsPage } from "./pages/ProductDetailsPage";
import "./styles.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "products/:productId", element: <ProductDetailsPage /> },
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
    <AuthProvider>
      <CartProvider>
        <RouterProvider router={router} />
      </CartProvider>
    </AuthProvider>
  </StrictMode>,
);
