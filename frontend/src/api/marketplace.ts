import http from "./http";
import type { Lead, PetListing, Trainer } from "@/types";

export const marketplaceApi = {
  listings: (params?: { species?: string; city?: string; keyword?: string }) =>
    http.get("/listings", { params }) as Promise<PetListing[]>,
  listing: (id: number) => http.get(`/listings/${id}`) as Promise<PetListing>,
  storeListings: () => http.get("/workspace/listings") as Promise<PetListing[]>,
  createListing: (data: Record<string, unknown>) =>
    http.post("/workspace/listings", data) as Promise<PetListing>,
  removeListing: (id: number) => http.delete(`/workspace/listings/${id}`),

  trainers: (params?: { city?: string; keyword?: string; verified_only?: boolean }) =>
    http.get("/trainers", { params }) as Promise<Trainer[]>,
  myTrainer: () => http.get("/trainers/me") as Promise<Trainer | null>,
  saveTrainer: (data: Record<string, unknown>) =>
    http.post("/trainers/me", data) as Promise<Trainer>,
  verifyTrainer: (id: number) => http.post(`/trainers/${id}/verify`),

  leads: () => http.get("/leads") as Promise<Lead[]>,
  createLead: (data: { need_type: string; summary: string; city?: string; budget?: number }) =>
    http.post("/leads", data) as Promise<Lead>,
  claimLead: (id: number) => http.post(`/leads/${id}/claim`) as Promise<Lead>,
  matchLead: (id: number, data: { store_id?: number; trainer_id?: number }) =>
    http.post(`/leads/${id}/match`, data) as Promise<Lead>,
};
