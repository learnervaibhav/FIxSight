// Mirrors the FastAPI response schemas in app/schemas.

export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown';
export type ServiceStatus = 'none' | 'scheduled' | 'in_service';
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH';
export type SlotStatus = 'PENDING' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
export type SimulationMode = 'mock' | 'real';

export interface LatestReading {
  id: number;
  timestamp: string;
  engine_rpm: number | null;
  coolant_temperature: number | null;
  oil_pressure: number | null;
  battery_voltage: number | null;
  transmission_temperature: number | null;
  vehicle_speed: number | null;
  health_score: number | null;
  degradation_index: number | null;
}

export interface FaultPrediction {
  id: number;
  vehicle_id: string;
  telemetry_reading_id: number | null;
  fault_label: string;
  fault_probability: number;
  severity: Severity;
  llm_explanation: string | null;
  maintenance_priority: string;
  recommended_service_window_hours: number;
  created_at: string;
}

export interface SlotSummary {
  slot_id: string;
  vehicle_id: string;
  center_id: string;
  center_name: string | null;
  center_latitude: number | null;
  center_longitude: number | null;
  scheduled_time: string;
  duration_hours: number;
  slot_status: SlotStatus;
  reason: string | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface VehicleOverview {
  vehicle_id: string;
  engine_type: string;
  driving_profile: string;
  manufacture_year: number;
  region: string;
  location: string;
  owner_name: string | null;
  owner_phone: string | null;
  latitude: number | null;
  longitude: number | null;
  health_status: HealthStatus;
  service_status: ServiceStatus;
  latest_reading: LatestReading | null;
  latest_fault: FaultPrediction | null;
  rul_hours: number | null;
  open_slot: SlotSummary | null;
}

export interface FleetSummary {
  total_vehicles: number;
  healthy: number;
  warning: number;
  critical: number;
  scheduled: number;
  in_service: number;
  service_centers: number;
  total_capacity: number;
  occupied_bays: number;
  alerts_total: number;
  average_health: number | null;
}

export interface FleetOverview {
  summary: FleetSummary;
  vehicles: VehicleOverview[];
}

export interface ServiceCenter {
  center_id: string;
  center_name: string;
  location: string;
  latitude: number;
  longitude: number;
  operating_hours_start: number;
  operating_hours_end: number;
  max_capacity: number;
  current_occupancy: number;
  available_slots: number;
  distance_km: number | null;
  created_at: string;
  updated_at: string;
}

export interface ServiceSlot {
  slot_id: string;
  center_id: string;
  vehicle_id: string;
  scheduled_time: string;
  duration_hours: number;
  slot_status: SlotStatus;
  reason: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TelemetryReading {
  id: number;
  vehicle_id: string;
  timestamp: string;
  engine_rpm: number;
  engine_load: number;
  coolant_temperature: number;
  oil_temperature: number;
  oil_pressure: number;
  battery_voltage: number;
  alternator_voltage: number;
  transmission_temperature: number;
  vehicle_speed: number;
  mass_air_flow: number;
  degradation_index: number;
  health_score: number;
  [key: string]: number | string;
}

export interface RULPoint {
  id: number;
  rul_hours: number;
  confidence_score: number | null;
  created_at: string;
}

export interface AlertLog {
  id: number;
  vehicle_id: string;
  fault_prediction_id: number | null;
  alert_type: string;
  channel: string;
  recipient: string | null;
  status: string;
  alert_message: string | null;
  created_at: string;
}

export interface LiveEvent {
  id: number;
  type: string;
  title: string;
  message: string;
  severity: 'info' | 'success' | 'warning' | 'critical';
  vehicle_id: string | null;
  created_at: string;
  data: Record<string, unknown>;
}

export interface SimVehicleState {
  vehicle_id: string;
  scenario: string | null;
  progress: number;
  notified: boolean;
  in_service: boolean;
  readings: number;
}

export interface SimulationStatus {
  running: boolean;
  mode: SimulationMode;
  tick: number;
  round: number;
  round_progress: number;
  sim_time: string | null;
  started_at: string | null;
  tick_seconds: number;
  sim_minutes_per_tick: number;
  vehicles_per_tick: number;
  use_llm: boolean;
  current_batch: string[];
  last_tick_ms: number;
  last_error: string | null;
  last_sms_error: string | null;
  stats: {
    readings: number;
    faults_detected: number;
    services_booked: number;
    services_started: number;
    services_completed: number;
    sms_sent: number;
    sms_mock: number;
    sms_failed?: number;
  };
  sms_limit: number;
  twilio_configured: boolean;
  llm_configured: boolean;
  vehicles: SimVehicleState[];
}

export interface SimulationStartRequest {
  mode: SimulationMode;
  tick_seconds?: number;
  sim_minutes_per_tick?: number;
  vehicles_per_tick?: number;
  fault_rate?: number;
  use_llm?: boolean;
}

export interface AgentRunResult {
  vehicle_id: string;
  fault_label?: string;
  fault_probability?: number;
  severity?: Severity;
  rul_hours?: number;
  llm_status?: string;
  llm_explanation?: string;
  maintenance_priority?: string;
  recommended_service_window_hours?: number;
  maintenance_action_items?: { title: string; owner: string; priority: string; due_in_hours: number; notes: string }[];
  service_booking_status?: string;
  selected_service_center?: { center_name: string; distance_km?: number };
  scheduled_slot_time?: string;
  alert_status?: string;
  alert_message?: string;
  errors?: string[];
}

export interface TwilioCheck {
  ok: boolean;
  issues: string[];
  sender?: string;
  recipient?: string;
  account_status?: string;
  account_type?: string;
  owned_numbers?: string[];
}
