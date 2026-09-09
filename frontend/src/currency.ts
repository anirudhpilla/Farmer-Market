const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
});

export function formatPrice(price: string): string {
  return currencyFormatter.format(Number(price));
}
