import type { HealthStatus, ServiceStatus, Severity, SlotStatus } from '../../types/api';
import { HEALTH_LABELS, alertStatusTone, healthTone, severityTone, slotTone } from '../../lib/utils';
import { Badge } from './primitives';

export function HealthBadge({ status }: { status: HealthStatus }) {
  return (
    <Badge tone={healthTone(status)}>
      <span className="size-1.5 rounded-full bg-current" />
      {HEALTH_LABELS[status]}
    </Badge>
  );
}

export function SeverityBadge({ severity }: { severity: Severity | string }) {
  return <Badge tone={severityTone(severity)}>{severity}</Badge>;
}

export function ServiceBadge({ status }: { status: ServiceStatus }) {
  if (status === 'none') return <span className="text-xs text-slate-400">—</span>;
  return <Badge tone={status === 'in_service' ? 'violet' : 'blue'}>{status === 'in_service' ? 'In service' : 'Scheduled'}</Badge>;
}

export function SlotBadge({ status }: { status: SlotStatus | string }) {
  return <Badge tone={slotTone(status)}>{status.charAt(0) + status.slice(1).toLowerCase()}</Badge>;
}

const ALERT_LABELS: Record<string, string> = {
  sent: 'Sent (Twilio)',
  mock_sent: 'Mock (dev)',
  failed: 'Failed',
  not_configured: 'Twilio not configured',
  rate_limited: 'SMS limit reached',
};

export function AlertStatusBadge({ status }: { status: string }) {
  return <Badge tone={alertStatusTone(status)}>{ALERT_LABELS[status] ?? status}</Badge>;
}
