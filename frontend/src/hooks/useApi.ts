import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '../lib/api';
import { useLive } from '../context/live';

interface ApiState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

/**
 * Fetch data and re-fetch whenever live events arrive (refreshKey) or `deps` change.
 * Keeps showing the previous data while reloading to avoid flicker.
 */
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const { refreshKey } = useLive();
  const [state, setState] = useState<ApiState<T>>({ data: null, error: null, loading: true });
  const [nonce, setNonce] = useState(0);
  const loaderRef = useRef(loader);

  useEffect(() => {
    loaderRef.current = loader;
  });

  useEffect(() => {
    let cancelled = false;
    loaderRef.current().then(
      (data) => !cancelled && setState({ data, error: null, loading: false }),
      (error: unknown) => !cancelled && setState((prev) => ({ ...prev, error: errorMessage(error), loading: false })),
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey, nonce, ...deps]);

  const reload = useCallback(() => setNonce((value) => value + 1), []);
  return { ...state, reload };
}
