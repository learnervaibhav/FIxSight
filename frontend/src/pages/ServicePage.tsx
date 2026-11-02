import { useMemo, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Building2, CalendarPlus } from 'lucide-react';
import { useLive } from '../context/live';
import { useApi } from '../hooks/useApi';
import { useIsDark } from '../hooks/useIsDark';
import { api, errorMessage } from '../lib/api';
import type { SlotStatus } from '../types/api';
import { cn, formatDateTime, hoursLabel, isOpenAt, occupancyColor, occupancyRatio, parseDate } from '../lib/utils';
import { FleetMap } from '../components/map/FleetMap';
import { Button, Card, CardHeader, EmptyState, ErrorBanner, PageHeader, ProgressBar, Spinner } from '../components/ui/primitives';
import { SlotBadge } from '../components/ui/StatusBadges';

const SLOT_FILTERS = [
  { id: 'PENDING,ACTIVE', label: 'Open' },
  { id: 'COMPLETED', label: 'Completed' },
  { id: 'CANCELLED', label: 'Cancelled' },
  { id: '', label: 'All' },
];

const inputClass =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500 dark:border-slate-700 dark:bg-slate-900';

export function ServicePage() {
  const { overview, status, refresh } = useLive();
  const dark = useIsDark();
  const [params] = useSearchParams();
  const [slotFilter, setSlotFilter] = useState('PENDING,ACTIVE');

  const centers = useApi(api.serviceCenters);
  const slots = useApi(() => api.slots(slotFilter || undefined), [slotFilter]);

  const [vehicleId, setVehicleId] = useState(params.get('vehicle') ?? '');
  const [centerId, setCenterId] = useState('');
  const [when, setWhen] = useState('');
  const [duration, setDuration] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formOk, setFormOk] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const vehicles = useMemo(() => overview?.vehicles ?? [], [overview]);
  const clock = parseDate(status?.sim_time) ?? new Date();
  const effectiveVehicleId = vehicleId || vehicles[0]?.vehicle_id || '';
  const selectedVehicle = vehicles.find((vehicle) => vehicle.vehicle_id === effectiveVehicleId);

  const nearby = useApi(
    async () => (selectedVehicle?.latitude != null ? api.nearbyCenters(selectedVehicle.latitude, selectedVehicle.longitude!, 60) : null),
    [selectedVehicle?.vehicle_id],
  );
  const centerOptions = useMemo(() => nearby.data?.centers ?? centers.data?.centers ?? [], [nearby.data, centers.data]);
  const effectiveCenterId = centerOptions.some((center) => center.center_id === centerId)
    ? centerId
    : (centerOptions.find((center) => center.available_slots > 0)?.center_id ?? '');

  const centerCounts = useMemo(() => {
    const counts = new Map<string, { pending: number; active: number }>();
    for (const vehicle of vehicles) {
      const slot = vehicle.open_slot;
      if (!slot) continue;
      const entry = counts.get(slot.center_id) ?? { pending: 0, active: 0 };
      if (slot.slot_status === 'ACTIVE') entry.active += 1;
      else entry.pending += 1;
      counts.set(slot.center_id, entry);
    }
    return counts;
  }, [vehicles]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    setFormOk(null);
    try {
      const slot = await api.scheduleService({
        vehicle_id: effectiveVehicleId,
        center_id: effectiveCenterId,
        duration_hours: duration,
        scheduled_time: when ? `${when}:00` : undefined,
        reason: 'Manual booking',
      });
      setFormOk(`Booked ${slot.vehicle_id} for ${formatDateTime(slot.scheduled_time)}`);
      refresh();
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const updateSlot = async (slotId: string, next: Exclude<SlotStatus, 'PENDING'>) => {
    setActionError(null);
    try {
      await api.updateSlot(slotId, next);
      refresh();
    } catch (error) {
      setActionError(errorMessage(error));
    }
  };

  return (
    <>
      <PageHeader title="Service centers" description="Live bay occupancy, the booking queue, and manual scheduling." />

      <div className="mb-6 grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader title="Service network" subtitle="Ring colour = occupancy · dashed ring = closed now · lines show booked vehicles" />
          {overview && centers.data ? <FleetMap centers={centers.data.centers} vehicles={vehicles} clock={clock} dark={dark} height={420} /> : <Spinner />}
        </Card>

        <Card>
          <CardHeader title="Book a service" subtitle="Leave time empty to use the center's next opening" action={<CalendarPlus className="size-4 text-slate-400" />} />
          <form onSubmit={(event) => void submit(event)} className="space-y-3 p-5">
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
              Vehicle
              <select value={effectiveVehicleId} onChange={(event) => setVehicleId(event.target.value)} className={cn(inputClass, 'mt-1')} required>
                {vehicles.map((vehicle) => (
                  <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>
                    {vehicle.vehicle_id} · {vehicle.owner_name} ({vehicle.location})
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
              Service center {selectedVehicle && <span className="font-normal text-slate-400">(nearest first)</span>}
              <select value={effectiveCenterId} onChange={(event) => setCenterId(event.target.value)} className={cn(inputClass, 'mt-1')} required>
                {centerOptions.map((center) => (
                  <option key={center.center_id} value={center.center_id} disabled={center.available_slots <= 0}>
                    {center.location}
                    {center.distance_km != null ? ` · ${center.distance_km} km` : ''} · {center.available_slots} free · {hoursLabel(center)}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-3 gap-3">
              <label className="col-span-2 block text-xs font-medium text-slate-600 dark:text-slate-300">
                Time (optional)
                <input type="datetime-local" step={3600} value={when} onChange={(event) => setWhen(event.target.value)} className={cn(inputClass, 'mt-1')} />
              </label>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">
                Hours
                <input type="number" min={0.5} max={12} step={0.5} value={duration} onChange={(event) => setDuration(Number(event.target.value))} className={cn(inputClass, 'mt-1')} />
              </label>
            </div>
            {formError && <p className="text-xs text-red-600">{formError}</p>}
            {formOk && <p className="text-xs text-emerald-600">{formOk}</p>}
            <Button type="submit" variant="primary" loading={submitting} disabled={!effectiveVehicleId || !effectiveCenterId} className="w-full">
              Book slot
            </Button>
          </form>
        </Card>
      </div>

      <Card className="mb-6">
        <CardHeader title="Centers" subtitle={`${centers.data?.total ?? 0} centers · status at ${clock.toLocaleString([], { weekday: 'short', hour: '2-digit', minute: '2-digit' })}`} />
        {!centers.data ? (
          <Spinner />
        ) : centers.data.centers.length === 0 ? (
          <EmptyState icon={<Building2 className="size-8" />} title="No service centers" description="Run scripts/bootstrap.py (Docker does this automatically)." />
        ) : (
          <div className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-5">
            {centers.data.centers.map((center) => {
              const ratio = occupancyRatio(center);
              const open = isOpenAt(center, clock);
              const counts = centerCounts.get(center.center_id);
              return (
                <div key={center.center_id} className="rounded-lg border border-slate-200 p-4 dark:border-slate-800">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium leading-tight">{center.location}</p>
                    <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase', open ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800')}>
                      {open ? 'Open' : 'Closed'}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-slate-500">{hoursLabel(center)}</p>
                  <div className="mt-3 flex items-baseline justify-between text-sm">
                    <span className="text-2xl font-semibold tabular-nums">{center.current_occupancy}</span>
                    <span className="text-xs text-slate-500">of {center.max_capacity} bays</span>
                  </div>
                  <ProgressBar value={ratio} color={occupancyColor(ratio)} className="mt-1" />
                  <p className="mt-2 text-xs text-slate-500">
                    {counts?.active ?? 0} in bay · {counts?.pending ?? 0} booked
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Service slots"
          subtitle={`${slots.data?.total ?? 0} slots`}
          action={
            <div className="flex gap-1">
              {SLOT_FILTERS.map((option) => (
                <button
                  key={option.label}
                  type="button"
                  onClick={() => setSlotFilter(option.id)}
                  className={cn('rounded-full px-2.5 py-0.5 text-xs', slotFilter === option.id ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300')}
                >
                  {option.label}
                </button>
              ))}
            </div>
          }
        />
        <div className="px-5 pt-3">
          <ErrorBanner message={actionError} />
        </div>
        {!slots.data ? (
          <Spinner />
        ) : slots.data.slots.length === 0 ? (
          <EmptyState title="No slots in this view" description="Faulty vehicles are booked automatically during simulation." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500 dark:bg-slate-800/50">
                <tr>
                  <th className="px-5 py-2.5 font-medium">Vehicle</th>
                  <th className="px-3 py-2.5 font-medium">Center</th>
                  <th className="px-3 py-2.5 font-medium">Scheduled</th>
                  <th className="px-3 py-2.5 font-medium">Duration</th>
                  <th className="px-3 py-2.5 font-medium">Reason</th>
                  <th className="px-3 py-2.5 font-medium">Status</th>
                  <th className="px-3 py-2.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {slots.data.slots.map((slot) => (
                  <tr key={slot.slot_id}>
                    <td className="px-5 py-2.5">
                      <Link to={`/fleet/${slot.vehicle_id}`} className="font-medium text-blue-600 hover:underline">
                        {slot.vehicle_id}
                      </Link>
                    </td>
                    <td className="px-3 py-2.5">{slot.center_name}</td>
                    <td className="px-3 py-2.5 tabular-nums">{formatDateTime(slot.scheduled_time)}</td>
                    <td className="px-3 py-2.5">{slot.duration_hours} h</td>
                    <td className="px-3 py-2.5 text-slate-600 dark:text-slate-300">{slot.reason ?? '—'}</td>
                    <td className="px-3 py-2.5"><SlotBadge status={slot.slot_status} /></td>
                    <td className="px-3 py-2.5">
                      <div className="flex justify-end gap-1.5">
                        {slot.slot_status === 'PENDING' && (
                          <Button size="sm" onClick={() => void updateSlot(slot.slot_id, 'ACTIVE')}>
                            Check in
                          </Button>
                        )}
                        {slot.slot_status === 'ACTIVE' && (
                          <Button size="sm" variant="primary" onClick={() => void updateSlot(slot.slot_id, 'COMPLETED')}>
                            Complete
                          </Button>
                        )}
                        {(slot.slot_status === 'PENDING' || slot.slot_status === 'ACTIVE') && (
                          <Button size="sm" variant="ghost" onClick={() => void updateSlot(slot.slot_id, 'CANCELLED')}>
                            Cancel
                          </Button>
                        )}
                      </div>
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
