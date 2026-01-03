/**
 * API client utilities with error handling and retries.
 */

// API Base URL: Verwende Umgebungsvariable oder bestimme automatisch
// Im Development: /api (Vite Proxy)
// Im Production: volle URL zum Backend
const getApiBaseUrl = (): string => {
  // 1. Umgebungsvariable (für Docker)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }
  
  // 2. Development (Vite Proxy)
  if (import.meta.env.DEV) {
    return '/api';
  }
  
  // 3. Production: Nutze gleichen Host wie Frontend
  // Funktioniert wenn Backend auf Port 8000 läuft
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8000/api`;
};

const API_BASE_URL = getApiBaseUrl();

/**
 * Get the full API URL for a given endpoint.
 * Verwendung: const url = getApiUrl('/actions/bottles/status');
 */
export const getApiUrl = (endpoint: string): string => {
  // Stelle sicher, dass endpoint mit / beginnt
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanEndpoint}`;
};

export interface ApiError {
  message: string;
  status?: number;
  details?: any;
}

export class NetworkError extends Error {
  constructor(message: string, public status?: number, public details?: any) {
    super(message);
    this.name = 'NetworkError';
  }
}

/**
 * Fetch with timeout.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = 10000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
}

/**
 * Parse API response with error handling.
 */
async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      throw new NetworkError(
        `HTTP ${response.status}: ${response.statusText}`,
        response.status
      );
    }

    throw new NetworkError(
      errorData.error || errorData.message || 'Request failed',
      response.status,
      errorData.details
    );
  }

  try {
    return await response.json();
  } catch (error) {
    throw new NetworkError('Failed to parse response');
  }
}

/**
 * GET request.
 */
export async function apiGet<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetchWithTimeout(url, {
    ...options,
    method: 'GET',
  });
  return parseResponse<T>(response);
}

/**
 * POST request.
 */
export async function apiPost<T = any>(
  endpoint: string,
  data?: any,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetchWithTimeout(url, {
    ...options,
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: data ? JSON.stringify(data) : undefined,
  });
  return parseResponse<T>(response);
}

/**
 * DELETE request.
 */
export async function apiDelete<T = any>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetchWithTimeout(url, {
    ...options,
    method: 'DELETE',
  });
  return parseResponse<T>(response);
}

/**
 * PUT request.
 */
export async function apiPut<T = any>(
  endpoint: string,
  data?: any,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetchWithTimeout(url, {
    ...options,
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: data ? JSON.stringify(data) : undefined,
  });
  return parseResponse<T>(response);
}

/**
 * Retry failed requests with exponential backoff.
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        const delay = baseDelay * Math.pow(2, attempt);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError!;
}
