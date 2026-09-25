import http from "./http";

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
  store_name?: string | null;
  store_type?: string | null;
  trainer_name?: string | null;
  pet_name?: string | null;
  user_name?: string | null;
  created_at: string;
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
  store_name?: string | null;
  pet_name?: string | null;
  created_at: string;
}

export interface AppointmentPayload {
  pet_id?: number | null;
  store_id?: number | null;
  trainer_id?: number | null;
  appt_type?: string;
  appt_time: string;
  notes?: string;
}

export interface BoardingPayload {
  pet_id: number;
  store_id?: number | null;
  start_date: string;
  end_date: string;
  daily_fee?: number | null;
  notes?: string;
}

export const bookingApi = {
  appointments: () => http.get("/booking/appointments") as Promise<Appointment[]>,
  createAppointment: (data: AppointmentPayload) =>
    http.post("/booking/appointments", data) as Promise<Appointment>,
  cancelAppointment: (id: number) =>
    http.post(`/booking/appointments/${id}/cancel`) as Promise<{ detail: string }>,

  trainerAppointments: (status?: string) =>
    http.get("/booking/trainer/appointments", { params: { status } }) as Promise<Appointment[]>,
  trainerSetStatus: (id: number, status: string) =>
    http.post(`/booking/trainer/appointments/${id}/status`, { status }) as Promise<Appointment>,

  boardings: () => http.get("/booking/boardings") as Promise<Boarding[]>,
  createBoarding: (data: BoardingPayload) =>
    http.post("/booking/boardings", data) as Promise<Boarding>,
  cancelBoarding: (id: number) =>
    http.post(`/booking/boardings/${id}/cancel`) as Promise<{ detail: string }>,
};
