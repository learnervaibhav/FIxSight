import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, errorMessage } from '../lib/api';
import { usePolling } from '../hooks/usePolling';
import type { FleetOverview, LiveEvent, SimulationMode, SimulationStatus } from '../types/api';
import { LiveContext, type LiveContextValue, type StartOptions, type Toast } from './live';

const TOAST_TYPES = new Set(['notification', 'fault_detected', 'service_booked', 'service_completed', 'service_unavailable']);
const MAX_EVENTS = 200;
const MAX_TOASTS = 5;

export function LiveProvider({ children }: { children: ReactNode }) {
  const [backendOnline, setBackendOnline] = useState(true);
  const [status, setStatus] = useState<SimulationStatus | null>(null);
  const [overview, setOverview] = useState<FleetOverview | null>(null);
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const lastEventId = useRef<number | null>(null);
  const eventsInFlight = useRef(false);
  const toastTimers = useRef(new Map<number, number>());

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
    const timer = toastTimers.current.get(id);
    if (timer) window.clearTimeout(timer);
    toastTimers.current.delete(id);
  }, []);

  const pushToasts = useCallback(
    (incoming: LiveEvent[]) => {
      const fresh = incoming.filter((event) => TOAST_TYPES.has(event.type)).slice(-MAX_TOASTS);
      if (!fresh.length) return;
      setToasts((prev) => {
        const known = new Set(prev.map((toast) => toast.id));
        return [...prev, ...fresh.filter((event) => !known.has(event.id)).map((event) => ({ id: event.id, event }))].slice(-MAX_TOASTS);
      });
      for (const event of fresh) {
        const ttl = event.type === 'notification' ? 9000 : 6000;
        toastTimers.current.set(event.id, window.setTimeout(() => dismissToast(event.id), ttl));
      }
    },
    [dismissToast],
  );

  const pollStatus = useCallback(async () => {
    try {
      setStatus(await api.simulationStatus());
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  const pollEvents = useCallback(async () => {
    // StrictMode and overlapping intervals can fire concurrently; one request at a time.
    if (eventsInFlight.current) return;
    eventsInFlight.current = true;
    try {
      const isFirstLoad = lastEventId.current === null;
      const result = await api.events(lastEventId.current ?? 0);
      // Event ids restart when the backend restarts.
      if (lastEventId.current !== null && result.last_id < lastEventId.current) {
        lastEventId.current = 0;
        return;
      }
      lastEventId.current = result.last_id;
      if (!result.events.length) return;
      setEvents((prev) => {
        const known = new Set(prev.map((event) => event.id));
        return [...prev, ...result.events.filter((event) => !known.has(event.id))].slice(-MAX_EVENTS);
      });
      if (!isFirstLoad) {
        pushToasts(result.events);
        setRefreshKey((key) => key + 1);
      }
    } catch {
      /* status poll reports connectivity */
    } finally {
      eventsInFlight.current = false;
    }
  }, [pushToasts]);

  const pollOverview = useCallback(async () => {
    try {
      setOverview(await api.fleetOverview());
    } catch {
      /* keep last good overview */
    }
  }, []);

  const running = status?.running ?? false;
  usePolling(pollStatus, 2000);
  usePolling(pollEvents, 1500);
  usePolling(pollOverview, running ? 3000 : 15000, [refreshKey]);

  const runAction = useCallback(
    async (action: () => Promise<SimulationStatus>) => {
      setBusy(true);
      setActionError(null);
      try {
        setStatus(await action());
        await pollEvents();
        setRefreshKey((key) => key + 1);
      } catch (error) {
        setActionError(errorMessage(error));
      } finally {
        setBusy(false);
      }
    },
    [pollEvents],
  );

  const value = useMemo<LiveContextValue>(
    () => ({
      backendOnline,
      status,
      overview,
      events,
      toasts,
      refreshKey,
      busy,
      actionError,
      start: (mode: SimulationMode, options: StartOptions = {}) =>
        runAction(() =>
          api.startSimulation({
            mode,
            tick_seconds: options.tick_seconds ?? status?.tick_seconds ?? 3,
            vehicles_per_tick: options.vehicles_per_tick ?? status?.vehicles_per_tick ?? 5,
            use_llm: options.use_llm ?? true,
          }),
        ),
      stop: () => runAction(api.stopSimulation),
      reset: () => runAction(api.resetSimulation),
      step: () => runAction(api.stepSimulation),
      refresh: () => setRefreshKey((key) => key + 1),
      dismissToast,
    }),
    [backendOnline, status, overview, events, toasts, refreshKey, busy, actionError, runAction, dismissToast],
  );

  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}
