import { Link, NavLink, Outlet } from "react-router-dom";

import { useAuth } from "./auth";
import { useCart } from "./cart";

export function AppLayout() {
  const { user } = useAuth();
  const { cart } = useCart();

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="page-width header-content">
          <Link className="brand" to="/">
            Farmer Market
          </Link>
          <nav aria-label="Main navigation">
            <NavLink to="/">Products</NavLink>
            {user && <NavLink to="/admin/orders">Orders</NavLink>}
            {!user && <NavLink to="/cart">Cart ({cart?.item_count ?? 0})</NavLink>}
            <NavLink to={user ? "/admin" : "/admin/login"}>
              {user ? "Admin" : "Sign in"}
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="page-width main-content">
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="page-width">Fresh produce from local farmers.</div>
      </footer>
    </div>
  );
}

