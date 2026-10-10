// Derive API and WebSocket URLs dynamically from Vite environment variable
const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').trim().replace(/\/+$/, '');

// Clean REST API Base URL
export const API_BASE_URL = `${rawBaseUrl}/api/v1`;

// Clean WebSocket Base URL with automatic wss:// / ws:// upgrade
export const WS_BASE_URL = `${rawBaseUrl.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')}/ws/tasks`;

export class FridayApiClient {
  static getBaseUrl() {
    return rawBaseUrl;
  }

  static async checkHealth() {
    try {
      const res = await fetch(`${API_BASE_URL}/health`, { method: 'GET' });
      if (!res.ok) return { online: false };
      const data = await res.json();
      return { online: true, ...data };
    } catch (err) {
      return { online: false, error: err.message };
    }
  }

  static async submitCommand(commandText, sessionId = 'web_session') {
    try {
      const res = await fetch(`${API_BASE_URL}/commands`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'friday-dev-secret-key'
        },
        body: JSON.stringify({
          command: commandText,
          session_id: sessionId,
          client_platform: 'web'
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn('[FridayApi] Backend unavailable or failed, using local simulation fallback', err);
      return null;
    }
  }

  static async fetchTasks() {
    try {
      const res = await fetch(`${API_BASE_URL}/tasks`, {
        headers: { 'X-API-Key': 'friday-dev-secret-key' }
      });
      if (!res.ok) return [];
      return await res.json();
    } catch {
      return [];
    }
  }

  static async createTask(type, title, payload = {}) {
    try {
      const res = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'friday-dev-secret-key'
        },
        body: JSON.stringify({ type, title, payload })
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  static connectTaskWebSocket(onTaskUpdate, onInitialSnapshot, onConnectionChange) {
    let ws = null;
    let reconnectTimeout = null;
    let reconnectAttempts = 0;
    let isDisposed = false;

    const connect = () => {
      if (isDisposed) return;
      try {
        ws = new WebSocket(WS_BASE_URL);

        ws.onopen = () => {
          reconnectAttempts = 0;
          if (onConnectionChange) onConnectionChange(true);
        };

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.event_type === 'initial_snapshot' && onInitialSnapshot) {
              onInitialSnapshot(msg.tasks);
            } else if (msg.event_type === 'task_update' && onTaskUpdate) {
              onTaskUpdate(msg.task);
            }
          } catch (e) {
            console.error('[FridayWS] JSON parse error', e);
          }
        };

        ws.onclose = () => {
          if (onConnectionChange) onConnectionChange(false);
          if (!isDisposed) {
            // Reconnect with backoff capped at 10 seconds
            reconnectAttempts += 1;
            const delay = Math.min(10000, 2000 * Math.pow(1.3, reconnectAttempts));
            reconnectTimeout = setTimeout(connect, delay);
          }
        };

        ws.onerror = () => {
          // Gracefully close on error without uncaught exceptions
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.close();
          }
        };
      } catch (err) {
        console.warn('[FridayWS] WebSocket initialization warning:', err);
        if (!isDisposed) {
          reconnectTimeout = setTimeout(connect, 4000);
        }
      }
    };

    connect();

    return {
      close: () => {
        isDisposed = true;
        if (reconnectTimeout) clearTimeout(reconnectTimeout);
        if (ws) {
          try {
            ws.close();
          } catch {}
        }
      }
    };
  }
}
