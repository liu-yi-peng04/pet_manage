import http from "./http";

export interface Store {
  id: number;
  name: string;
  store_type: string;
  address: string | null;
  phone: string | null;
  city?: string | null;
  description: string;
  created_at: string;
}

export interface Product {
  id: number;
  store_id: number | null;
  name: string;
  category: string;
  price: number | null;
  species: string;
  min_weight_kg: number | null;
  max_weight_kg: number | null;
  spec: string | null;
  image_url: string | null;
  description: string;
  is_active?: boolean;
  created_at?: string;
  stock?: number;
  promo?: string | null;
  shipping_mode?: string;
  brand?: string | null;
  package_spec?: string | null;
  store_name?: string | null;
  store_phone?: string | null;
  store_address?: string | null;
  store_city?: string | null;
  store_rating?: number | null;
}

export interface StorePayload {
  name: string;
  store_type?: string;
  address?: string | null;
  phone?: string | null;
  description?: string;
}

export interface ProductPayload {
  name: string;
  store_id?: number | null;
  category?: string;
  price?: number | null;
  species?: string;
  min_weight_kg?: number | null;
  max_weight_kg?: number | null;
  spec?: string | null;
  image_url?: string | null;
  description?: string;
  is_active?: boolean;
  stock?: number;
  promo?: string | null;
  shipping_mode?: string;
  brand?: string | null;
  package_spec?: string | null;
}

export const storeApi = {
  stores: (params?: { store_type?: string; city?: string }) =>
    http.get("/stores", { params }) as Promise<Store[]>,
  createStore: (data: StorePayload) => http.post("/stores", data) as Promise<Store>,
  removeStore: (id: number) => http.delete(`/stores/${id}`) as Promise<{ detail: string }>,

  products: (params?: { category?: string; species?: string; keyword?: string; store_id?: number }) =>
    http.get("/stores/products", { params }) as Promise<Product[]>,
  product: (id: number) => http.get(`/stores/products/${id}`) as Promise<Product>,
  createProduct: (data: ProductPayload) => http.post("/stores/products", data) as Promise<Product>,
  updateProduct: (id: number, data: ProductPayload) =>
    http.put(`/stores/products/${id}`, data) as Promise<Product>,
  removeProduct: (id: number) =>
    http.delete(`/stores/products/${id}`) as Promise<{ detail: string }>,
};
