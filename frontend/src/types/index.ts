export interface UserInfo {
  id: number;
  username: string;
  email: string | null;
  role: string;
  store_id?: number | null;
  staff_role?: string | null;
  store_type?: string | null;
  points?: number;
  created_at: string;
}

export interface TokenResult {
  access_token: string;
  token_type: string;
}

export interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  is_public: boolean;
  created_at: string;
  doc_count?: number;
}

export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  status: "uploading" | "indexing" | "indexed" | "failed" | string;
  kb_id?: number;
  created_at: string;
}

export interface ChatConversation {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatReply {
  id: number;
  conversation_id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface MessageItem {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  tools?: string[];
}

export interface LoginForm {
  username: string;
  password: string;
}

export interface RegisterForm {
  username: string;
  email: string;
  password: string;
  role?: string;
}

export interface MedicalExam {
  id: number;
  pet_id: number;
  exam_date: string;
  hospital: string | null;
  items: string | null;
  result: string;
  vet_name: string | null;
  created_at: string;
}

export interface Medication {
  id: number;
  pet_id: number;
  drug_name: string;
  start_date: string | null;
  end_date: string | null;
  dosage: string | null;
  reason: string | null;
  notes: string;
  created_at: string;
}

export interface Store {
  id: number;
  name: string;
  store_type: string;
  address: string | null;
  phone: string | null;
  city?: string | null;
  rating?: number;
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
  is_active: boolean;
  created_at: string;
  store_name?: string | null;
  store_phone?: string | null;
  store_address?: string | null;
  store_city?: string | null;
  store_rating?: number | null;
  stock?: number;
  promo?: string | null;
  shipping_mode?: string;
  brand?: string | null;
  package_spec?: string | null;
}

export interface Appointment {
  id: number;
  user_id: number;
  pet_id: number | null;
  store_id: number | null;
  trainer_id?: number | null;
  appt_type: string;
  appt_time: string;
  status: string;
  notes: string;
  created_at: string;
  store_name?: string | null;
  store_type?: string | null;
  trainer_name?: string | null;
  pet_name?: string | null;
  user_name?: string | null;
}

export interface Boarding {
  id: number;
  user_id: number;
  pet_id: number;
  store_id: number | null;
  start_date: string;
  end_date: string;
  daily_fee: number | null;
  notes: string;
  status: string;
  created_at: string;
}

export interface PetListing {
  id: number;
  store_id: number;
  store_name?: string | null;
  store_phone?: string | null;
  store_address?: string | null;
  store_city?: string | null;
  store_rating?: number | null;
  name: string;
  species: string;
  breed: string | null;
  gender: string;
  age_months: number | null;
  price: number | null;
  health_note: string | null;
  vaccine_note: string | null;
  description: string;
  appearance?: string;
  color?: string | null;
  weight_kg?: number | null;
  image_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Trainer {
  id: number;
  user_id: number;
  display_name: string;
  city: string | null;
  specialties: string;
  years: number;
  price_from: number | null;
  service_mode: string;
  bio: string;
  avatar_url?: string | null;
  experience?: string;
  cert_note?: string;
  proof_images?: string[];
  verified: boolean;
  created_at: string;
}

export interface Lead {
  id: number;
  user_id: number;
  user_name?: string | null;
  operator_id: number | null;
  need_type: string;
  summary: string;
  city: string | null;
  budget: number | null;
  status: string;
  matched_store_id: number | null;
  matched_store_name: string | null;
  matched_trainer_id: number | null;
  matched_trainer_name: string | null;
  created_at: string;
}

export interface OrderItem {
  id: number;
  product_id: number | null;
  name: string;
  qty: number;
  price: number;
}

export interface Order {
  id: number;
  user_id: number;
  store_id: number;
  store_name?: string | null;
  status: string;
  shipping_mode: string;
  address: string;
  total: number;
  notes: string;
  items: OrderItem[];
  created_at: string;
}

export interface VaccineRecall {
  vaccine_id: number;
  pet_id: number;
  pet_name: string;
  species: string;
  owner_id: number;
  owner_name: string;
  vaccine_name: string;
  dose_no: number;
  next_due_date: string;
  status: string;
  days_left: number;
}