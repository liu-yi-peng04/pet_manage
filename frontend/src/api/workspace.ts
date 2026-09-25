import http from "./http";
import type { Appointment, Boarding, Product, Store } from "@/types";
import type { DocumentItem } from "@/types";

export interface StoreOverview {
  store: Store;
  staff: number;
  pending_appointments: number;
  active_boardings: number;
  customers: number;
  products: number;
  due_vaccines?: number;
}

export interface StaffMember {
  id: number;
  username: string;
  email: string | null;
  staff_role: string | null;
  store_id: number | null;
  created_at: string;
}

export interface CustomerPet {
  id: number;
  name: string;
  species: string;
  breed: string | null;
}

export interface Customer {
  id: number;
  username: string;
  email: string | null;
  pets: CustomerPet[];
  last_appointment_at: string | null;
}

export const workspaceApi = {
  overview: () => http.get("/workspace/overview") as Promise<StoreOverview>,
  appointments: (status?: string) =>
    http.get("/workspace/appointments", { params: { status } }) as Promise<Appointment[]>,
  setAppointmentStatus: (id: number, status: string) =>
    http.post(`/workspace/appointments/${id}/status`, { status }) as Promise<{ detail: string }>,
  boardings: (status?: string) =>
    http.get("/workspace/boardings", { params: { status } }) as Promise<Boarding[]>,
  setBoardingStatus: (id: number, status: string) =>
    http.post(`/workspace/boardings/${id}/status`, { status }) as Promise<{ detail: string }>,
  customers: () => http.get("/workspace/customers") as Promise<Customer[]>,
  products: () => http.get("/workspace/products") as Promise<Product[]>,
  vaccineRecalls: (days = 30) =>
    http.get("/workspace/vaccine-recalls", { params: { days } }) as Promise<import("@/types").VaccineRecall[]>,
  inviteVaccine: (data: {
    pet_id: number;
    vaccine_id?: number;
    hospital_id: number;
    appt_time?: string;
    notes?: string;
  }) => http.post("/workspace/vaccine-recalls/invite", data) as Promise<Appointment>,
  storeKb: () => http.get("/workspace/kb") as Promise<{ id: number; name: string; description: string }>,
  storeKbDocuments: () =>
    http.get("/workspace/kb/documents") as Promise<DocumentItem[]>,
};

export const staffApi = {
  list: (storeId: number) => http.get(`/stores/${storeId}/staff`) as Promise<StaffMember[]>,
  search: (storeId: number, username: string) =>
    http.get(`/stores/${storeId}/staff/search`, { params: { username } }) as Promise<
      { id: number; username: string; email: string | null }[]
    >,
  assign: (storeId: number, data: { user_id: number; staff_role: string }) =>
    http.post(`/stores/${storeId}/staff`, data) as Promise<StaffMember>,
  remove: (storeId: number, staffId: number) =>
    http.delete(`/stores/${storeId}/staff/${staffId}`) as Promise<{ detail: string }>,
};

export type { Appointment, Boarding, Product, Store };