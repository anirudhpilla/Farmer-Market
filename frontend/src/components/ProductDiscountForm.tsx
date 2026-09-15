import { useState } from "react";
import { cancelProductDiscount, getApiError, scheduleProductDiscount } from "../api";
import type { AdminProduct } from "../api";

function localDateTime(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

export function ProductDiscountForm({ product }: { product: AdminProduct }) {
  const [saved, setSaved] = useState(product);
  const [percent, setPercent] = useState(product.discount_percent ?? "");
  const [start, setStart] = useState(localDateTime(product.discount_starts_at));
  const [end, setEnd] = useState(localDateTime(product.discount_ends_at));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (new Date(end) <= new Date(start) || new Date(end) <= new Date()) {
      setError("End time must be after start time and in the future.");
      return;
    }
    if (!window.confirm("Save this discount window? It replaces any existing discount.")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const updated = await scheduleProductDiscount(product.id, {
        percent, starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString(),
      });
      setSaved(updated);
      setMessage("Discount window saved. The regular price returns automatically at the end.");
    } catch (error) {
      setError(getApiError(error, "Could not save the discount."));
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (busy || !window.confirm("Cancel this discount and restore the regular price now?")) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setSaved(await cancelProductDiscount(product.id));
      setPercent(""); setStart(""); setEnd("");
      setMessage("Discount cancelled. Regular price restored.");
    } catch (error) {
      setError(getApiError(error, "Could not cancel the discount."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="discount-section" aria-labelledby="discount-heading">
      <h2 id="discount-heading">Scheduled discount</h2>
      <p>Save product changes above before scheduling a discount. Times use your device’s timezone ({Intl.DateTimeFormat().resolvedOptions().timeZone}).</p>
      {saved.discount_starts_at && saved.discount_ends_at && (
        <p>Saved: {saved.discount_percent}% off, {new Date(saved.discount_starts_at).toLocaleString()} – {new Date(saved.discount_ends_at).toLocaleString()}.</p>
      )}
      <form className="product-form" onSubmit={save}>
        <label><span>Discount (%) *</span>
          <input required type="number" min="0.01" max="99.99" step="0.01" value={percent} onChange={(event) => setPercent(event.target.value)} />
        </label>
        <label><span>Starts at *</span>
          <input required type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label><span>Ends at *</span>
          <input required type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        {error && <p role="alert" className="form-error product-form__wide">{error}</p>}
        {message && <p role="status" className="product-form__wide">{message}</p>}
        <div className="product-form__actions product-form__wide">
          <button disabled={busy} type="submit">{busy ? "Saving…" : "Save discount"}</button>
          {saved.regular_price !== null && <button disabled={busy} type="button" onClick={cancel}>Cancel discount</button>}
        </div>
      </form>
    </section>
  );
}
