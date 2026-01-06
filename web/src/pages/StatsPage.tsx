import { 
  VStack, 
  Text, 
  Heading, 
  Box, 
  Stat, 
  StatLabel, 
  StatNumber, 
  StatHelpText,
  HStack,
  useToast,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  Progress
} from "@chakra-ui/react";
import { DashboardCard } from "../components/DashboardCard";
import { FiBarChart2, FiTrendingUp, FiTrendingDown, FiZap } from "react-icons/fi";
import { useState, useEffect } from "react";
import { getApiUrl } from "../utils/api";
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
  BarChart,
  Bar,
  Cell
} from "recharts";

interface BottlePriceData {
  timestamp: string;
  price_cents: number;
}

interface BottlePriceHistory {
  prices: BottlePriceData[];
  count: number;
  current_price: number | null;
}

interface MoneyHistoryData {
  timestamp: string;
  amount: number;
}

interface MoneyHistory {
  history: MoneyHistoryData[];
  count: number;
  current_amount: number | null;
}

interface PerformanceEndpoint {
  requests: number;
  avg_time: number;
  min_time: number;
  max_time: number;
}

interface CacheStats {
  hits: number;
  misses: number;
  hit_rate: number;
}

interface PerformanceStats {
  cache: CacheStats;
  [endpoint: string]: PerformanceEndpoint | CacheStats;
}

export const StatsPage = () => {
  const [priceHistory, setPriceHistory] = useState<BottlePriceHistory | null>(null);
  const [moneyHistory, setMoneyHistory] = useState<MoneyHistory | null>(null);
  const [performanceStats, setPerformanceStats] = useState<PerformanceStats | null>(null);
  const [isLoadingPrices, setIsLoadingPrices] = useState(false);
  const [isLoadingMoney, setIsLoadingMoney] = useState(false);
  const [isLoadingPerformance, setIsLoadingPerformance] = useState(false);
  const toast = useToast();

  useEffect(() => {
    fetchPriceHistory();
    fetchMoneyHistory();
    fetchPerformanceStats();
  }, []);

  const fetchPriceHistory = async () => {
    setIsLoadingPrices(true);
    try {
      const response = await fetch(getApiUrl("/bottle-prices"));
      if (response.ok) {
        const data = await response.json();
        setPriceHistory(data);
      } else {
        toast({
          title: "Fehler",
          description: "Preis-Historie konnte nicht geladen werden",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Verbindung zum Server fehlgeschlagen",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoadingPrices(false);
    }
  };

  const fetchMoneyHistory = async () => {
    setIsLoadingMoney(true);
    try {
      const response = await fetch(getApiUrl("/money-history"));
      if (response.ok) {
        const data = await response.json();
        setMoneyHistory(data);
      } else {
        toast({
          title: "Fehler",
          description: "Geld-Historie konnte nicht geladen werden",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Verbindung zum Server fehlgeschlagen",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoadingMoney(false);
    }
  };

  const fetchPerformanceStats = async () => {
    setIsLoadingPerformance(true);
    try {
      const response = await fetch(getApiUrl("/performance-stats"));
      if (response.ok) {
        const data = await response.json();
        setPerformanceStats(data);
      } else {
        toast({
          title: "Fehler",
          description: "Performance-Statistiken konnten nicht geladen werden",
          status: "error",
          duration: 5000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Verbindung zum Server fehlgeschlagen",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setIsLoadingPerformance(false);
    }
  };

  const formatChartData = () => {
    if (!priceHistory || !priceHistory.prices.length) return [];
    
    return priceHistory.prices.map((item, index) => ({
      index: index + 1,
      price: item.price_cents,
      time: new Date(item.timestamp).toLocaleTimeString("de-DE", {
        hour: "2-digit",
        minute: "2-digit"
      }),
      date: new Date(item.timestamp).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "2-digit"
      })
    }));
  };

  const calculateStats = () => {
    if (!priceHistory || !priceHistory.prices.length) {
      return { min: 0, max: 0, avg: 0, trend: 0 };
    }

    const prices = priceHistory.prices.map(p => p.price_cents);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
    
    // Trend: Vergleiche ersten und letzten Wert
    const first = prices[0];
    const last = prices[prices.length - 1];
    const trend = last - first;

    return { min, max, avg, trend };
  };

  const formatMoneyChartData = () => {
    if (!moneyHistory || !moneyHistory.history.length) return [];
    
    return moneyHistory.history.map((item, index) => ({
      index: index + 1,
      amount: item.amount,
      time: new Date(item.timestamp).toLocaleTimeString("de-DE", {
        hour: "2-digit",
        minute: "2-digit"
      }),
      date: new Date(item.timestamp).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "2-digit"
      })
    }));
  };

  const calculateMoneyStats = () => {
    if (!moneyHistory || !moneyHistory.history.length) {
      return { min: 0, max: 0, avg: 0, trend: 0 };
    }

    const amounts = moneyHistory.history.map(h => h.amount);
    const min = Math.min(...amounts);
    const max = Math.max(...amounts);
    const avg = amounts.reduce((a, b) => a + b, 0) / amounts.length;
    
    // Trend: Vergleiche ersten und letzten Wert
    const first = amounts[0];
    const last = amounts[amounts.length - 1];
    const trend = last - first;

    return { min, max, avg, trend };
  };

  const stats = calculateStats();
  const chartData = formatChartData();
  const moneyStats = calculateMoneyStats();
  const moneyChartData = formatMoneyChartData();

  return (
    <VStack align="stretch" spacing={6} className="fade-in">
      <Heading size="lg" color="white">
        Statistiken
      </Heading>

      {/* Performance-Statistiken */}
      <DashboardCard title="Performance & Cache" icon={FiZap}>
        <VStack align="stretch" spacing={6}>
          {performanceStats ? (
            <>
              {/* Cache Stats */}
              <Box>
                <Heading size="md" mb={4} color="white">📊 Cache-Statistik</Heading>
                <HStack spacing={4} justify="space-around" flexWrap="wrap">
                  <Stat textAlign="center" minW="150px">
                    <StatLabel>Cache Hits</StatLabel>
                    <StatNumber color="green.400">{performanceStats.cache.hits}</StatNumber>
                    <StatHelpText>Erfolgreiche Zugriffe</StatHelpText>
                  </Stat>

                  <Stat textAlign="center" minW="150px">
                    <StatLabel>Cache Misses</StatLabel>
                    <StatNumber color="orange.400">{performanceStats.cache.misses}</StatNumber>
                    <StatHelpText>Verpasste Zugriffe</StatHelpText>
                  </Stat>

                  <Stat textAlign="center" minW="150px">
                    <StatLabel>Hit Rate</StatLabel>
                    <StatNumber color="purple.400">{performanceStats.cache.hit_rate}%</StatNumber>
                    <StatHelpText>Trefferquote</StatHelpText>
                  </Stat>
                </HStack>

                {/* Cache Hit Rate Progress Bar */}
                <Box mt={6}>
                  <Text fontSize="sm" color="gray.400" mb={2}>Cache-Effizienz</Text>
                  <Progress 
                    value={performanceStats.cache.hit_rate} 
                    colorScheme={performanceStats.cache.hit_rate > 80 ? "green" : performanceStats.cache.hit_rate > 50 ? "yellow" : "red"}
                    size="lg"
                    borderRadius="md"
                  />
                </Box>
              </Box>

              {/* API Endpoint Stats */}
              <Box>
                <Heading size="md" mb={4} color="white">⚡ API-Endpunkt Performance</Heading>
                
                {Object.entries(performanceStats).filter(([key]) => key !== 'cache').length > 0 ? (
                  <>
                    {/* Performance Chart */}
                    <Box bg="gray.800" p={6} borderRadius="lg" borderWidth="1px" borderColor="gray.700" mb={4}>
                      <Text fontSize="sm" color="gray.400" mb={4}>
                        Durchschnittliche Antwortzeit (ms)
                      </Text>
                      <ResponsiveContainer width="100%" height={300}>
                        <BarChart 
                          data={Object.entries(performanceStats)
                            .filter(([key]) => key !== 'cache')
                            .map(([endpoint, stats]) => ({
                              endpoint: endpoint.replace('GET ', '').replace('POST ', '').replace('PUT ', ''),
                              avg_time: (stats as PerformanceEndpoint).avg_time * 1000,
                              requests: (stats as PerformanceEndpoint).requests
                            }))
                            .sort((a, b) => b.avg_time - a.avg_time)
                          }
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                          <XAxis 
                            dataKey="endpoint" 
                            stroke="#9CA3AF"
                            tick={{ fill: "#9CA3AF", fontSize: 10 }}
                            angle={-45}
                            textAnchor="end"
                            height={100}
                          />
                          <YAxis 
                            stroke="#9CA3AF"
                            tick={{ fill: "#9CA3AF" }}
                            label={{ value: "Zeit (ms)", angle: -90, position: "insideLeft", fill: "#9CA3AF" }}
                          />
                          <Tooltip 
                            contentStyle={{ 
                              backgroundColor: "#1F2937", 
                              border: "1px solid #374151",
                              borderRadius: "8px",
                              color: "#F3F4F6"
                            }}
                            formatter={(value: any, name: string) => [
                              name === 'avg_time' ? `${(value as number).toFixed(2)} ms` : value,
                              name === 'avg_time' ? 'Ø Antwortzeit' : 'Anfragen'
                            ]}
                            labelFormatter={(label: string) => `Endpoint: ${label}`}
                          />
                          <Bar dataKey="avg_time" radius={[8, 8, 0, 0]}>
                            {Object.entries(performanceStats)
                              .filter(([key]) => key !== 'cache')
                              .map(([_, stats], index) => {
                                const avgTime = (stats as PerformanceEndpoint).avg_time * 1000;
                                const color = avgTime < 100 ? "#48BB78" : avgTime < 500 ? "#ECC94B" : "#F56565";
                                return <Cell key={`cell-${index}`} fill={color} />;
                              })
                            }
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </Box>

                    {/* Endpoint Details Table */}
                    <Box overflowX="auto">
                      <Table variant="simple" size="sm">
                        <Thead>
                          <Tr>
                            <Th color="gray.400">Endpunkt</Th>
                            <Th color="gray.400" isNumeric>Anfragen</Th>
                            <Th color="gray.400" isNumeric>Ø Zeit</Th>
                            <Th color="gray.400" isNumeric>Min</Th>
                            <Th color="gray.400" isNumeric>Max</Th>
                            <Th color="gray.400">Status</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {Object.entries(performanceStats)
                            .filter(([key]) => key !== 'cache')
                            .sort(([, a], [, b]) => (b as PerformanceEndpoint).requests - (a as PerformanceEndpoint).requests)
                            .map(([endpoint, stats]) => {
                              const s = stats as PerformanceEndpoint;
                              const avgMs = s.avg_time * 1000;
                              const status = avgMs < 100 ? { label: "Schnell", color: "green" } : 
                                            avgMs < 500 ? { label: "Okay", color: "yellow" } : 
                                            { label: "Langsam", color: "red" };
                              
                              return (
                                <Tr key={endpoint}>
                                  <Td color="white" fontSize="xs">{endpoint}</Td>
                                  <Td color="blue.300" isNumeric fontWeight="bold">{s.requests}</Td>
                                  <Td color="purple.300" isNumeric>{avgMs.toFixed(2)} ms</Td>
                                  <Td color="green.300" isNumeric>{(s.min_time * 1000).toFixed(2)} ms</Td>
                                  <Td color="orange.300" isNumeric>{(s.max_time * 1000).toFixed(2)} ms</Td>
                                  <Td>
                                    <Badge colorScheme={status.color} fontSize="xs">
                                      {status.label}
                                    </Badge>
                                  </Td>
                                </Tr>
                              );
                            })
                          }
                        </Tbody>
                      </Table>
                    </Box>
                  </>
                ) : (
                  <Box py={8}>
                    <Text color="gray.400" textAlign="center">
                      Noch keine API-Anfragen verarbeitet
                    </Text>
                  </Box>
                )}
              </Box>

              {/* Info */}
              <Box p={4} bg="purple.900" borderRadius="md" borderWidth="1px" borderColor="purple.700">
                <Text fontSize="sm" color="purple.200">
                  ⚡ Performance-Metriken werden bei jeder API-Anfrage automatisch erfasst. 
                  Der Cache reduziert unnötige API-Aufrufe und verbessert die Antwortzeiten.
                </Text>
              </Box>
            </>
          ) : (
            <Box py={8}>
              <Text color="gray.400" textAlign="center">
                {isLoadingPerformance 
                  ? "Lade Performance-Daten..." 
                  : "Keine Performance-Daten verfügbar"}
              </Text>
            </Box>
          )}
        </VStack>
      </DashboardCard>

      {/* Geld-Historie */}
      <DashboardCard title="Geld-Historie" icon={FiBarChart2}>
        <VStack align="stretch" spacing={6}>
          {/* Stats Cards */}
          <HStack spacing={4} justify="space-around" flexWrap="wrap">
            <Stat textAlign="center" minW="150px">
              <StatLabel>Aktuelles Geld</StatLabel>
              <StatNumber color="green.400">
                €{(moneyHistory?.current_amount || 0).toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
              </StatNumber>
              <StatHelpText>
                {moneyStats.trend > 0 && (
                  <HStack justify="center" color="green.400">
                    <FiTrendingUp />
                    <Text>+€{moneyStats.trend.toLocaleString('de-DE', {minimumFractionDigits: 2})}</Text>
                  </HStack>
                )}
                {moneyStats.trend < 0 && (
                  <HStack justify="center" color="red.400">
                    <FiTrendingDown />
                    <Text>-€{Math.abs(moneyStats.trend).toLocaleString('de-DE', {minimumFractionDigits: 2})}</Text>
                  </HStack>
                )}
                {moneyStats.trend === 0 && (
                  <Text color="gray.400">Stabil</Text>
                )}
              </StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Minimum</StatLabel>
              <StatNumber color="red.400">€{moneyStats.min.toLocaleString('de-DE', {minimumFractionDigits: 2})}</StatNumber>
              <StatHelpText>Tiefster Wert</StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Maximum</StatLabel>
              <StatNumber color="green.400">€{moneyStats.max.toLocaleString('de-DE', {minimumFractionDigits: 2})}</StatNumber>
              <StatHelpText>Höchster Wert</StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Durchschnitt</StatLabel>
              <StatNumber color="purple.400">€{moneyStats.avg.toLocaleString('de-DE', {minimumFractionDigits: 2})}</StatNumber>
              <StatHelpText>Mittelwert</StatHelpText>
            </Stat>
          </HStack>

          {/* Chart */}
          {moneyChartData.length > 0 ? (
            <Box bg="gray.800" p={6} borderRadius="lg" borderWidth="1px" borderColor="gray.700">
              <Text fontSize="sm" color="gray.400" mb={4}>
                Geldentwicklung (letzte {moneyHistory?.count} Änderungen)
              </Text>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={moneyChartData}>
                  <defs>
                    <linearGradient id="colorMoney" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#48BB78" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#48BB78" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="index" 
                    stroke="#9CA3AF"
                    tick={{ fill: "#9CA3AF" }}
                    label={{ value: "Messpunkt", position: "insideBottom", offset: -5, fill: "#9CA3AF" }}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    tick={{ fill: "#9CA3AF" }}
                    label={{ value: "Betrag (€)", angle: -90, position: "insideLeft", fill: "#9CA3AF" }}
                    tickFormatter={(value) => `€${value.toLocaleString('de-DE')}`}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "#1F2937", 
                      border: "1px solid #374151",
                      borderRadius: "8px",
                      color: "#F3F4F6"
                    }}
                    labelFormatter={(value: any) => `Messpunkt ${value}`}
                    formatter={(value: any, _name: string, props: any) => [
                      `€${(value as number).toLocaleString('de-DE', {minimumFractionDigits: 2})}`, 
                      `${props.payload.date} ${props.payload.time}`
                    ]}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="amount" 
                    stroke="#48BB78" 
                    strokeWidth={3}
                    fillOpacity={1} 
                    fill="url(#colorMoney)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Box py={8}>
              <Text color="gray.400" textAlign="center">
                {isLoadingMoney 
                  ? "Lade Daten..." 
                  : "Noch keine Geld-Daten vorhanden. Die Daten werden bei der nächsten Aktualisierung erfasst."}
              </Text>
            </Box>
          )}

          {/* Info */}
          <Box p={4} bg="green.900" borderRadius="md" borderWidth="1px" borderColor="green.700">
            <Text fontSize="sm" color="green.200">
              💰 Dein Geldbestand wird bei jeder Aktualisierung automatisch erfasst. 
              Die letzten 50 Änderungen werden gespeichert und hier als Graph dargestellt.
            </Text>
          </Box>
        </VStack>
      </DashboardCard>

      {/* Pfandflaschen-Preis Historie */}
      <DashboardCard title="Pfandflaschen-Preis Historie" icon={FiBarChart2}>
        <VStack align="stretch" spacing={6}>
          {/* Stats Cards */}
          <HStack spacing={4} justify="space-around" flexWrap="wrap">
            <Stat textAlign="center" minW="150px">
              <StatLabel>Aktueller Preis</StatLabel>
              <StatNumber color="blue.400">
                {priceHistory?.current_price || 0} ¢
              </StatNumber>
              <StatHelpText>
                {stats.trend > 0 && (
                  <HStack justify="center" color="green.400">
                    <FiTrendingUp />
                    <Text>+{stats.trend} ¢</Text>
                  </HStack>
                )}
                {stats.trend < 0 && (
                  <HStack justify="center" color="red.400">
                    <FiTrendingDown />
                    <Text>{stats.trend} ¢</Text>
                  </HStack>
                )}
                {stats.trend === 0 && (
                  <Text color="gray.400">Stabil</Text>
                )}
              </StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Minimum</StatLabel>
              <StatNumber color="red.400">{stats.min} ¢</StatNumber>
              <StatHelpText>Tiefster Wert</StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Maximum</StatLabel>
              <StatNumber color="green.400">{stats.max} ¢</StatNumber>
              <StatHelpText>Höchster Wert</StatHelpText>
            </Stat>

            <Stat textAlign="center" minW="150px">
              <StatLabel>Durchschnitt</StatLabel>
              <StatNumber color="purple.400">{stats.avg.toFixed(1)} ¢</StatNumber>
              <StatHelpText>Mittelwert</StatHelpText>
            </Stat>
          </HStack>

          {/* Chart */}
          {chartData.length > 0 ? (
            <Box bg="gray.800" p={6} borderRadius="lg" borderWidth="1px" borderColor="gray.700">
              <Text fontSize="sm" color="gray.400" mb={4}>
                Preisentwicklung (letzte {priceHistory?.count} Änderungen)
              </Text>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3182CE" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#3182CE" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="index" 
                    stroke="#9CA3AF"
                    tick={{ fill: "#9CA3AF" }}
                    label={{ value: "Messpunkt", position: "insideBottom", offset: -5, fill: "#9CA3AF" }}
                  />
                  <YAxis 
                    stroke="#9CA3AF"
                    tick={{ fill: "#9CA3AF" }}
                    label={{ value: "Preis (Cent)", angle: -90, position: "insideLeft", fill: "#9CA3AF" }}
                    domain={[stats.min - 2, stats.max + 2]}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "#1F2937", 
                      border: "1px solid #374151",
                      borderRadius: "8px",
                      color: "#F3F4F6"
                    }}
                    labelFormatter={(value: any) => `Messpunkt ${value}`}
                    formatter={(value: any, _name: string, props: any) => [
                      `${value} Cent`, 
                      `${props.payload.date} ${props.payload.time}`
                    ]}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="price" 
                    stroke="#3182CE" 
                    strokeWidth={3}
                    fillOpacity={1} 
                    fill="url(#colorPrice)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Box py={8}>
              <Text color="gray.400" textAlign="center">
                {isLoadingPrices 
                  ? "Lade Daten..." 
                  : "Noch keine Preis-Daten vorhanden. Die Daten werden bei der nächsten Aktualisierung erfasst."}
              </Text>
            </Box>
          )}

          {/* Info */}
          <Box p={4} bg="blue.900" borderRadius="md" borderWidth="1px" borderColor="blue.700">
            <Text fontSize="sm" color="blue.200">
              💡 Der Pfandflaschenpreis wird bei jeder Aktualisierung automatisch erfasst. 
              Die letzten 50 Preisänderungen werden gespeichert und hier als Graph dargestellt.
            </Text>
          </Box>
        </VStack>
      </DashboardCard>
    </VStack>
  );
};

