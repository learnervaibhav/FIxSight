import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Search, Truck } from 'lucide-react';
import { useLive } from '../context/live';
import type { HealthStatus } from '../types/api';
import { cn, formatDateTime, formatNumber, percent } from '../lib/utils';
import { Card, EmptyState, PageHeader, Spinner } from '../components/ui/primitives';
import { HealthBadge, ServiceBadge } from '../components/ui/StatusBadges';

const FILTERS: { id: 'all' | HealthStatus | 'service'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'critical', label: 'Critical' },
  { id: 'warning', label: 'Warning' },
  { id: 'healthy', label: 'Healthy' },
  { id: 'service', label: 'In service pipeline' },
];

export function FleetPage() {
  const { overview } = useLive();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['id']>('all');
  const [query, setQuery] = useState('');

  const vehicles = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (overview?.vehicles ?? []).filter((vehicle) => {
      if (filter === 'service' && vehicle.service_status === 'none') return false;
      if (filter !== 'all' && filter !== 'service' && vehicle.health_status !== filter) return false;
      if (!q) return true;
      return [vehicle.vehicle_id, vehicle.owner_name, vehicle.location, vehicle.engine_type].some((field) => field?.toLowerCase().includes(q));
    });
  }, [overview, filter, query]);

  const counts = useMemo(() => {
    const list = overview?.vehicles ?? [];
    return {
      all: list.length,
      critical: list.filter((v) => v.health_status === 'critical').length,
      warning: list.filter((v) => v.health_status === 'warning').length,
      healthy: list.filter((v) => v.health_status === 'healthy' || v.health_status === 'unknown').length,
      unknown: 0,
      service: list.filter((v) => v.service_status !== 'none').length,
    };
  }, [overview]);

  return (
    <>
      <PageHeader title="Fleet" description="Every vehicle with its latest reading, AI prediction and service state." />

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-4 dark:border-slate-800">
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setFilter(option.id)}
                className={cn(
                  'rounded-full px-3 py-1 text-xs font-medium',
                  filter === option.id ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300',
                )}
              >
                {option.label} <span className="opacity-70">{counts[option.id as keyof typeof counts]}</span>
              </button>
            ))}
          </div>
          <label className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2 size-4 text-slate-400" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search vehicle, owner, area…"
              className="w-64 rounded-lg border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900"
            />
          </label>
        </div>

        {!overview ? (
          <Spinner />
        ) : vehicles.length === 0 ? (
          <EmptyState icon={<Truck className="size-8" />} title="No vehicles match" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                <tr>
                  <th className="px-5 py-3 font-medium">Vehicle</th>
                  <th className="px-3 py-3 font-medium">Owner / area</th>
                  <th className="px-3 py-3 font-medium">Status</th>
                  <th className="px-3 py-3 font-medium">Health</th>
                  <th className="px-3 py-3 font-medium">RUL</th>
                  <th className="px-3 py-3 font-medium">Latest prediction</th>
                  <th className="px-3 py-3 font-medium">Coolant / Oil / Battery</th>
                  <th className="px-3 py-3 font-medium">Service</th>
                  <th className="px-3 py-3 font-medium">Last reading</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {vehicles.map((vehicle) => {
                  const reading = vehicle.latest_reading;
                  const fault = vehicle.latest_fault;
                  return (
                    <tr
                      key={vehicle.vehicle_id}
                      onClick={() => navigate(`/fleet/${vehicle.vehicle_id}`)}
                      className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/40"
                    >
                      <td className="px-5 py-3">
                        <Link to={`/fleet/${vehicle.vehicle_id}`} className="font-medium text-blue-600 hover:underline" onClick={(event) => event.stopPropagation()}>
                          {vehicle.vehicle_id}
                        </Link>
                        <p className="text-xs capitalize text-slate-500">
                          {vehicle.engine_type.replace('_', ' ')} · {vehicle.manufacture_year}
                        </p>
                      </td>
                      <td className="px-3 py-3">
                        <p>{vehicle.owner_name ?? '—'}</p>
                        <p className="text-xs text-slate-500">{vehicle.location}</p>
                      </td>
                      <td className="px-3 py-3"><HealthBadge status={vehicle.health_status} /></td>
                      <td className="px-3 py-3 tabular-nums">{formatNumber(reading?.health_score, 1)}</td>
                      <td className="px-3 py-3 tabular-nums">{formatNumber(vehicle.rul_hours)} h</td>
                      <td className="px-3 py-3">
                        {fault ? (
                          <span className={fault.fault_label === 'normal' ? 'text-slate-500' : ''}>
                            {fault.fault_label === 'normal' ? 'Normal' : fault.fault_label}{' '}
                            <span className="text-xs text-slate-500">{fault.fault_label === 'normal' ? '' : percent(fault.fault_probability)}</span>
                          </span>
                        ) : (
                          <span className="text-slate-400">Not analysed</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-xs tabular-nums text-slate-600 dark:text-slate-300">
                        {formatNumber(reading?.coolant_temperature, 1)}°C · {formatNumber(reading?.oil_pressure, 1)} psi · {formatNumber(reading?.battery_voltage, 2)} V
                      </td>
                      <td className="px-3 py-3"><ServiceBadge status={vehicle.service_status} /></td>
                      <td className="px-3 py-3 text-xs text-slate-500">{formatDateTime(reading?.timestamp)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
