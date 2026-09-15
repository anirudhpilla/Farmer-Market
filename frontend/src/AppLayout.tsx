import { Suspense, useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth";
import { useCart } from "./cart";
import { useWishlist } from "./wishlist";
import { getApiError } from "./api";

export function AppLayout() {
  const { user, logout } = useAuth();
  const { cart } = useCart();
  const { wishlist } = useWishlist();
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
          <div className="brand-group">
            <Link className="brand" to="/">
              <svg className="brand-logo" width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                <rect width="32" height="32" rx="8" fill="#e8f1e5" />
                <path d="M24 7C13 7 7 11 9 19c8 3 15-2 15-12Z" fill="#397348" />
                <path d="M7 25 20 12" stroke="#203126" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <span>Farmer Market</span>
            </Link>
            {user && <span className="admin-session-badge" aria-label="Administrator signed in">Admin</span>}
          </div>
          <nav aria-label="Main navigation">
            <NavLink to="/">Products</NavLink>
            {user && <NavLink to="/admin" end>Manage products</NavLink>}
            <NavLink to={user ? "/admin/orders" : "/orders"}>Orders</NavLink>
            {!user && <NavLink to="/wishlist">Wishlist ({wishlist.item_count})</NavLink>}
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
