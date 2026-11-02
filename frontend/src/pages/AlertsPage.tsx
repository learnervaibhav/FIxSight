import { useState } from 'react';
import { Link } from 'react-router-dom';
import { BellOff } from 'lucide-react';
import { useLive } from '../context/live';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';
import { cn, formatDateTime } from '../lib/utils';
import { Card, EmptyState, ErrorBanner, PageHeader, Spinner } from '../components/ui/primitives';
import { AlertStatusBadge } from '../components/ui/StatusBadges';

const TYPES = [
  { id: '', label: 'All' },
  { id: 'fault', label: 'Fault alerts' },
  { id: 'service_completed', label: 'Service completed' },
];

export function AlertsPage() {
  const { status } = useLive();
  const [type, setType] = useState('');
  const { data, error, loading } = useApi(() => api.alerts({ alert_type: type || undefined, limit: 200 }), [type]);

  return (
    <>
      <PageHeader
        title="Alerts & SMS log"
        description={
          status?.twilio_configured
            ? 'Every notification sent by the alert dispatcher. Real mode delivers via Twilio; mock mode only logs.'
            : 'Every notification sent by the alert dispatcher. Twilio is not configured, so only mock mode is available.'
        }
        actions={
          <div className="flex gap-1.5">
            {TYPES.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setType(option.id)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium',
                  type === option.id ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      />
      <ErrorBanner message={error} />

      <Card>
        {loading && !data ? (
          <Spinner />
        ) : !data?.alerts.length ? (
          <EmptyState icon={<BellOff className="size-8" />} title="No alerts yet" description="High-severity faults trigger an SMS (or a dev notification in mock mode)." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                <tr>
                  <th className="px-5 py-2.5 font-medium">Time</th>
                  <th className="px-3 py-2.5 font-medium">Vehicle</th>
                  <th className="px-3 py-2.5 font-medium">Type</th>
                  <th className="px-3 py-2.5 font-medium">Status</th>
                  <th className="px-3 py-2.5 font-medium">Recipient</th>
                  <th className="px-3 py-2.5 font-medium">Message</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 align-top dark:divide-slate-800">
                {data.alerts.map((alert) => (
                  <tr key={alert.id}>
                    <td className="whitespace-nowrap px-5 py-3 tabular-nums text-slate-500">{formatDateTime(alert.created_at)}</td>
                    <td className="px-3 py-3">
                      <Link to={`/fleet/${alert.vehicle_id}`} className="font-medium text-blue-600 hover:underline">
                        {alert.vehicle_id}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 capitalize">{alert.alert_type.replace('_', ' ')}</td>
                    <td className="px-3 py-3"><AlertStatusBadge status={alert.status} /></td>
                    <td className="px-3 py-3 text-xs text-slate-500">{alert.recipient ?? '—'}</td>
                    <td className="max-w-xl px-3 py-3">
                      <p className="whitespace-pre-line text-xs text-slate-600 dark:text-slate-300">{alert.alert_message}</p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
