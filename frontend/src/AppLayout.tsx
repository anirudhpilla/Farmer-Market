import { Link, NavLink, Outlet } from "react-router-dom";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="page-width header-content">
          <Link className="brand" to="/">
            Farmer Market
          </Link>
          <nav aria-label="Main navigation">
            <NavLink to="/">Products</NavLink>
            <span className="nav-placeholder" aria-disabled="true">
              Cart (0)
            </span>
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
