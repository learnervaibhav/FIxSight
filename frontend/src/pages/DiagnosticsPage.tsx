import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Stethoscope } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { api } from '../lib/api';
import { cn, formatDateTime, percent } from '../lib/utils';
import { Card, EmptyState, ErrorBanner, PageHeader, ProgressBar, Spinner } from '../components/ui/primitives';
import { SeverityBadge } from '../components/ui/StatusBadges';

const FILTERS = [
  { id: 'HIGH,MEDIUM', label: 'High & medium' },
  { id: 'HIGH', label: 'High' },
  { id: 'MEDIUM', label: 'Medium' },
  { id: 'LOW', label: 'Low' },
];

export function DiagnosticsPage() {
  const [severity, setSeverity] = useState('HIGH,MEDIUM');
  const { data, error, loading } = useApi(() => api.recentFaults({ severity, limit: 60 }), [severity]);

  // One card per vehicle+fault episode: keep the newest prediction of each.
  const seen = new Set<string>();
  const items = (data?.predictions ?? []).filter((prediction) => {
    const key = `${prediction.vehicle_id}|${prediction.fault_label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return (
    <>
      <PageHeader
        title="Diagnostics"
        description="XGBoost fault predictions with Gemini explanations and recommended maintenance windows."
        actions={
          <div className="flex gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setSeverity(option.id)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium',
                  severity === option.id ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50 dark:bg-slate-900 dark:text-slate-300 dark:ring-slate-700',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      />
      <ErrorBanner message={error} />

      {loading && !data ? (
        <Spinner />
      ) : items.length === 0 ? (
        <Card>
          <EmptyState icon={<Stethoscope className="size-8" />} title="No fault predictions yet" description="Start a simulation: faulty vehicles will appear here with AI explanations." />
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {items.map((prediction) => (
            <Card key={prediction.id} className="flex flex-col p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold">{prediction.fault_label}</p>
                  <Link to={`/fleet/${prediction.vehicle_id}`} className="text-sm text-blue-600 hover:underline">
                    {prediction.vehicle_id}
                  </Link>
                  <span className="text-xs text-slate-500"> · {formatDateTime(prediction.created_at)}</span>
                </div>
                <SeverityBadge severity={prediction.severity} />
              </div>
              <div className="mt-3 flex items-center gap-3 text-xs text-slate-500">
                <span className="w-20 shrink-0">Confidence</span>
                <ProgressBar value={prediction.fault_probability} color={prediction.severity === 'HIGH' ? '#dc2626' : prediction.severity === 'MEDIUM' ? '#d97706' : '#16a34a'} />
                <span className="w-10 text-right tabular-nums">{percent(prediction.fault_probability)}</span>
              </div>
              <p className="mt-3 flex-1 whitespace-pre-line text-sm text-slate-600 dark:text-slate-300">{prediction.llm_explanation ?? 'No explanation recorded.'}</p>
              <div className="mt-4 flex gap-4 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-800">
                <span>
                  Priority <b className="text-slate-700 dark:text-slate-200">{prediction.maintenance_priority}</b>
                </span>
                <span>
                  Service within <b className="text-slate-700 dark:text-slate-200">{prediction.recommended_service_window_hours} h</b>
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
