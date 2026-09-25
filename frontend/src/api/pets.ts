import http from "./http";
import type { MedicalExam, Medication } from "@/types";

export interface Pet {
  id: number;
  name: string;
  species: string;
  breed: string | null;
  gender: string;
  birth_date: string | null;
  weight_kg: number | null;
  chip_no: string | null;
  is_neutered: boolean;
  nickname?: string;
  color?: string | null;
  activity_level?: string;
  diet?: string;
  allergies?: string;
  chronic_conditions?: string;
  temperament?: string | null;
  living_env?: string;
  city?: string | null;
  notes: string;
  image_url?: string | null;
  created_at: string;
}

export interface PetPayload {
  name: string;
  species: string;
  breed?: string | null;
  gender?: string;
  birth_date?: string | null;
  weight_kg?: number | null;
  chip_no?: string | null;
  is_neutered?: boolean;
  nickname?: string;
  color?: string | null;
  activity_level?: string;
  diet?: string;
  allergies?: string;
  chronic_conditions?: string;
  temperament?: string | null;
  living_env?: string;
  city?: string | null;
  notes?: string;
  image_url?: string | null;
}

export function petDisplayName(p: Pet): string {
  const title = p.nickname ? `${p.name}（${p.nickname}）` : p.name;
  const extra = [p.breed, p.birth_date].filter(Boolean);
  return extra.length ? `${title} · ${extra.join(" · ")}` : title;
}

export interface Vaccine {
  id: number;
  pet_id: number;
  vaccine_name: string;
  dose_no: number;
  vaccinated_at: string;
  next_due_date: string | null;
  notes: string;
  created_at: string;
}

export interface VaccinePayload {
  vaccine_name: string;
  dose_no?: number;
  vaccinated_at: string;
  next_due_date?: string | null;
  notes?: string;
}

export interface ExamPayload {
  exam_date: string;
  hospital?: string | null;
  items?: string | null;
  result?: string;
  vet_name?: string | null;
}

export interface MedicationPayload {
  drug_name: string;
  start_date?: string | null;
  end_date?: string | null;
  dosage?: string | null;
  reason?: string | null;
  notes?: string;
}

export const petsApi = {
  list: () => http.get("/pets") as Promise<Pet[]>,
  create: (data: PetPayload) => http.post("/pets", data) as Promise<Pet>,
  get: (id: number) => http.get(`/pets/${id}`) as Promise<Pet>,
  update: (id: number, data: PetPayload) => http.put(`/pets/${id}`, data) as Promise<Pet>,
  remove: (id: number) => http.delete(`/pets/${id}`) as Promise<{ detail: string }>,

  vaccines: (petId: number) => http.get(`/pets/${petId}/vaccines`) as Promise<Vaccine[]>,
  addVaccine: (petId: number, data: VaccinePayload) =>
    http.post(`/pets/${petId}/vaccines`, data) as Promise<Vaccine>,
  upcoming: (petId: number, days = 30) =>
    http.get(`/pets/${petId}/vaccines/upcoming?days=${days}`) as Promise<Vaccine[]>,
  updateVaccine: (vid: number, data: VaccinePayload) =>
    http.put(`/pets/vaccines/${vid}`, data) as Promise<Vaccine>,
  removeVaccine: (vid: number) => http.delete(`/pets/vaccines/${vid}`) as Promise<{ detail: string }>,

  exams: (petId: number) => http.get(`/pets/${petId}/health/exams`) as Promise<MedicalExam[]>,
  addExam: (petId: number, data: ExamPayload) =>
    http.post(`/pets/${petId}/health/exams`, data) as Promise<MedicalExam>,
  removeExam: (petId: number, examId: number) =>
    http.delete(`/pets/${petId}/health/exams/${examId}`) as Promise<{ detail: string }>,

  medications: (petId: number) =>
    http.get(`/pets/${petId}/health/medications`) as Promise<Medication[]>,
  addMedication: (petId: number, data: MedicationPayload) =>
    http.post(`/pets/${petId}/health/medications`, data) as Promise<Medication>,
  removeMedication: (petId: number, medId: number) =>
    http.delete(`/pets/${petId}/health/medications/${medId}`) as Promise<{ detail: string }>,
};

export type { MedicalExam, Medication } from "@/types";
