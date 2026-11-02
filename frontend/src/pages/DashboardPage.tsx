import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, Building2, CalendarClock, HeartPulse, MessageSquareText, Truck } from 'lucide-react';
import { useLive } from '../context/live';
import { useApi } from '../hooks/useApi';
import { useIsDark } from '../hooks/useIsDark';
import { api } from '../lib/api';
import { formatDateTime, formatNumber, hoursLabel, isOpenAt, occupancyColor, occupancyRatio, parseDate, percent } from '../lib/utils';
import { FleetMap } from '../components/map/FleetMap';
import { ActivityFeed } from '../components/dashboard/ActivityFeed';
import { Card, CardHeader, EmptyState, PageHeader, ProgressBar, Spinner, StatCard } from '../components/ui/primitives';
import { HealthBadge, ServiceBadge } from '../components/ui/StatusBadges';

const SEVERITY_ORDER = { critical: 0, warning: 1, unknown: 2, healthy: 3 } as const;

export function DashboardPage() {
  const { overview, status, events } = useLive();
  const { data: centersData } = useApi(api.serviceCenters);
  const dark = useIsDark();

  const centers = centersData?.centers ?? [];
  const summary = overview?.summary;
  const clock = parseDate(status?.sim_time) ?? new Date();

  const attention = (overview?.vehicles ?? [])
    .filter((vehicle) => vehicle.health_status === 'critical' || vehicle.health_status === 'warning' || vehicle.service_status !== 'none')
    .sort((a, b) => SEVERITY_ORDER[a.health_status] - SEVERITY_ORDER[b.health_status]);

  return (
    <>
      <PageHeader
        title="Fleet overview"
        description="Live telemetry, AI fault predictions and service-center capacity across Delhi NCR."
      />

      {status?.running && (
        <Card className="mb-6 grid grid-cols-2 gap-4 p-4 text-sm sm:grid-cols-4 xl:grid-cols-8">
          {[
            ['Sim clock', formatDateTime(status.sim_time)],
            ['Round', `${status.round} (${percent(status.round_progress)})`],
            ['Tick', status.tick],
            ['Readings', status.stats.readings],
            ['Faults found', status.stats.faults_detected],
            ['Booked', status.stats.services_booked],
            ['Completed', status.stats.services_completed],
            [status.mode === 'real' ? 'SMS sent / failed' : 'Mock SMS', status.mode === 'real' ? `${status.stats.sms_sent}/${status.sms_limit} · ${status.stats.sms_failed ?? 0}` : status.stats.sms_mock],
          ].map(([label, value]) => (
            <div key={String(label)}>
              <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
              <p className="font-semibold tabular-nums">{value}</p>
            </div>
          ))}
          {status.last_error && <p className="col-span-full text-xs text-red-600">Last tick error: {status.last_error}</p>}
          {status.mode === 'real' && status.last_sms_error && (
            <div className="col-span-full rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/50 dark:text-red-300">
              <b>SMS not delivered ({status.stats.sms_failed ?? 0} failed):</b> {status.last_sms_error}. Fix the Twilio settings in app/core/.env and restart the backend.
            </div>
          )}
        </Card>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
        <StatCard label="Vehicles" value={summary?.total_vehicles ?? '—'} hint={`${summary?.healthy ?? 0} healthy`} icon={<Truck className="size-5" />} tone="blue" />
        <StatCard label="Avg health" value={formatNumber(summary?.average_health, 1)} hint="Latest readings, 0–100" icon={<HeartPulse className="size-5" />} tone="green" />
        <StatCard
          label="Needs attention"
          value={(summary?.critical ?? 0) + (summary?.warning ?? 0)}
          hint={`${summary?.critical ?? 0} critical · ${summary?.warning ?? 0} warning`}
          icon={<AlertTriangle className="size-5" />}
          tone="red"
        />
        <StatCard
          label="Service pipeline"
          value={(summary?.scheduled ?? 0) + (summary?.in_service ?? 0)}
          hint={`${summary?.scheduled ?? 0} booked · ${summary?.in_service ?? 0} in bay`}
          icon={<CalendarClock className="size-5" />}
          tone="violet"
        />
        <StatCard
          label="Bays occupied"
          value={`${summary?.occupied_bays ?? 0}/${summary?.total_capacity ?? 0}`}
          hint={`${summary?.service_centers ?? 0} service centers`}
          icon={<Building2 className="size-5" />}
          tone="amber"
        />
        <StatCard label="Alerts sent" value={summary?.alerts_total ?? 0} hint="SMS log (real + mock)" icon={<MessageSquareText className="size-5" />} />
      </div>

      <div className="mb-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader
            title="Live fleet map"
            subtitle="Vehicles at owner locations · service centers coloured by occupancy · dashed line = booked, solid = in service"
          />
          {overview ? <FleetMap centers={centers} vehicles={overview.vehicles} clock={clock} dark={dark} /> : <Spinner />}
        </Card>

        <Card className="flex max-h-[540px] flex-col">
          <CardHeader title="Live activity" subtitle="Faults, bookings and SMS from the agent pipeline" action={<Activity className="size-4 text-slate-400" />} />
          <div className="flex-1 overflow-y-auto">
            <ActivityFeed events={events} />
          </div>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Vehicles needing attention" subtitle="Critical/warning predictions and vehicles in the service pipeline" action={<Link to="/fleet" className="text-xs font-medium text-blue-600 hover:underline">View fleet</Link>} />
          {attention.length === 0 ? (
            <EmptyState icon={<HeartPulse className="size-8" />} title="All vehicles healthy" description="Nothing needs attention right now." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                  <tr>
                    <th className="px-5 py-2.5 font-medium">Vehicle</th>
                    <th className="px-3 py-2.5 font-medium">Status</th>
                    <th className="px-3 py-2.5 font-medium">Predicted fault</th>
                    <th className="px-3 py-2.5 font-medium">RUL</th>
                    <th className="px-3 py-2.5 font-medium">Service</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {attention.map((vehicle) => (
                    <tr key={vehicle.vehicle_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="px-5 py-2.5">
                        <Link to={`/fleet/${vehicle.vehicle_id}`} className="font-medium text-blue-600 hover:underline">
                          {vehicle.vehicle_id}
                        </Link>
                        <p className="text-xs text-slate-500">{vehicle.owner_name}</p>
                      </td>
                      <td className="px-3 py-2.5"><HealthBadge status={vehicle.health_status} /></td>
                      <td className="px-3 py-2.5">
                        {vehicle.latest_fault && vehicle.latest_fault.fault_label !== 'normal' ? (
                          <>
                            {vehicle.latest_fault.fault_label}
                            <span className="ml-1 text-xs text-slate-500">{percent(vehicle.latest_fault.fault_probability)}</span>
                          </>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 tabular-nums">{formatNumber(vehicle.rul_hours)} h</td>
                      <td className="px-3 py-2.5">
                        <ServiceBadge status={vehicle.service_status} />
                        {vehicle.open_slot && <p className="mt-0.5 text-xs text-slate-500">{vehicle.open_slot.center_name?.replace('Delhi Service ', '')}</p>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card>
          <CardHeader title="Service center capacity" subtitle={`Open/closed at ${clock.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}${status?.running ? ' (sim time)' : ''}`} />
          {centers.length === 0 ? (
            <EmptyState icon={<Building2 className="size-8" />} title="No service centers" description="Run scripts/bootstrap.py to seed the 10 Delhi NCR centers." />
          ) : (
            <ul className="space-y-3 p-5">
              {centers.map((center) => {
                const ratio = occupancyRatio(center);
                const open = isOpenAt(center, clock);
                return (
                  <li key={center.center_id}>
                    <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                      <span className="truncate font-medium">{center.location}</span>
                      <span className="shrink-0 text-xs tabular-nums text-slate-500">
                        <span className={open ? 'text-emerald-600' : 'text-slate-400'}>{open ? 'Open' : 'Closed'}</span> · {hoursLabel(center)} ·{' '}
                        <b className="text-slate-700 dark:text-slate-200">
                          {center.current_occupancy}/{center.max_capacity}
                        </b>
                      </span>
                    </div>
                    <ProgressBar value={ratio} color={occupancyColor(ratio)} />
                  </li>
                );
              })}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
