import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import {
  createAdminProduct,
  editAdminProduct,
  getAdminProduct,
  getApiError,
  getCategories,
} from "../api";
import type { Category, ProductInput } from "../api";

const emptyForm = {
  name: "",
  categoryId: "",
  farmerName: "",
  description: "",
  price: "",
  availableQuantity: "0",
  imageUrl: "",
  status: "inactive" as "active" | "inactive",
};

export function AdminProductFormPage() {
  const productId = useParams().productId;
  const editing = productId !== undefined;
  const numericId = Number(productId);
  const validId = Number.isInteger(numericId) && numericId > 0;
  const navigate = useNavigate();
  const [categories, setCategories] = useState<Category[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (editing && !validId) return;

    const controller = new AbortController();
    const productRequest = editing
      ? getAdminProduct(numericId, controller.signal)
      : Promise.resolve(null);

    Promise.all([getCategories(controller.signal), productRequest])
      .then(([categoryList, product]) => {
        setCategories(categoryList);
        if (product) {
          setForm({
            name: product.name,
            categoryId: String(product.category.id),
            farmerName: product.farmer_name,
            description: product.description,
            price: product.price,
            availableQuantity: String(product.available_quantity),
            imageUrl: product.image_url,
            status: product.status,
          });
        }
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          setError(getApiError(requestError, "The product form could not be loaded."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [editing, numericId, validId]);

  function change(field: keyof typeof emptyForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    const input: ProductInput = {
      name: form.name,
      category_id: Number(form.categoryId),
      farmer_name: form.farmerName,
      description: form.description,
      price: form.price,
      available_quantity: Number(form.availableQuantity),
      image_url: form.imageUrl,
      status: form.status,
    };

    try {
      if (editing) {
        await editAdminProduct(numericId, {
          name: input.name,
          category_id: input.category_id,
          farmer_name: input.farmer_name,
          description: input.description,
          price: input.price,
          image_url: input.image_url,
        });
      } else {
        await createAdminProduct(input);
      }
      navigate("/admin", { replace: true });
    } catch (requestError) {
      setError(getApiError(requestError, "The product could not be saved."));
    } finally {
      setSubmitting(false);
    }
  }

  if (editing && !validId) {
    return <p className="catalog-message catalog-message--error">Invalid product ID.</p>;
  }
  if (loading) return <p className="catalog-message">Loading product form…</p>;

  return (
    <section className="product-form-page">
      <Link className="back-link" to="/admin">← Back to products</Link>
      <p className="eyebrow">Administration</p>
      <h1>{editing ? "Edit product" : "Add product"}</h1>

      <form className="product-form" onSubmit={submit}>
        <label>
          <span>Name and sale unit *</span>
          <input
            value={form.name}
            minLength={2}
            maxLength={160}
            required
            onChange={(event) => change("name", event.target.value)}
          />
        </label>
        <label>
          <span>Category *</span>
          <select
            value={form.categoryId}
            required
            onChange={(event) => change("categoryId", event.target.value)}
          >
            <option value="">Select category</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Farmer name *</span>
          <input
            value={form.farmerName}
            minLength={2}
            maxLength={160}
            required
            onChange={(event) => change("farmerName", event.target.value)}
          />
        </label>
        <label>
          <span>Price (INR) *</span>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={form.price}
            required
            onChange={(event) => change("price", event.target.value)}
          />
        </label>
        <label className="product-form__wide">
          <span>Description *</span>
          <textarea
            value={form.description}
            minLength={10}
            maxLength={3000}
            required
            onChange={(event) => change("description", event.target.value)}
          />
        </label>
        <label className="product-form__wide">
          <span>Image URL *</span>
          <input
            type="url"
            value={form.imageUrl}
            maxLength={2048}
            required
            onChange={(event) => change("imageUrl", event.target.value)}
          />
        </label>
        <label>
          <span>Available quantity</span>
          <input
            type="number"
            min="0"
            max="1000000"
            value={form.availableQuantity}
            disabled={editing}
            required
            onChange={(event) => change("availableQuantity", event.target.value)}
          />
          {editing && <small>Update stock from the product list.</small>}
        </label>
        <label>
          <span>Status</span>
          <select
            value={form.status}
            disabled={editing}
            onChange={(event) => change("status", event.target.value)}
          >
            <option value="inactive">Inactive</option>
            <option value="active">Active</option>
          </select>
          {editing && <small>Change status from the product list.</small>}
        </label>

        {error && <p className="form-error product-form__wide" role="alert">{error}</p>}
        <div className="product-form__actions product-form__wide">
          <Link to="/admin">Cancel</Link>
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Save product"}
          </button>
        </div>
      </form>
    </section>
  );
}
