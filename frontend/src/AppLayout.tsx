import { Suspense, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth";
import { useCart } from "./cart";
import { getApiError } from "./api";

export function AppLayout() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");

  async function signOut() {
    if (signingOut || !window.confirm("Sign out of the admin account?")) return;
    setSigningOut(true);
    setLogoutError("");
    try {
      await logout();
    } catch (error) {
      setLogoutError(getApiError(error, "Server sign-out failed. Please try signing in and out again."));
    } finally {
      setSigningOut(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="page-width header-content">
          <Link className="brand" to="/">
            Farmer Market
          </Link>
          <nav aria-label="Main navigation">
            <NavLink to="/">Products</NavLink>
            {user && <NavLink to="/admin" end>Manage products</NavLink>}
            <NavLink to={user ? "/admin/orders" : "/orders"}>Orders</NavLink>
            {!user && <NavLink to="/cart">Cart ({cart?.item_count ?? 0})</NavLink>}
          </nav>
        </div>
      </header>

      <main className="page-width main-content">
        <Suspense fallback={<p role="status">Loading page…</p>}><Outlet /></Suspense>
      </main>

      <footer className="site-footer">
        <div className="page-width footer-content">
          <span>{user ? `Signed in as ${user.email}` : "Fresh produce from local farmers."}</span>
          <nav className="footer-admin" aria-label="Admin navigation">
            <NavLink to="/admin" end className={({ isActive }) => user || isActive ? "active" : undefined}>
              Admin
            </NavLink>
            {user && (
              <button type="button" disabled={signingOut} onClick={() => void signOut()}>
                {signingOut ? "Signing out…" : "Sign out"}
              </button>
            )}
          </nav>
          {logoutError && <p className="form-error" role="alert">{logoutError}</p>}
        </div>
      </footer>
    </div>
  );
}
