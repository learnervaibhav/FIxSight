import { createContext, useContext } from 'react';
import type { FleetOverview, LiveEvent, SimulationMode, SimulationStatus } from '../types/api';

export interface Toast {
  id: number;
  event: LiveEvent;
}

export interface StartOptions {
  tick_seconds?: number;
  vehicles_per_tick?: number;
  use_llm?: boolean;
}

export interface LiveContextValue {
  backendOnline: boolean;
  status: SimulationStatus | null;
  overview: FleetOverview | null;
  events: LiveEvent[];
  toasts: Toast[];
  /** Increments whenever new events arrive; pages re-fetch on change. */
  refreshKey: number;
  busy: boolean;
  actionError: string | null;
  start: (mode: SimulationMode, options?: StartOptions) => Promise<void>;
  stop: () => Promise<void>;
  reset: () => Promise<void>;
  step: () => Promise<void>;
  refresh: () => void;
  dismissToast: (id: number) => void;
}

export const LiveContext = createContext<LiveContextValue | undefined>(undefined);

export function useLive(): LiveContextValue {
  const context = useContext(LiveContext);
  if (!context) throw new Error('useLive must be used inside <LiveProvider>');
  return context;
}
