import type { ImgHTMLAttributes } from "react";

type ProductImageProps = Omit<ImgHTMLAttributes<HTMLImageElement>, "onError" | "src"> & {
  src: string;
};

export function ProductImage({ src, alt, ...props }: ProductImageProps) {
  return (
    <img
      src={src}
      alt={alt}
      onError={(event) => {
        event.currentTarget.onerror = null;
        event.currentTarget.src = "/product-placeholder.svg";
      }}
      {...props}
    />
  );
}
