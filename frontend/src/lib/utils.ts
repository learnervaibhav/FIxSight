import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { HealthStatus, ServiceCenter, Severity, SlotStatus } from '../types/api';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Backend datetimes are naive local times (simulation clock) -> parse as local.
export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDateTime(value: string | null | undefined): string {
  const date = parseDate(value);
  if (!date) return '—';
  return date.toLocaleString(undefined, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export function formatTime(value: string | null | undefined): string {
  const date = parseDate(value);
  return date ? date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function percent(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`;
}

export const HEALTH_COLORS: Record<HealthStatus, string> = {
  healthy: '#16a34a',
  warning: '#d97706',
  critical: '#dc2626',
  unknown: '#64748b',
};

export const HEALTH_LABELS: Record<HealthStatus, string> = {
  healthy: 'Healthy',
  warning: 'Warning',
  critical: 'Critical',
  unknown: 'No data',
};

export type Tone = 'neutral' | 'green' | 'amber' | 'red' | 'blue' | 'violet';

export const healthTone = (status: HealthStatus): Tone =>
  ({ healthy: 'green', warning: 'amber', critical: 'red', unknown: 'neutral' })[status] as Tone;

export const severityTone = (severity: Severity | string | null | undefined): Tone =>
  severity === 'HIGH' ? 'red' : severity === 'MEDIUM' ? 'amber' : 'green';

const SLOT_TONES: Record<SlotStatus, Tone> = { PENDING: 'blue', ACTIVE: 'violet', COMPLETED: 'green', CANCELLED: 'neutral' };

export const slotTone = (status: SlotStatus | string): Tone => SLOT_TONES[status as SlotStatus] ?? 'neutral';

export const alertStatusTone = (status: string): Tone =>
  status === 'sent' ? 'green' : status === 'mock_sent' ? 'blue' : status === 'failed' ? 'red' : 'amber';

export function occupancyRatio(center: Pick<ServiceCenter, 'current_occupancy' | 'max_capacity'>): number {
  return center.max_capacity ? center.current_occupancy / center.max_capacity : 0;
}

export function occupancyColor(ratio: number): string {
  if (ratio >= 0.85) return '#dc2626';
  if (ratio >= 0.5) return '#d97706';
  return '#16a34a';
}

export function isOpenAt(center: Pick<ServiceCenter, 'operating_hours_start' | 'operating_hours_end'>, at: Date): boolean {
  const hour = at.getHours() + at.getMinutes() / 60;
  return hour >= center.operating_hours_start && hour < center.operating_hours_end;
}

export function hoursLabel(center: Pick<ServiceCenter, 'operating_hours_start' | 'operating_hours_end'>): string {
  const pad = (h: number) => `${String(h).padStart(2, '0')}:00`;
  return `${pad(center.operating_hours_start)}–${pad(center.operating_hours_end)}`;
}
