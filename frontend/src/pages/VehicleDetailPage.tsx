import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowLeft, Bot, CalendarPlus, Cpu, Gauge, HeartPulse, Timer } from 'lucide-react';
import { useLive } from '../context/live';
import { useApi } from '../hooks/useApi';
import { api, errorMessage } from '../lib/api';
import type { AgentRunResult } from '../types/api';
import { formatDateTime, formatNumber, parseDate, percent } from '../lib/utils';
import { Badge, Button, Card, CardHeader, EmptyState, ErrorBanner, PageHeader, Spinner, StatCard } from '../components/ui/primitives';
import { AlertStatusBadge, HealthBadge, SeverityBadge, SlotBadge } from '../components/ui/StatusBadges';

const CHARTS = [
  { key: 'coolant_temperature', label: 'Coolant temperature (°C)', color: '#dc2626', threshold: 110 },
  { key: 'oil_pressure', label: 'Oil pressure (psi)', color: '#2563eb', threshold: 25 },
  { key: 'battery_voltage', label: 'Battery voltage (V)', color: '#16a34a', threshold: 11.5 },
  { key: 'transmission_temperature', label: 'Transmission temp (°C)', color: '#d97706', threshold: 120 },
] as const;

const shortTime = (value: string) => parseDate(value)?.toLocaleString([], { day: '2-digit', hour: '2-digit', minute: '2-digit' }) ?? '';

export function VehicleDetailPage() {
  const { vehicleId = '' } = useParams();
  const { overview } = useLive();
  const vehicle = overview?.vehicles.find((item) => item.vehicle_id === vehicleId);

  const telemetry = useApi(() => api.vehicleTelemetry(vehicleId, 60), [vehicleId]);
  const predictions = useApi(() => api.vehiclePredictions(vehicleId, 60), [vehicleId]);
  const slots = useApi(() => api.vehicleSlots(vehicleId), [vehicleId]);
  const alerts = useApi(() => api.alerts({ vehicle_id: vehicleId, limit: 10 }), [vehicleId]);

  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<AgentRunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const series = useMemo(() => [...(telemetry.data?.readings ?? [])].reverse(), [telemetry.data]);
  const rulSeries = useMemo(
    () => [...(predictions.data?.rul ?? [])].reverse().map((point) => ({ ...point, label: shortTime(point.created_at) })),
    [predictions.data],
  );
  const faults = (predictions.data?.faults ?? []).filter((fault) => fault.fault_label !== 'normal').slice(0, 8);

  const runDiagnosis = async () => {
    const latest = telemetry.data?.readings[0];
    if (!latest) return;
    setRunning(true);
    setRunError(null);
    try {
      setRunResult(await api.runAgent(vehicleId, { telemetry_reading_id: latest.id, alert_mode: 'mock' }));
    } catch (error) {
      setRunError(errorMessage(error));
    } finally {
      setRunning(false);
    }
  };

  if (overview && !vehicle) {
    return <EmptyState title={`Vehicle ${vehicleId} not found`} description={<Link to="/fleet" className="text-blue-600">Back to fleet</Link>} />;
  }

  return (
    <>
      <Link to="/fleet" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800 dark:hover:text-white">
        <ArrowLeft className="size-4" /> Fleet
      </Link>
      <PageHeader
        title={vehicleId}
        description={vehicle ? `${vehicle.owner_name} · ${vehicle.location} · ${vehicle.engine_type.replace('_', ' ')} ${vehicle.manufacture_year} · ${vehicle.driving_profile} driving` : undefined}
        actions={
          <>
            {vehicle && <HealthBadge status={vehicle.health_status} />}
            <Link to={`/service?vehicle=${vehicleId}`}>
              <Button>
                <CalendarPlus className="size-4" /> Book service
              </Button>
            </Link>
            <Button variant="primary" onClick={() => void runDiagnosis()} loading={running} disabled={!telemetry.data?.readings.length}>
              <Bot className="size-4" /> Run AI diagnosis
            </Button>
          </>
        }
      />

      <ErrorBanner message={runError} />
      {runResult && (
        <Card className="mb-6 border-blue-200 dark:border-blue-900">
          <CardHeader
            title="AI diagnosis on latest reading"
            subtitle={`LLM: ${runResult.llm_status ?? '—'} · priority ${runResult.maintenance_priority ?? '—'} · window ${runResult.recommended_service_window_hours ?? '—'} h`}
            action={runResult.severity && <SeverityBadge severity={runResult.severity} />}
          />
          <div className="grid gap-4 p-5 md:grid-cols-2">
            <div>
              <p className="text-lg font-semibold">{runResult.fault_label === 'normal' ? 'No fault detected' : runResult.fault_label}</p>
              <p className="text-sm text-slate-500">
                Confidence {percent(runResult.fault_probability)} · RUL {formatNumber(runResult.rul_hours)} h
              </p>
              <p className="mt-3 whitespace-pre-line text-sm text-slate-700 dark:text-slate-300">{runResult.llm_explanation}</p>
              {runResult.service_booking_status && (
                <p className="mt-3 text-sm">
                  Booking: <b>{runResult.service_booking_status}</b>
                  {runResult.selected_service_center && ` · ${runResult.selected_service_center.center_name} · ${formatDateTime(runResult.scheduled_slot_time)}`}
                </p>
              )}
            </div>
            <ul className="space-y-2">
              {runResult.maintenance_action_items?.map((item) => (
                <li key={item.title} className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{item.title}</span>
                    <Badge tone={item.priority === 'P1' ? 'red' : item.priority === 'P2' ? 'amber' : 'neutral'}>{item.priority}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.owner} · within {item.due_in_hours} h — {item.notes}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Health score" value={formatNumber(vehicle?.latest_reading?.health_score, 1)} hint="0–100" icon={<HeartPulse className="size-5" />} tone="green" />
        <StatCard label="Remaining life" value={`${formatNumber(vehicle?.rul_hours)} h`} hint="XGBoost RUL forecast" icon={<Timer className="size-5" />} tone="blue" />
        <StatCard
          label="Latest prediction"
          value={<span className="text-base">{vehicle?.latest_fault ? (vehicle.latest_fault.fault_label === 'normal' ? 'Normal' : vehicle.latest_fault.fault_label) : '—'}</span>}
          hint={vehicle?.latest_fault ? `${percent(vehicle.latest_fault.fault_probability)} fault probability` : undefined}
          icon={<Cpu className="size-5" />}
          tone={vehicle?.health_status === 'critical' ? 'red' : vehicle?.health_status === 'warning' ? 'amber' : 'neutral'}
        />
        <StatCard
          label="Engine"
          value={`${formatNumber(vehicle?.latest_reading?.engine_rpm)} rpm`}
          hint={`${formatNumber(vehicle?.latest_reading?.vehicle_speed)} km/h · ${formatDateTime(vehicle?.latest_reading?.timestamp)}`}
          icon={<Gauge className="size-5" />}
        />
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {CHARTS.map((chart) => (
          <Card key={chart.key}>
            <CardHeader title={chart.label} subtitle={`Last ${series.length} readings · fault threshold ${chart.threshold}`} />
            <div className="h-52 p-3">
              {telemetry.loading && !series.length ? (
                <Spinner />
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                    <XAxis dataKey="timestamp" tickFormatter={shortTime} tick={{ fontSize: 10 }} minTickGap={40} stroke="#94a3b8" />
                    <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" domain={['auto', 'auto']} />
                    <Tooltip labelFormatter={(value) => formatDateTime(String(value))} formatter={(value) => formatNumber(Number(value), 2)} />
                    <Line type="monotone" dataKey={chart.key} stroke={chart.color} strokeWidth={2} dot={false} isAnimationActive={false} name={chart.label} />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </Card>
        ))}
      </div>

      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Fault history & AI explanations" subtitle="Latest non-normal predictions" />
          {faults.length === 0 ? (
            <EmptyState title="No faults predicted" description="This vehicle has only produced normal readings." />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {faults.map((fault) => (
                <li key={fault.id} className="px-5 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{fault.fault_label}</span>
                    <SeverityBadge severity={fault.severity} />
                    <span className="text-xs text-slate-500">
                      {percent(fault.fault_probability)} · {fault.maintenance_priority} · {formatDateTime(fault.created_at)}
                    </span>
                  </div>
                  {fault.llm_explanation && <p className="mt-1 whitespace-pre-line text-sm text-slate-600 dark:text-slate-300">{fault.llm_explanation}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <CardHeader title="RUL trend" subtitle="Remaining useful life (hours)" />
          <div className="h-60 p-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={rulSeries} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} minTickGap={40} stroke="#94a3b8" />
                <YAxis tick={{ fontSize: 10 }} stroke="#94a3b8" />
                <Tooltip formatter={(value) => `${formatNumber(Number(value))} h`} />
                <Line type="monotone" dataKey="rul_hours" stroke="#7c3aed" strokeWidth={2} dot={false} isAnimationActive={false} name="RUL" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Service history" />
          {!slots.data?.slots.length ? (
            <EmptyState title="No service bookings yet" />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {slots.data.slots.map((slot) => (
                <li key={slot.slot_id} className="flex items-center justify-between gap-3 px-5 py-3 text-sm">
                  <div>
                    <p className="font-medium">{slot.reason ?? 'Service'}</p>
                    <p className="text-xs text-slate-500">
                      {formatDateTime(slot.scheduled_time)} · {slot.duration_hours} h
                    </p>
                  </div>
                  <SlotBadge status={slot.slot_status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
        <Card>
          <CardHeader title="Recent notifications" />
          {!alerts.data?.alerts.length ? (
            <EmptyState title="No alerts sent" />
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {alerts.data.alerts.map((alert) => (
                <li key={alert.id} className="px-5 py-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-slate-500">
                      {alert.alert_type.replace('_', ' ')} · {formatDateTime(alert.created_at)}
                    </span>
                    <AlertStatusBadge status={alert.status} />
                  </div>
                  <p className="mt-1 line-clamp-2 whitespace-pre-line text-xs text-slate-600 dark:text-slate-300">{alert.alert_message}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </>
  );
}
