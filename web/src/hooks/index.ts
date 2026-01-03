/**
 * Custom React hooks for PennerBot.
 * 
 * Provides reusable hooks for common patterns.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { useToast } from '@chakra-ui/react';

/**
 * Hook for API calls with loading and error states.
 */
export function useApi<T = any>() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);

  const execute = useCallback(async (
    url: string,
    options?: RequestInit
  ): Promise<T | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(url, options);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { loading, error, data, execute };
}

/**
 * Hook for debounced values.
 */
export function useDebounce<T>(value: T, delay: number = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Hook for interval-based polling.
 */
export function usePolling(
  callback: () => void | Promise<void>,
  interval: number,
  enabled: boolean = true
) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const tick = () => savedCallback.current();
    const id = setInterval(tick, interval);

    return () => clearInterval(id);
  }, [interval, enabled]);
}

/**
 * Hook for SSE (Server-Sent Events) connection.
 */
export function useSSE(
  url: string,
  onMessage: (data: any) => void,
  enabled: boolean = true
) {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;

  useEffect(() => {
    if (!enabled) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: number;

    const connect = () => {
      if (reconnectAttempts.current >= maxReconnectAttempts) {
        setError('Max reconnection attempts reached');
        return;
      }

      try {
        eventSource = new EventSource(url);

        eventSource.onopen = () => {
          setConnected(true);
          setError(null);
          reconnectAttempts.current = 0;
        };

        eventSource.onmessage = (event) => {
          try {
            if (!event.data || event.data.trim() === '') return;
            const data = JSON.parse(event.data);
            onMessage(data);
          } catch (e) {
            console.error('SSE parse error:', e);
          }
        };

        eventSource.onerror = () => {
          setConnected(false);
          eventSource?.close();
          reconnectAttempts.current++;

          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = 2000 * reconnectAttempts.current;
            reconnectTimeout = window.setTimeout(connect, delay);
          } else {
            setError('Connection failed');
          }
        };
      } catch (e) {
        setError('Failed to establish SSE connection');
      }
    };

    connect();

    return () => {
      eventSource?.close();
      clearTimeout(reconnectTimeout);
    };
  }, [url, enabled, onMessage]);

  return { connected, error };
}

/**
 * Hook for local storage with JSON serialization.
 */
export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  const [storedValue, setStoredValue] = useState<T>(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error loading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  const setValue = useCallback((value: T | ((prev: T) => T)) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
}

/**
 * Hook for toast notifications with common patterns.
 */
export function useNotifications() {
  const toast = useToast();

  const showSuccess = useCallback((message: string, title: string = 'Success') => {
    toast({
      title,
      description: message,
      status: 'success',
      duration: 2000,
      isClosable: true,
    });
  }, [toast]);

  const showError = useCallback((message: string, title: string = 'Error') => {
    toast({
      title,
      description: message,
      status: 'error',
      duration: 5000,
      isClosable: true,
    });
  }, [toast]);

  const showInfo = useCallback((message: string, title: string = 'Info') => {
    toast({
      title,
      description: message,
      status: 'info',
      duration: 3000,
      isClosable: true,
    });
  }, [toast]);

  const showWarning = useCallback((message: string, title: string = 'Warning') => {
    toast({
      title,
      description: message,
      status: 'warning',
      duration: 4000,
      isClosable: true,
    });
  }, [toast]);

  return { showSuccess, showError, showInfo, showWarning };
}
