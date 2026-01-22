import { useEffect, useRef, useState, useCallback } from "react";

interface UsePollingOptions {
  interval?: number;
  enabled?: boolean;
}

export function usePolling<T>(
  fetchFn: () => Promise<T>,
  options: UsePollingOptions = {}
) {
  const { interval = 5000, enabled = true } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Use ref to store the latest fetchFn to avoid dependency issues
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  const fetchData = useCallback(async () => {
    try {
      const result = await fetchFnRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const refresh = useCallback(() => {
    setIsLoading(true);
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (!enabled) return;

    fetchData();

    const intervalId = window.setInterval(fetchData, interval);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [fetchData, interval, enabled]);

  return { data, error, isLoading, refresh };
}
