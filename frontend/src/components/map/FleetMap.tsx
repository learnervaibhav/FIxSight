import { useMemo } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip } from 'react-leaflet';
import { Link } from 'react-router-dom';
import type { ServiceCenter, VehicleOverview } from '../../types/api';
import { HEALTH_COLORS, HEALTH_LABELS, formatDateTime, formatNumber, hoursLabel, isOpenAt, occupancyColor, occupancyRatio } from '../../lib/utils';

const DELHI: [number, number] = [28.6, 77.2];

interface PlacedVehicle {
  vehicle: VehicleOverview;
  position: [number, number];
}

/** Several vehicles share an owner's coordinates; spread them on a small ring so all are clickable. */
function placeVehicles(vehicles: VehicleOverview[]): PlacedVehicle[] {
  const groups = new Map<string, VehicleOverview[]>();
  for (const vehicle of vehicles) {
    if (vehicle.latitude === null || vehicle.longitude === null) continue;
    const key = `${vehicle.latitude.toFixed(4)},${vehicle.longitude.toFixed(4)}`;
    groups.set(key, [...(groups.get(key) ?? []), vehicle]);
  }
  const placed: PlacedVehicle[] = [];
  for (const group of groups.values()) {
    group.forEach((vehicle, index) => {
      const angle = (index / group.length) * 2 * Math.PI + Math.PI / 4;
      const radius = 0.006; // ~600 m, keeps vehicles visually apart from the center at the same spot
      placed.push({
        vehicle,
        position: [vehicle.latitude! + radius * Math.sin(angle), vehicle.longitude! + radius * Math.cos(angle)],
      });
    });
  }
  return placed;
}

export function FleetMap({
  centers,
  vehicles,
  clock,
  height = 460,
  dark = false,
}: {
  centers: ServiceCenter[];
  vehicles: VehicleOverview[];
  clock: Date;
  height?: number;
  dark?: boolean;
}) {
  const placed = useMemo(() => placeVehicles(vehicles), [vehicles]);
  const centerById = useMemo(() => new Map(centers.map((center) => [center.center_id, center])), [centers]);

  return (
    <div className="relative overflow-hidden rounded-b-xl" style={{ height }}>
      <MapContainer center={DELHI} zoom={10} scrollWheelZoom className="size-full" attributionControl>
        <TileLayer
          key={dark ? 'dark' : 'light'}
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          className={dark ? 'map-tiles-dark' : undefined}
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />

        {placed.map(({ vehicle, position }) => {
          const slot = vehicle.open_slot;
          const center = slot ? centerById.get(slot.center_id) : undefined;
          if (!slot || !center) return null;
          return (
            <Polyline
              key={`route-${vehicle.vehicle_id}`}
              positions={[position, [center.latitude, center.longitude]]}
              pathOptions={{
                color: slot.slot_status === 'ACTIVE' ? '#7c3aed' : '#2563eb',
                weight: 2,
                dashArray: slot.slot_status === 'ACTIVE' ? undefined : '6 6',
                opacity: 0.8,
              }}
            />
          );
        })}

        {centers.map((center) => {
          const ratio = occupancyRatio(center);
          const open = isOpenAt(center, clock);
          return (
            <CircleMarker
              key={center.center_id}
              center={[center.latitude, center.longitude]}
              radius={10 + center.max_capacity}
              pathOptions={{ color: occupancyColor(ratio), fillColor: occupancyColor(ratio), fillOpacity: open ? 0.35 : 0.12, weight: 2.5, dashArray: open ? undefined : '4 4' }}
            >
              <Tooltip direction="top" offset={[0, -8]}>
                {center.location}: {center.current_occupancy}/{center.max_capacity}
              </Tooltip>
              <Popup>
                <div className="min-w-48 space-y-1 text-sm">
                  <p className="font-semibold">{center.center_name}</p>
                  <p>
                    Occupancy: <b>{center.current_occupancy}</b> / {center.max_capacity} bays
                  </p>
                  <p>
                    Hours: {hoursLabel(center)} · {open ? <span className="text-emerald-600">Open</span> : <span className="text-slate-500">Closed</span>}
                  </p>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        {placed.map(({ vehicle, position }) => (
          <CircleMarker
            key={vehicle.vehicle_id}
            center={position}
            radius={vehicle.health_status === 'critical' ? 8 : 6}
            pathOptions={{
              color: vehicle.service_status === 'in_service' ? '#7c3aed' : '#ffffff',
              weight: vehicle.service_status === 'none' ? 1.5 : 3,
              fillColor: HEALTH_COLORS[vehicle.health_status],
              fillOpacity: 1,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              {vehicle.vehicle_id} · {HEALTH_LABELS[vehicle.health_status]}
            </Tooltip>
            <Popup>
              <div className="min-w-52 space-y-1 text-sm">
                <p className="font-semibold">
                  <Link to={`/fleet/${vehicle.vehicle_id}`}>{vehicle.vehicle_id}</Link> · {vehicle.owner_name}
                </p>
                <p>{vehicle.location}</p>
                <p>
                  Health {formatNumber(vehicle.latest_reading?.health_score)} · RUL {formatNumber(vehicle.rul_hours)} h
                </p>
                {vehicle.latest_fault && vehicle.latest_fault.fault_label !== 'normal' && (
                  <p className="text-red-600">
                    {vehicle.latest_fault.fault_label} ({Math.round(vehicle.latest_fault.fault_probability * 100)}%)
                  </p>
                )}
                {vehicle.open_slot && (
                  <p>
                    {vehicle.open_slot.slot_status === 'ACTIVE' ? 'In service at ' : 'Booked at '}
                    {vehicle.open_slot.center_name} · {formatDateTime(vehicle.open_slot.scheduled_time)}
                  </p>
                )}
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      <div className="pointer-events-none absolute bottom-3 left-3 z-[500] rounded-lg border border-slate-200 bg-white/95 px-3 py-2 text-[11px] text-slate-600 shadow dark:border-slate-700 dark:bg-slate-900/95 dark:text-slate-300">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          {(['healthy', 'warning', 'critical'] as const).map((status) => (
            <span key={status} className="flex items-center gap-1">
              <span className="size-2.5 rounded-full" style={{ background: HEALTH_COLORS[status] }} /> {HEALTH_LABELS[status]}
            </span>
          ))}
          <span className="flex items-center gap-1">
            <span className="size-2.5 rounded-full border-2 border-violet-600" /> In service
          </span>
        </div>
        <div className="mt-1 flex items-center gap-3">
          <span>Centers (ring size = capacity):</span>
          {[0.2, 0.6, 0.9].map((ratio) => (
            <span key={ratio} className="flex items-center gap-1">
              <span className="size-2.5 rounded-full border-2" style={{ borderColor: occupancyColor(ratio) }} />
              {ratio < 0.5 ? '<50%' : ratio < 0.85 ? '50–85%' : 'full'}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
