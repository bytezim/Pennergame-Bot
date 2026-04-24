import { useEffect, useState, useCallback } from "react";
import "./App.css";
import { Box, Container, Spinner, Text } from "@chakra-ui/react";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";
import { TasksPage } from "./pages/TasksPage";
import { DebugPage } from "./pages/DebugPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Status, Penner, Log, PageType } from "./types";
import { getApiUrl } from "./utils/api";

interface SSEEventData {
  type: string;
  data: Record<string, unknown>;
}

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>("dashboard");
  const [status, setStatus] = useState<Status | null>(null);
  const [penner, setPenner] = useState<Penner | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [backendReady, setBackendReady] = useState(false);
  const [appLoading, setAppLoading] = useState(true);

  useEffect(() => {
    const waitForBackend = async () => {
      const maxAttempts = 30;
      const baseDelay = 1000;

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          const response = await fetch(getApiUrl("/health"), {
            method: "GET",
            signal: AbortSignal.timeout(3000),
          });
          if (response.ok) {
            const data = await response.json();

            if (data.status === "initializing") {
              await new Promise((resolve) => setTimeout(resolve, 1000));
            } else if (data.status === "ready") {
              setBackendReady(true);
              setAppLoading(false);
              return;
            } else {
              setBackendReady(true);
              setAppLoading(false);
              return;
            }
          }
        } catch {
          // Backend not ready yet, continue waiting
        }

        const delay = baseDelay * Math.pow(2, Math.min(attempt, 4));
        await new Promise((resolve) => setTimeout(resolve, delay));
      }

      setBackendReady(true);
      setAppLoading(false);
    };

    waitForBackend();
  }, []);

  useEffect(() => {
    if (!backendReady) return;

    const checkAndRedirect = async () => {
      try {
        const response = await fetch(getApiUrl("/status"));
        if (response.ok) {
          const data = await response.json();
          setIsAuthenticated(data.logged_in || false);
          setStatus({
            logged_in: data.logged_in || false,
            bot_running: false,
          });
          setPenner(data.penner || null);

          if (data.logged_in) {
            setCurrentPage("dashboard");
          } else {
            setCurrentPage("login");
          }
        }
      } catch (error) {
        console.error("Failed to check auth status:", error);

        setIsAuthenticated(false);
        setCurrentPage("login");
      }
    };

    const timer = setTimeout(checkAndRedirect, 500);
    return () => clearTimeout(timer);
  }, [backendReady]);

  useEffect(() => {
    if (!isAuthenticated) return;

    let eventSource: EventSource | null = null;
    let pollingInterval: number | null = null;
    let reconnectTimeout: number | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;

    const connectSSE = () => {
      if (reconnectAttempts >= maxReconnectAttempts) {
        console.warn("⚠️ SSE failed after 10 attempts, using polling mode");
        if (!pollingInterval) {
          pollingInterval = setInterval(fetchData, 30000) as unknown as number;
          fetchData();
        }
        return;
      }

      try {
        console.log(
          `🔄 Connecting to SSE (attempt ${reconnectAttempts + 1})...`,
        );
        eventSource = new EventSource(getApiUrl("/events/stream"));

        eventSource.onopen = () => {
          console.log("✅ SSE connected - real-time updates active");
          reconnectAttempts = 0;
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
        };

        eventSource.onmessage = (event) => {
          try {
            if (!event.data || event.data.trim() === "") return;

            const data = JSON.parse(event.data);
            handleSSEEvent(data);
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        };

        eventSource.onerror = (err) => {
          console.error("SSE error:", err);
          eventSource?.close();
          eventSource = null;
          reconnectAttempts++;

          const delay = Math.min(2000 * reconnectAttempts, 30000);
          if (reconnectAttempts < maxReconnectAttempts) {
            reconnectTimeout = setTimeout(() => {
              connectSSE();
            }, delay) as unknown as number;
          } else {
            console.warn(
              "SSE connection failed, switching to polling fallback",
            );
            if (!pollingInterval) {
              pollingInterval = setInterval(
                fetchData,
                30000,
              ) as unknown as number;
              fetchData();
            }
          }
        };
      } catch (e) {
        console.error("SSE setup failed:", e);
        reconnectAttempts = maxReconnectAttempts;
        pollingInterval = setInterval(fetchData, 30000) as unknown as number;
        fetchData();
      }
    };

    fetchData().then(() => {
      connectSSE();
    });

    return () => {
      eventSource?.close();
      if (pollingInterval) clearInterval(pollingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const dashboardRes = await fetch(getApiUrl("/dashboard"), {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!dashboardRes.ok) {
        throw new Error(`Dashboard fetch failed: ${dashboardRes.status}`);
      }

      const dashboardData = await dashboardRes.json();

      setStatus({
        logged_in: dashboardData.logged_in || false,
        bot_running: dashboardData.bot?.running || false,
        activities: dashboardData.activities || undefined,
      });
      setPenner(dashboardData.penner || null);

      if (dashboardData.latest_log) {
        setLogs((prev) => {
          const exists = prev.some(
            (log) => log.id === dashboardData.latest_log.id,
          );
          if (!exists) {
            return [dashboardData.latest_log, ...prev].slice(0, 50);
          }
          return prev;
        });
      }

      const now = Date.now();
      const lastLogFetch =
        (window as unknown as { __lastLogFetch?: number }).__lastLogFetch || 0;
      if (now - lastLogFetch > 60000) {
        try {
          const logsRes = await fetch(getApiUrl("/logs"));
          if (logsRes.ok) {
            const logsData = await logsRes.json();
            setLogs(logsData.logs || []);
            (window as unknown as { __lastLogFetch?: number }).__lastLogFetch =
              now;
          }
        } catch (logsError) {
          console.warn("Failed to fetch logs:", logsError);
        }
      }
    } catch (error) {
      console.error("Failed to fetch data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSSEEvent = useCallback(
    (event: SSEEventData) => {
      const { type, data } = event;

      switch (type) {
        case "status_changed":
          setStatus((prev) =>
            prev
              ? {
                  ...prev,
                  activities: data.activities as Status["activities"],
                }
              : null,
          );
          break;

        case "activity_started":
        case "activity_completed":
          fetchData();
          break;

        case "penner_data_updated":
          setPenner(data as unknown as Penner);
          break;

        case "money_changed":
          setPenner((prev) =>
            prev ? { ...prev, money: String(data.money) } : null,
          );
          break;

        case "promille_changed":
          setPenner((prev) =>
            prev ? { ...prev, promille: Number(data.promille) } : null,
          );
          break;

        case "bottle_price_changed":
          break;

        case "bot_state_changed":
          setStatus((prev) =>
            prev ? { ...prev, bot_running: Boolean(data.is_running) } : null,
          );
          break;

        case "log_added":
          setLogs((prev) => {
            const newLogs = [
              {
                id: `${String(data.timestamp)}-${Math.random().toString(36).substr(2, 9)}`,
                timestamp: String(data.timestamp),
                message: String(data.message),
              },
              ...prev,
            ];
            return newLogs.slice(0, 50);
          });
          break;
      }
    },
    [fetchData],
  );

  const handleLoginSuccess = useCallback(
    (showToast: boolean = true) => {
      setIsAuthenticated(true);

      fetchData().catch((error) => {
        console.warn("Initial data fetch failed after login:", error);
      });
      if (showToast) {
        console.log("Login successful");
      }
    },
    [fetchData],
  );

  const handleStartBot = useCallback(async () => {
    try {
      await fetch(getApiUrl("/bot/start"), { method: "POST" });
      console.log("Bot started");
      fetchData();
    } catch (error) {
      console.error("Failed to start bot:", error);
    }
  }, [fetchData]);

  const handleStopBot = useCallback(async () => {
    try {
      await fetch(getApiUrl("/bot/stop"), { method: "POST" });
      console.log("Bot stopped");
      fetchData();
    } catch (error) {
      console.error("Failed to stop bot:", error);
    }
  }, [fetchData]);

  const handleRefresh = useCallback(async () => {
    try {
      await fetch(getApiUrl("/status/refresh"), { method: "POST" });

      await fetchData();
    } catch (error) {
      console.error("Failed to refresh:", error);
      throw error;
    }
  }, [fetchData]);

  const handleLogout = useCallback(async () => {
    try {
      await fetch(getApiUrl("/logout"), { method: "POST" });

      setIsAuthenticated(false);
      setStatus(null);
      setPenner(null);
      setLogs([]);
      setCurrentPage("dashboard");
      console.log("User logged out");
    } catch (error) {
      console.error("Logout failed:", error);
    }
  }, []);

  if (appLoading) {
    return (
      <Box
        minH="100vh"
        bg="gray.900"
        display="flex"
        alignItems="center"
        justifyContent="center"
      >
        <Spinner size="lg" color="teal.400" />
        <Text ml={2} color="gray.400">
          PennerBot wird geladen...
        </Text>
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  const botRunning = status?.bot_running || false;

  const renderPage = () => {
    switch (currentPage) {
      case "dashboard":
        return (
          <DashboardPage
            status={status}
            penner={penner}
            logs={logs}
            botRunning={botRunning}
            loading={loading}
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
    }
  };

  return (
    <Box bg="gray.900" minH="100vh">
      <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <Box
        ml={{ base: 0, md: "250px" }}
        w={{ base: "100%", md: "calc(100vw - 250px)" }}
      >
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
