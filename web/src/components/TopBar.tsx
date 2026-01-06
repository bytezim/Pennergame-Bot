import { 
  Box, 
  Flex, 
  HStack, 
  Badge, 
  Text, 
  Spinner, 
  Icon, 
  Button,
  useDisclosure,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Tooltip,
  IconButton,
  useToast
} from "@chakra-ui/react";
import { FiCheckCircle, FiXCircle, FiPlay, FiPause, FiLogOut, FiBook, FiPackage, FiRefreshCw } from "react-icons/fi";
import { GiSwordman } from "react-icons/gi";
import { Status } from "../types";
import { useState, useEffect } from "react";

interface TopBarProps {
  status: Status | null;
  botRunning: boolean;
  loading: boolean;
  username?: string;
  onStartBot?: () => void;
  onStopBot?: () => void;
  onLogout?: () => void;
  onRefresh?: () => void;
}

export const TopBar = ({ 
  status, 
  botRunning, 
  loading, 
  username,
  onStartBot,
  onStopBot,
  onLogout,
  onRefresh
}: TopBarProps) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Lokale Sekunden-Counter die runterzählen - initialisiere mit aktuellen Werten
  const [localSeconds, setLocalSeconds] = useState({
    skill: status?.activities?.skill_seconds_remaining || 0,
    fight: status?.activities?.fight_seconds_remaining || 0,
    bottles: status?.activities?.bottles_seconds_remaining || 0
  });

  // Aktualisiere lokale Counter wenn sich der Status ändert
  useEffect(() => {
    if (status?.activities) {
      setLocalSeconds({
        skill: status.activities.skill_seconds_remaining || 0,
        fight: status.activities.fight_seconds_remaining || 0,
        bottles: status.activities.bottles_seconds_remaining || 0
      });
    }
  }, [status?.activities?.skill_seconds_remaining, status?.activities?.fight_seconds_remaining, status?.activities?.bottles_seconds_remaining]);

  // Countdown-Timer der jede Sekunde runterzählt
  useEffect(() => {
    const interval = setInterval(() => {
      setLocalSeconds(prev => ({
        skill: prev.skill > 0 ? prev.skill - 1 : 0,
        fight: prev.fight > 0 ? prev.fight - 1 : 0,
        bottles: prev.bottles > 0 ? prev.bottles - 1 : 0
      }));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Formatiere Zeit
  const formatTime = (seconds: number): string => {
    if (seconds <= 0) return "";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleLogout = () => {
    onClose();
    if (onLogout) onLogout();
  };

  const handleBotToggle = () => {
    if (botRunning && onStopBot) {
      onStopBot();
    } else if (!botRunning && onStartBot) {
      onStartBot();
    }
  };

  const handleRefresh = async () => {
    if (!onRefresh) return;
    
    setIsRefreshing(true);
    try {
      await onRefresh();
      toast({
        title: "Aktualisiert",
        description: "Status wurde erfolgreich aktualisiert",
        status: "success",
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Status konnte nicht aktualisiert werden",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <Box className="topbar">
      <Flex h="100%" px={6} align="center" justify="space-between">
        <HStack spacing={4}>
          <Text fontSize="lg" fontWeight="bold" color="white">
            PennerBot Dashboard
          </Text>
          {loading && <Spinner size="sm" color="teal.300" className="spinner" />}
        </HStack>

        <HStack spacing={4}>
          {/* Activity Status Badges */}
          {localSeconds.skill > 0 && (
            <Tooltip label={`Weiterbildung läuft noch ${formatTime(localSeconds.skill)}`} placement="bottom" hasArrow>
              <Badge 
                colorScheme="purple" 
                fontSize="sm" 
                px={3} 
                py={1} 
                borderRadius="full"
                display="flex"
                alignItems="center"
                gap={2}
                className="badge-pulse"
              >
                <Icon as={FiBook} boxSize={3} />
                <Text fontFamily="mono" fontWeight="bold">{formatTime(localSeconds.skill)}</Text>
              </Badge>
            </Tooltip>
          )}

          {localSeconds.fight > 0 && (
            <Tooltip label={`Kampf läuft noch ${formatTime(localSeconds.fight)}`} placement="bottom" hasArrow>
              <Badge 
                colorScheme="red" 
                fontSize="sm" 
                px={3} 
                py={1} 
                borderRadius="full"
                display="flex"
                alignItems="center"
                gap={2}
                className="badge-pulse"
              >
                <Icon as={GiSwordman} boxSize={4} />
                <Text fontFamily="mono" fontWeight="bold">{formatTime(localSeconds.fight)}</Text>
              </Badge>
            </Tooltip>
          )}

          {localSeconds.bottles > 0 && (
            <Tooltip label={`Pfandflaschen sammeln läuft noch ${formatTime(localSeconds.bottles)}`} placement="bottom" hasArrow>
              <Badge 
                colorScheme="green" 
                fontSize="sm" 
                px={3} 
                py={1} 
                borderRadius="full"
                display="flex"
                alignItems="center"
                gap={2}
                className="badge-pulse"
              >
                <Icon as={FiPackage} boxSize={3} />
                <Text fontFamily="mono" fontWeight="bold">{formatTime(localSeconds.bottles)}</Text>
              </Badge>
            </Tooltip>
          )}

          {/* Refresh Button */}
          <Tooltip label="Status aktualisieren" placement="bottom" hasArrow>
            <IconButton
              aria-label="Status aktualisieren"
              icon={<Icon as={FiRefreshCw} />}
              size="sm"
              colorScheme="blue"
              variant="ghost"
              onClick={handleRefresh}
              isLoading={isRefreshing}
              _hover={{ 
                bg: "blue.500",
                transform: "rotate(180deg)"
              }}
              transition="all 0.3s"
            />
          </Tooltip>

          {/* Bot Control Button */}
          <Tooltip 
            label={botRunning ? "Bot stoppen" : "Bot starten"} 
            placement="bottom"
            hasArrow
          >
            <Button
              size="sm"
              colorScheme={botRunning ? "red" : "green"}
              onClick={handleBotToggle}
              leftIcon={<Icon as={botRunning ? FiPause : FiPlay} />}
              className={botRunning ? "badge-pulse btn-glow" : "btn-glow"}
              _hover={{ transform: "translateY(-2px)" }}
              transition="all 0.3s"
            >
              {botRunning ? "Bot stoppen" : "Bot starten"}
            </Button>
          </Tooltip>

          {/* Login Status */}
          <HStack spacing={2}>
            <Icon
              as={status?.logged_in ? FiCheckCircle : FiXCircle}
              color={status?.logged_in ? "green.400" : "red.400"}
              boxSize={5}
            />
            <Text fontSize="sm" fontWeight="medium" color="white">
              {status?.logged_in ? "Eingeloggt" : "Nicht eingeloggt"}
            </Text>
          </HStack>

          {/* Username with Logout */}
          {username && (
            <Tooltip label="Klicken zum Ausloggen" placement="bottom" hasArrow>
              <Badge 
                colorScheme="teal" 
                fontSize="sm" 
                px={3} 
                py={1} 
                borderRadius="full"
                cursor="pointer"
                onClick={onOpen}
                _hover={{ 
                  transform: "translateY(-2px)",
                  boxShadow: "0 4px 12px rgba(56, 178, 172, 0.4)"
                }}
                transition="all 0.3s"
                display="flex"
                alignItems="center"
                gap={2}
              >
                <Text>{username}</Text>
                <Icon as={FiLogOut} boxSize={3} />
              </Badge>
            </Tooltip>
          )}
        </HStack>
      </Flex>

      {/* Logout Confirmation Modal */}
      <Modal isOpen={isOpen} onClose={onClose} isCentered>
        <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(10px)" />
        <ModalContent bg="gray.800" borderColor="gray.700" borderWidth="1px">
          <ModalHeader color="white">Ausloggen bestätigen</ModalHeader>
          <ModalBody>
            <Text color="gray.300">
              Bist du sicher, dass du dich ausloggen möchtest?
            </Text>
          </ModalBody>
          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose} color="white">
              Abbrechen
            </Button>
            <Button colorScheme="red" onClick={handleLogout} leftIcon={<Icon as={FiLogOut} />}>
              Ausloggen
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};
