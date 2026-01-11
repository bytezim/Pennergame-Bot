import { useEffect, useState, useCallback } from "react";
import "./App.css";
import { Box, Container, useToast } from "@chakra-ui/react";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";
import { TasksPage } from "./pages/TasksPage";
import { DebugPage } from "./pages/DebugPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Status, Penner, Log, PageType } from "./types";

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>("dashboard");
  const [status, setStatus] = useState<Status | null>(null);
  const [penner, setPenner] = useState<Penner | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  
  const toast = useToast();

  // Check authentication status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;

    let eventSource: EventSource | null = null;
    let pollingInterval: number | null = null;
    let reconnectTimeout: number | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10; // Increased from 3 to 10 for better resilience

    const connectSSE = () => {
      // Nach 10 fehlgeschlagenen Versuchen auf Polling umsteigen
      if (reconnectAttempts >= maxReconnectAttempts) {
        console.warn('⚠️ SSE failed after 10 attempts, using polling mode');
        if (!pollingInterval) {
          pollingInterval = setInterval(fetchData, 30000) as unknown as number;
          fetchData();
        }
        return;
      }

      try {
        console.log(`🔄 Connecting to SSE (attempt ${reconnectAttempts + 1})...`);
        eventSource = new EventSource('/api/events/stream');
        
        eventSource.onopen = () => {
          console.log('✅ SSE connected - real-time updates active');
          reconnectAttempts = 0; // Reset bei erfolgreicher Verbindung
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
        };

        eventSource.onmessage = (event) => {
          try {
            // Ignore keep-alive messages
            if (!event.data || event.data.trim() === '') return;
            
            const data = JSON.parse(event.data);
            handleSSEEvent(data);
          } catch (e) {
            console.error('SSE parse error:', e);
          }
        };

        eventSource.onerror = (err) => {
          console.error('SSE error:', err);
          eventSource?.close();
          eventSource = null;
          reconnectAttempts++;
          
          // Versuche Reconnect nach kurzer Pause (exponential backoff, max 30s)
          const delay = Math.min(2000 * reconnectAttempts, 30000);
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectTimeout = setTimeout(() => {
              connectSSE();
            }, delay) as unknown as number;
          } else {
            // Fallback auf Polling
            console.warn('SSE connection failed, switching to polling fallback');
            if (!pollingInterval) {
              pollingInterval = setInterval(fetchData, 30000) as unknown as number;
              fetchData();
            }
          }
        };
      } catch (e) {
        console.error('SSE setup failed:', e);
        reconnectAttempts = maxReconnectAttempts; // Direkt zu Polling
        pollingInterval = setInterval(fetchData, 30000) as unknown as number;
        fetchData();
      }
    };

    // Initiales Daten-Laden, dann SSE
    fetchData().then(() => {
      connectSSE();
    });

    return () => {
      eventSource?.close();
      if (pollingInterval) clearInterval(pollingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, [isAuthenticated]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      // OPTIMIERUNG: Nutze /api/dashboard statt 3 separate Requests!
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout
      
      const dashboardRes = await fetch("/api/dashboard", {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!dashboardRes.ok) {
        throw new Error(`Dashboard fetch failed: ${dashboardRes.status}`);
      }
      
      const dashboardData = await dashboardRes.json();

      setStatus({ 
        logged_in: dashboardData.logged_in || false, 
        bot_running: dashboardData.bot?.running || false,
        activities: dashboardData.activities || undefined
      });
      setPenner(dashboardData.penner || null);
      
      // Latest log aus Dashboard
      if (dashboardData.latest_log) {
        setLogs(prev => {
          const exists = prev.some(log => log.id === dashboardData.latest_log.id);
          if (!exists) {
            return [dashboardData.latest_log, ...prev].slice(0, 50);
          }
          return prev;
        });
      }

      // Hole vollständige Logs nur alle 30s
      const now = Date.now();
      const lastLogFetch = (window as any).__lastLogFetch || 0;
      if (now - lastLogFetch > 30000) {
        try {
          const logsRes = await fetch("/api/logs");
          if (logsRes.ok) {
            const logsData = await logsRes.json();
            setLogs(logsData.logs || []);
            (window as any).__lastLogFetch = now;
          }
        } catch (logsError) {
          console.warn('Failed to fetch logs:', logsError);
        }
      }

    } catch (error: any) {
      console.error("Failed to fetch data:", error);
      
      // Nur Toast wenn kein Timeout/Abort
      if (error.name !== 'AbortError') {
        toast({
          title: "Fehler beim Laden",
          description: "Daten konnten nicht geladen werden",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const handleSSEEvent = useCallback((event: any) => {
    const { type, data } = event;

    switch (type) {
      case 'status_changed':
        // Update nur Activities-Teil
        setStatus(prev => prev ? { ...prev, activities: data.activities } : null);
        break;
      
      case 'activity_started':
      case 'activity_completed':
        // Refresh Status nach Activity-Änderung
        fetchData();
        break;
      
      case 'penner_data_updated':
        // Vollständiger Penner-Update
        setPenner(data);
        break;
      
      case 'money_changed':
        // Update nur Geld-Wert
        setPenner(prev => prev ? { ...prev, money: data.money } : null);
        break;
      
      case 'promille_changed':
        // Update nur Promille-Wert
        setPenner(prev => prev ? { ...prev, promille: data.promille } : null);
        break;
      
      case 'bottle_price_changed':
        // Wird für Stats-Page genutzt (Charts)
        // Dashboard zeigt keinen Bottle-Price direkt
        break;
      
      case 'bot_state_changed':
        setStatus(prev => prev ? { ...prev, bot_running: data.is_running } : null);
        break;
      
      case 'log_added':
        // Füge Log hinzu (max 50 behalten)
        setLogs(prev => {
          const newLogs = [{
            id: `${data.timestamp}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: data.timestamp,
            message: data.message
          }, ...prev];
          return newLogs.slice(0, 50);
        });
        break;
    }
  }, [fetchData]);

  const checkAuthStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/status");
      
      // If status endpoint fails, don't immediately set isAuthenticated to false
      // Use dashboard data if already loaded
      if (!response.ok) {
        console.warn("Status endpoint failed:", response.status);
        // Don't change isAuthenticated state - keep current state
        // The dashboard data will be used to determine login status
        return;
      }
      
      const data = await response.json();
      
      // Set status with proper structure
      setStatus({ 
        logged_in: data.logged_in || false, 
        bot_running: false 
      });
      setPenner(data.penner || null);
      setIsAuthenticated(data.logged_in || false);
    } catch (error) {
      console.error("Failed to check auth status:", error);
      // Don't set isAuthenticated to false on network errors
      // Keep current state - user might still be logged in based on dashboard data
    }
  }, []);

  const handleLoginSuccess = useCallback((showToast: boolean = true) => {
    setIsAuthenticated(true);
    // Lade Daten sofort nach Login, aber nicht blockieren
    fetchData().catch(error => {
      console.warn('Initial data fetch failed after login:', error);
    });
    if (showToast) {
      toast({
        title: "Anmeldung erfolgreich",
        description: "Willkommen zurück!",
        status: "success",
        duration: 2000,
      });
    }
  }, [fetchData, toast]);

  const handleStartBot = useCallback(async () => {
    try {
      await fetch("/api/bot/start", { method: "POST" });
      toast({
        title: "Bot gestartet",
        status: "success",
        duration: 2000,
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Bot konnte nicht gestartet werden",
        status: "error",
        duration: 3000,
      });
    }
  }, [fetchData, toast]);

  const handleStopBot = useCallback(async () => {
    try {
      await fetch("/api/bot/stop", { method: "POST" });
      toast({
        title: "Bot gestoppt",
        status: "info",
        duration: 2000,
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Bot konnte nicht gestoppt werden",
        status: "error",
        duration: 3000,
      });
    }
  }, [fetchData, toast]);

  const handleRefresh = useCallback(async () => {
    try {
      // Rufe den force-refresh Endpoint auf
      await fetch("/api/status/refresh", { method: "POST" });
      // Dann hole die aktualisierten Daten
      await fetchData();
    } catch (error) {
      console.error("Failed to refresh:", error);
      throw error; // Propagiere den Fehler für Toast-Handling in TopBar
    }
  }, [fetchData]);

  const handleLogout = useCallback(async () => {
    try {
      // Call logout API endpoint
      await fetch("/api/logout", { method: "POST" });
      
      // Reset state
      setIsAuthenticated(false);
      setStatus(null);
      setPenner(null);
      setLogs([]);
      setCurrentPage("dashboard");
      
      toast({
        title: "Abgemeldet",
        description: "Du wurdest erfolgreich abgemeldet",
        status: "info",
        duration: 2000,
      });
    } catch (error) {
      console.error("Logout failed:", error);
      toast({
        title: "Fehler",
        description: "Abmeldung fehlgeschlagen",
        status: "error",
        duration: 3000,
      });
    }
  }, [toast]);

  // Show login page if not authenticated
  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const botRunning = status?.bot_running || false;

  // Render current page
  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return (
          <DashboardPage
            status={status}
            penner={penner}
            logs={logs}
            botRunning={botRunning}
            onStart={handleStartBot}
            onStop={handleStopBot}
            onRefresh={handleRefresh}
          />
        );
      case "settings":
        return <SettingsPage />;
      case "stats":
        return <StatsPage />;
      case "tasks":
        return <TasksPage onRefresh={handleRefresh} status={status} />;
      case "debug":
        return <DebugPage />;
      default:
        return <DashboardPage status={status} penner={penner} logs={logs} botRunning={botRunning} onStart={handleStartBot} onStop={handleStopBot} onRefresh={handleRefresh} />;
    }
  };

  return (
    <Box bg="gray.900" minH="100vh">
      <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <Box ml={{ base: 0, md: "250px" }} w={{ base: "100%", md: "calc(100vw - 250px)" }}>
        <TopBar 
          status={status} 
          botRunning={botRunning} 
          loading={loading} 
          username={penner?.username}
          onStartBot={handleStartBot}
          onStopBot={handleStopBot}
          onLogout={handleLogout}
          onRefresh={handleRefresh}
        />
        <Container 
          maxW="7xl" 
          pt={{ base: "140px", md: "90px" }} 
          pb={8}
          px={{ base: 4, md: 6 }}
        >
          {renderPage()}
        </Container>
      </Box>
    </Box>
  );
}

export default App;
