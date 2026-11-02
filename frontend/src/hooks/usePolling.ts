import { useEffect, useRef } from 'react';

/** Run `callback` now and every `intervalMs` (null pauses). Always calls the latest callback. */
export function usePolling(callback: () => void | Promise<void>, intervalMs: number | null, deps: unknown[] = []) {
  const saved = useRef(callback);

  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  useEffect(() => {
    if (intervalMs === null) return;
    let cancelled = false;
    const run = () => {
      if (!cancelled) void saved.current();
    };
    run();
    const id = window.setInterval(run, intervalMs);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, ...deps]);
}
