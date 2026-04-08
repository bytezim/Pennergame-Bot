import { VStack, SimpleGrid, Button, Icon, HStack, Flex, Text, Code, Progress, Box, Badge, SimpleGrid as Grid, Spinner } from "@chakra-ui/react";
import { FiPlay, FiPause, FiRefreshCw, FiUser, FiDollarSign, FiTrendingUp, FiShield, FiAward, FiActivity, FiPackage, FiClock, FiCalendar } from "react-icons/fi";
import { DashboardCard } from "../components/DashboardCard";
import { StatCard } from "../components/StatCard";
import { Status, Penner, Log, UpcomingActivity } from "../types";
import { useState, useEffect } from "react";
import { getApiUrl } from "../utils/api";

interface DashboardPageProps {
  status: Status | null;
  penner: Penner | null;
  logs: Log[];
  botRunning: boolean;
  onStart: () => void;
  onStop: () => void;
  onRefresh: () => void;
}

// Hilfsfunktion zum Formatieren von Sekunden in Minuten:Sekunden
const formatTime = (seconds: number | null): string => {
  if (seconds === null || seconds <= 0) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const DashboardPage = ({
  status,
  penner,
  logs,
  botRunning,
  onStart,
  onStop,
  onRefresh,
}: DashboardPageProps) => {
  const activities = status?.activities;
  const [upcomingActivities, setUpcomingActivities] = useState<UpcomingActivity[]>([]);
  const [upcomingLoading, setUpcomingLoading] = useState(false);

  // Lokale Timer-States für Countdown
  const [bottlesTimer, setBottlesTimer] = useState<number | null>(null);
  const [skillTimer, setSkillTimer] = useState<number | null>(null);
  const [fightTimer, setFightTimer] = useState<number | null>(null);

  // Synchronisiere lokale Timer mit Server-Daten
  useEffect(() => {
    if (activities?.bottles_running && activities.bottles_seconds_remaining !== null) {
      setBottlesTimer(activities.bottles_seconds_remaining);
    } else if (!activities?.bottles_running) {
      setBottlesTimer(null);
    }
  }, [activities?.bottles_running, activities?.bottles_seconds_remaining]);

  useEffect(() => {
    if (activities?.skill_running && activities.skill_seconds_remaining !== null) {
      setSkillTimer(activities.skill_seconds_remaining);
    } else if (!activities?.skill_running) {
      setSkillTimer(null);
    }
  }, [activities?.skill_running, activities?.skill_seconds_remaining]);

  useEffect(() => {
    if (activities?.fight_running && activities.fight_seconds_remaining !== null) {
      setFightTimer(activities.fight_seconds_remaining);
    } else if (!activities?.fight_running) {
      setFightTimer(null);
    }
  }, [activities?.fight_running, activities?.fight_seconds_remaining]);

  // Countdown-Timer (tickt jede Sekunde runter)
  useEffect(() => {
    const interval = setInterval(() => {
      setBottlesTimer(prev => (prev !== null && prev > 0 ? prev - 1 : null));
      setSkillTimer(prev => (prev !== null && prev > 0 ? prev - 1 : null));
      setFightTimer(prev => (prev !== null && prev > 0 ? prev - 1 : null));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const fetchUpcomingActivities = async () => {
    setUpcomingLoading(true);
    try {
      const response = await fetch(getApiUrl("/activities/upcoming"));
      if (response.ok) {
        const data = await response.json();
        setUpcomingActivities(data.upcoming || []);
      }
    } catch (error) {
      console.error("Failed to fetch upcoming activities:", error);
    } finally {
      setUpcomingLoading(false);
    }
  };

  useEffect(() => {
    if (status?.logged_in) {
      fetchUpcomingActivities();
      const interval = setInterval(fetchUpcomingActivities, 30000);
      return () => clearInterval(interval);
    }
  }, [status?.logged_in]);

  return (
    <VStack align="stretch" spacing={6} className="fade-in">
      {/* Bot Control Card */}
      <DashboardCard
        title="Bot Steuerung"
        icon={botRunning ? FiPause : FiPlay}
        action={
          <Button
            leftIcon={<Icon as={FiRefreshCw} />}
            onClick={onRefresh}
            size="sm"
            variant="ghost"
            colorScheme="teal"
            _hover={{ bg: "whiteAlpha.200" }}
          >
            Aktualisieren
          </Button>
        }
      >
        <VStack spacing={4} align="stretch">
          <HStack spacing={4}>
            <Button
              colorScheme="green"
              size="lg"
              onClick={onStart}
              isDisabled={botRunning}
              leftIcon={<Icon as={FiPlay} />}
              flex={1}
              className={!botRunning ? "btn-glow" : ""}
              _hover={{ transform: "translateY(-2px)" }}
            >
              Bot starten
            </Button>
            <Button
              colorScheme="red"
              size="lg"
              onClick={onStop}
              isDisabled={!botRunning}
              leftIcon={<Icon as={FiPause} />}
              flex={1}
              _hover={{ transform: "translateY(-2px)" }}
            >
              Bot stoppen
            </Button>
          </HStack>

          {/* Aktivitäts-Status */}
          {activities && (
            <Box bg="whiteAlpha.50" p={3} borderRadius="md" mt={2}>
              <Text fontSize="sm" fontWeight="bold" color="gray.300" mb={2}>
                Laufende Aktivitäten
              </Text>
              <VStack spacing={2} align="stretch">
                {activities.bottles_running && bottlesTimer !== null && bottlesTimer > 0 && (
                  <HStack justify="space-between" p={2} bg="teal.900" borderRadius="md">
                    <HStack>
                      <Icon as={FiClock} color="teal.300" />
                      <Text fontSize="sm" color="teal.100">🍾 Pfandflaschen sammeln</Text>
                    </HStack>
                    <Badge colorScheme="teal" fontSize="xs">
                      {formatTime(bottlesTimer)}
                    </Badge>
                  </HStack>
                )}
                {activities.skill_running && skillTimer !== null && skillTimer > 0 && (
                  <HStack justify="space-between" p={2} bg="purple.900" borderRadius="md">
                    <HStack>
                      <Icon as={FiClock} color="purple.300" />
                      <Text fontSize="sm" color="purple.100">🎓 Weiterbildung</Text>
                    </HStack>
                    <Badge colorScheme="purple" fontSize="xs">
                      {formatTime(skillTimer)}
                    </Badge>
                  </HStack>
                )}
                {activities.fight_running && fightTimer !== null && fightTimer > 0 && (
                  <HStack justify="space-between" p={2} bg="red.900" borderRadius="md">
                    <HStack>
                      <Icon as={FiClock} color="red.300" />
                      <Text fontSize="sm" color="red.100">⚔️ Kampf</Text>
                    </HStack>
                    <Badge colorScheme="red" fontSize="xs">
                      {formatTime(fightTimer)}
                    </Badge>
                  </HStack>
                )}
                {(!activities.bottles_running || bottlesTimer === null || bottlesTimer <= 0) && 
                 (!activities.skill_running || skillTimer === null || skillTimer <= 0) && 
                 (!activities.fight_running || fightTimer === null || fightTimer <= 0) && (
                  <Text fontSize="sm" color="gray.500" textAlign="center" py={1}>
                    Keine aktiven Aktivitäten
                  </Text>
                )}
              </VStack>
            </Box>
          )}
        </VStack>
      </DashboardCard>

      {/* Anstehende Aktivitäten */}
      <DashboardCard title="Anstehende Aktivitäten" icon={FiCalendar}>
        {upcomingLoading ? (
          <HStack justify="center" py={4}>
            <Spinner size="sm" color="teal.400" />
            <Text color="gray.400" fontSize="sm">Lade...</Text>
          </HStack>
        ) : upcomingActivities.length === 0 ? (
          <Text color="gray.500" textAlign="center" py={4}>
            Keine anstehenden Aktivitäten
          </Text>
        ) : (
          <VStack spacing={3} align="stretch">
            {upcomingActivities.map((activity, index) => (
              <HStack 
                key={index}
                p={3} 
                bg={activity.status === "running" ? "teal.900" : activity.status === "scheduled" ? "orange.900" : "gray.700"}
                borderRadius="md"
                borderLeft="4px solid"
                borderLeftColor={
                  activity.status === "running" ? "teal.400" : 
                  activity.status === "scheduled" ? "orange.400" : "gray.500"
                }
              >
                <VStack align="start" spacing={1} flex={1}>
                  <HStack>
                    <Badge 
                      colorScheme={
                        activity.status === "running" ? "teal" : 
                        activity.status === "scheduled" ? "orange" : "gray"
                      }
                      fontSize="xs"
                    >
                      {activity.status === "running" ? "⏱️ Läuft" : 
                       activity.status === "scheduled" ? "📅 Geplant" : "✅ Bereit"}
                    </Badge>
                    <Text color="white" fontWeight="semibold" fontSize="sm">
                      {activity.name}
                    </Text>
                  </HStack>
                  {activity.remaining_seconds && (
                    <Text color="gray.400" fontSize="xs">
                      Noch: {formatTime(activity.remaining_seconds)}
                    </Text>
                  )}
                  {activity.delay_minutes && activity.status !== "running" && (
                    <Text color="gray.400" fontSize="xs">
                      Start in: {activity.delay_minutes} Min.
                    </Text>
                  )}
                </VStack>
                {activity.status === "running" && activity.remaining_seconds && (
                  <Badge colorScheme="teal" fontSize="sm">
                    {formatTime(activity.remaining_seconds)}
                  </Badge>
                )}
              </HStack>
            ))}
          </VStack>
        )}
      </DashboardCard>

      {/* Stats Overview */}
      <VStack align="stretch" spacing={4}>
        <Text fontSize="lg" fontWeight="bold" color="white" className="slide-in">
          Spieler-Übersicht
        </Text>
        <SimpleGrid columns={[1, 2, 3]} spacing={6}>
          <StatCard label="Spielername" value={penner?.username} icon={FiUser} />
          <StatCard
            label="Stadt"
            value={penner?.city || "Hamburg"}
            icon={FiUser}
          />
          <StatCard
            label="Rang"
            value={penner?.rank}
            icon={FiAward}
            trend={penner?.rank_trend}
          />
          <StatCard
            label="Punkte"
            value={penner?.points?.toLocaleString()}
            icon={FiTrendingUp}
            trend={penner?.points_trend}
          />
          <StatCard
            label="Geld"
            value={penner?.money}
            icon={FiDollarSign}
            trend={penner?.money_trend}
          />
          <StatCard label="Promille" value={penner?.promille} icon={FiActivity} />
        </SimpleGrid>

        <SimpleGrid columns={[1, 2, 3]} spacing={6}>
          <StatCard label="Angriff" value={penner?.att} icon={FiShield} />
          <StatCard label="Verteidigung" value={penner?.deff} icon={FiShield} />
          <StatCard label="Sauberkeit" value={penner?.cleanliness} icon={FiActivity} />
        </SimpleGrid>
      </VStack>

      {/* Container Status */}
      <DashboardCard title="Container Status" icon={FiPackage}>
        <VStack align="stretch" spacing={3}>
          <Flex justify="space-between" align="center">
            <Text color="gray.300" fontWeight="medium">
              Füllstand
            </Text>
            <Text
              fontWeight="bold"
              className="gradient-text"
              fontSize="lg"
              bgGradient="linear(to-r, teal.400, blue.400)"
              bgClip="text"
            >
              {penner?.container_filled_percent || 0}%
            </Text>
          </Flex>
          <Progress
            value={penner?.container_filled_percent || 0}
            colorScheme="teal"
            size="lg"
            borderRadius="md"
            className="progress-glow"
            bg="gray.700"
          />
          <SimpleGrid columns={3} spacing={4} mt={2}>
            <Box className="fade-in" style={{ animationDelay: "0.1s" }}>
              <Text fontSize="sm" color="gray.400" mb={1}>
                Spender insg.
              </Text>
              <Text fontSize="xl" fontWeight="bold" color="teal.300" isTruncated>
                {penner?.container_donors || 0}
              </Text>
            </Box>
            <Box className="fade-in" style={{ animationDelay: "0.2s" }}>
              <Text fontSize="sm" color="gray.400" mb={1}>
                Spenden heute
              </Text>
              <Text fontSize="xl" fontWeight="bold" color="teal.300" isTruncated>
                {penner?.container_donations_today || 0}
              </Text>
            </Box>
            <Box className="fade-in" style={{ animationDelay: "0.3s" }}>
              <Text fontSize="sm" color="gray.400" mb={1}>
                Gesamt Spenden
              </Text>
              <Text fontSize="xl" fontWeight="bold" color="teal.300" isTruncated>
                {penner?.container_total_donations || 0}
              </Text>
            </Box>
          </SimpleGrid>
        </VStack>
      </DashboardCard>

      {/* Activity Log */}
      <DashboardCard title="Letzte Aktivitäten" icon={FiActivity}>
        <VStack align="stretch" spacing={2} maxH="300px" overflowY="auto" className="custom-scrollbar">
          {logs.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={4}>
              Keine Aktivitäten vorhanden
            </Text>
          ) : (
            logs.slice(0, 50).map((l, index) => (
              <Flex
                key={l.id}
                gap={3}
                p={3}
                bg="gray.900"
                borderRadius="md"
                align="center"
                className="fade-in activity-log-item"
                style={{ animationDelay: `${index * 0.05}s` }}
                transition="all 0.2s ease"
                borderLeft="3px solid transparent"
                _hover={{
                  bg: "gray.800",
                  transform: "translateX(4px)",
                  boxShadow: "0 2px 8px rgba(56, 178, 172, 0.2)",
                  borderLeftColor: "teal.400",
                }}
              >
                <Code colorScheme="teal" fontSize="xs" fontWeight="bold" bg="teal.900" color="teal.200">
                  {new Date(l.timestamp).toLocaleTimeString()}
                </Code>
                <Text fontSize="sm" color="gray.300" noOfLines={2} wordBreak="break-word">
                  {l.message}
                </Text>
              </Flex>
            ))
          )}
        </VStack>
      </DashboardCard>
    </VStack>
  );
};
