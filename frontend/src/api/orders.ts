import http from "./http";
import type { Order } from "@/types";

export const ordersApi = {
  create: (data: {
    items: { product_id: number; qty: number }[];
    address: string;
    shipping_mode?: string;
    notes?: string;
  }) => http.post("/orders", data) as Promise<Order>,
  mine: () => http.get("/orders") as Promise<Order[]>,
  cancel: (id: number) => http.post(`/orders/${id}/cancel`),
  storeOrders: () => http.get("/orders/store") as Promise<Order[]>,
  setStatus: (id: number, status: string) =>
    http.post(`/orders/${id}/status`, { status }) as Promise<Order>,
};
