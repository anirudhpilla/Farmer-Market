import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "./AppLayout";
import { AuthProvider, RequireAdmin } from "./auth";
import { AdminPage } from "./pages/AdminPage";
import { AdminProductFormPage } from "./pages/AdminProductFormPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProductDetailsPage } from "./pages/ProductDetailsPage";
import "./styles.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "products/:productId", element: <ProductDetailsPage /> },
      { path: "admin/login", element: <LoginPage /> },
      {
        element: <RequireAdmin />,
        children: [
          { path: "admin", element: <AdminPage /> },
          { path: "admin/products/new", element: <AdminProductFormPage /> },
          { path: "admin/products/:productId/edit", element: <AdminProductFormPage /> },
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
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
