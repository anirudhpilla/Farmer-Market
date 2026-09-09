import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="not-found">
      <p className="eyebrow">404</p>
      <h1>That page does not exist.</h1>
      <Link className="button-link" to="/">
        Return to products
      </Link>
    </section>
  );
}
