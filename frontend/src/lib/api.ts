import axios, { AxiosError } from 'axios';
import type {
  AgentRunResult,
  AlertLog,
  FaultPrediction,
  FleetOverview,
  LiveEvent,
  RULPoint,
  ServiceCenter,
  ServiceSlot,
  SimulationStartRequest,
  SimulationStatus,
  SlotStatus,
  SlotSummary,
  TelemetryReading,
  TwilioCheck,
} from '../types/api';

// Relative by default: Vite (dev) and nginx (Docker) proxy /api to FastAPI.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 30000,
});

export function errorMessage(error: unknown): string {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ');
    if (!error.response) return 'Backend is unreachable';
    return error.message;
  }
  return error instanceof Error ? error.message : 'Unexpected error';
}

const get = async <T>(url: string, params?: Record<string, unknown>) => (await apiClient.get<T>(url, { params })).data;
const post = async <T>(url: string, body?: unknown) => (await apiClient.post<T>(url, body)).data;

export const api = {
  health: () => get<{ status: string }>('/health'),

  fleetOverview: () => get<FleetOverview>('/api/fleet/overview'),
  vehicleTelemetry: (vehicleId: string, limit = 60) =>
    get<{ vehicle_id: string; readings: TelemetryReading[]; total: number }>(`/api/vehicles/${vehicleId}/telemetry`, { limit }),
  vehiclePredictions: (vehicleId: string, limit = 60) =>
    get<{ vehicle_id: string; faults: FaultPrediction[]; rul: RULPoint[] }>(`/api/vehicles/${vehicleId}/predictions`, { limit }),
  recentFaults: (params: { severity?: string; vehicle_id?: string; limit?: number } = {}) =>
    get<{ predictions: FaultPrediction[]; total: number }>('/api/predictions/faults', params),

  runAgent: (vehicleId: string, body: Record<string, unknown>) => post<AgentRunResult>(`/api/agent/run/${vehicleId}`, body),

  serviceCenters: () => get<{ centers: ServiceCenter[]; total: number }>('/api/service/centers'),
  nearbyCenters: (latitude: number, longitude: number, radius_km = 25) =>
    get<{ centers: ServiceCenter[]; total: number }>('/api/service/centers/nearby', { latitude, longitude, radius_km }),
  slots: (slot_status?: string) => get<{ slots: SlotSummary[]; total: number }>('/api/service/slots', { slot_status }),
  vehicleSlots: (vehicleId: string) => get<{ slots: ServiceSlot[]; total: number }>(`/api/service/schedule/${vehicleId}`),
  scheduleService: (body: { vehicle_id: string; center_id: string; scheduled_time?: string; duration_hours: number; reason?: string }) =>
    post<ServiceSlot>('/api/service/schedule', body),
  updateSlot: async (slotId: string, slot_status: Exclude<SlotStatus, 'PENDING'>) =>
    (await apiClient.patch<ServiceSlot>(`/api/service/slots/${slotId}`, { slot_status })).data,

  alerts: (params: { vehicle_id?: string; alert_type?: string; limit?: number } = {}) =>
    get<{ alerts: AlertLog[]; total: number }>('/api/alerts', params),

  events: (after_id: number) => get<{ events: LiveEvent[]; last_id: number }>('/api/events', { after_id, limit: 200 }),

  twilioCheck: () => get<TwilioCheck>('/api/simulation/twilio-check'),
  simulationStatus: () => get<SimulationStatus>('/api/simulation/status'),
  startSimulation: (body: SimulationStartRequest) => post<SimulationStatus>('/api/simulation/start', body),
  stopSimulation: () => post<SimulationStatus>('/api/simulation/stop'),
  resetSimulation: () => post<SimulationStatus>('/api/simulation/reset'),
  stepSimulation: () => post<SimulationStatus>('/api/simulation/tick'),
};
