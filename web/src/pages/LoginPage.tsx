import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Container,
  FormControl,
  FormLabel,
  Heading,
  Input,
  VStack,
  Text,
  Icon,
  useToast,
  InputGroup,
  InputLeftElement,
  HStack,
  Spinner,
  Collapse,
  useDisclosure,
  Select,
} from "@chakra-ui/react";
import { getApiUrl } from "../utils/api";
import { FiLogIn, FiUser, FiLock, FiServer, FiAlertCircle, FiSettings, FiChevronDown, FiChevronUp, FiGlobe } from "react-icons/fi";

interface LoginPageProps {
  onLoginSuccess: (showToast?: boolean) => void;
}

export const LoginPage = ({ onLoginSuccess }: LoginPageProps) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [userAgent, setUserAgent] = useState("");
  const [city, setCity] = useState("hamburg");
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const { isOpen, onToggle } = useDisclosure();
  const toast = useToast();

  // City configuration
  const cities = [
    { key: "hamburg", name: "Hamburg" },
    { key: "vatikan", name: "Vatikan" },
    { key: "sylt", name: "Sylt" },
    { key: "malle", name: "Malle" },
    { key: "reloaded", name: "Hamburg Reloaded" },
    { key: "koeln", name: "Köln" },
    { key: "berlin", name: "Berlin" },
    { key: "muenchen", name: "München" },
  ];

  // Detect and save browser user agent and city on first visit
  useEffect(() => {
    const initializeSettings = async () => {
      try {
        // First, check if settings are already saved in backend
        const response = await fetch(getApiUrl("/settings"));
        if (response.ok) {
          const data = await response.json();
          
          // Load user agent
          if (data.settings && data.settings.user_agent) {
            setUserAgent(data.settings.user_agent);
            console.log("Loaded existing user agent:", data.settings.user_agent);
          } else {
            // No user agent saved yet, use browser's user agent
            const browserUA = navigator.userAgent;
            setUserAgent(browserUA);
            console.log("Detected browser user agent:", browserUA);
          }
          
          // Load city
          if (data.settings && data.settings.city) {
            setCity(data.settings.city);
            console.log("Loaded existing city:", data.settings.city);
          } else {
            // No city saved yet, use default (hamburg)
            console.log("Using default city: hamburg");
          }
        }
      } catch (error) {
        console.error("Failed to initialize settings:", error);
        // Fallback to defaults
        setUserAgent(navigator.userAgent);
        setCity("hamburg");
      }
    };
    
    initializeSettings();
  }, []);

  // Attempt auto-login on mount if credentials are saved
  useEffect(() => {
    const attemptAutoLogin = async () => {
      try {
        const response = await fetch(getApiUrl("/login/auto"), {
          method: "POST",
        });
        
        const data = await response.json();
        
        if (data.success && data.logged_in) {
          console.log("Auto-login successful");
          // Auto-login: suppress toast here
          onLoginSuccess(false);
        } else {
          console.log("Auto-login not possible or failed:", data.message);
        }
      } catch (error) {
        console.error("Auto-login request failed:", error);
      }
    };
    
    // Small delay to ensure backend is ready
    const timer = setTimeout(attemptAutoLogin, 500);
    return () => clearTimeout(timer);
  }, [onLoginSuccess]);

  // Check backend status on mount and periodically
  useEffect(() => {
    checkBackendStatus();
    const interval = setInterval(checkBackendStatus, 5000); // Check every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const checkBackendStatus = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000); // 3 second timeout
      
      const response = await fetch(getApiUrl("/status"), {
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      if (response.ok) {
        setBackendStatus("online");
      } else {
        setBackendStatus("offline");
      }
    } catch (error) {
      setBackendStatus("offline");
    }
  };

  const handleCityChange = async (newCity: string) => {
    setCity(newCity);
    try {
      // Save city immediately when changed
      await fetch(getApiUrl("/settings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          city: newCity
        }),
      });
      console.log("City saved:", newCity);
    } catch (error) {
      console.error("Failed to save city:", error);
    }
  };

  const handleLogin = async () => {
    if (!username || !password) {
      toast({
        title: "Fehler",
        description: "Bitte Benutzername und Passwort eingeben",
        status: "error",
        duration: 3000,
      });
      return;
    }

    setLoading(true);
    try {
      // First, set the user agent and city before login
      if (userAgent || city) {
        await fetch(getApiUrl("/settings"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_agent: userAgent,
            city: city
          }),
        });
      }

      // Then proceed with login
      const response = await fetch(getApiUrl("/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (data.success) {
        // Manual login: let App.tsx show the "Anmeldung erfolgreich" toast
        onLoginSuccess();
      } else {
        toast({
          title: "Login fehlgeschlagen",
          description: data.message || "Ungültige Zugangsdaten",
          status: "error",
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Verbindung zum Server fehlgeschlagen",
        status: "error",
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleLogin();
    }
  };

  return (
    <Box
      minH="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bg="gray.900"
      position="relative"
      overflow="hidden"
    >
      {/* Background gradient effect */}
      <Box
        position="absolute"
        top="0"
        left="0"
        right="0"
        bottom="0"
        bgGradient="radial(circle at 50% 50%, rgba(56, 178, 172, 0.1) 0%, transparent 50%)"
        pointerEvents="none"
      />

      <Container maxW="md" position="relative" zIndex={1}>
        <VStack spacing={8} className="fade-in">
          {/* Logo/Header */}
          <VStack spacing={3}>
            <Heading
              size="2xl"
              className="gradient-text"
              textAlign="center"
              bgGradient="linear(to-r, teal.400, blue.400)"
              bgClip="text"
            >
              PennerBot
            </Heading>
          </VStack>

          {/* Login Form */}
          <Box
            w="100%"
            bg="gray.800"
            p={8}
            borderRadius="2xl"
            borderWidth="1px"
            borderColor="whiteAlpha.200"
            boxShadow="0 8px 32px rgba(0, 0, 0, 0.4)"
            className="glass"
          >
            <VStack spacing={6} align="stretch">
              <VStack spacing={3}>
                <Heading size="md" textAlign="center" color="white" fontWeight="semibold">
                  Bei Pennergame.de anmelden
                </Heading>
                
                {/* Backend Status Indicator */}
                <HStack spacing={2} justify="center">
                  {backendStatus === "checking" && (
                    <>
                      <Spinner size="xs" color="gray.400" />
                      <Text fontSize="xs" color="gray.400">
                        Backend wird geprüft...
                      </Text>
                    </>
                  )}
                  {backendStatus === "online" && (
                    <>
                      <Box
                        w={2}
                        h={2}
                        borderRadius="full"
                        bg="green.400"
                        boxShadow="0 0 8px rgba(72, 187, 120, 0.6)"
                        className="badge-pulse"
                      />
                      <Text fontSize="xs" color="green.400" fontWeight="medium">
                        Backend verbunden
                      </Text>
                    </>
                  )}
                  {backendStatus === "offline" && (
                    <>
                      <Icon as={FiAlertCircle} color="red.400" boxSize={3} />
                      <Text fontSize="xs" color="red.400" fontWeight="medium">
                        Backend nicht erreichbar
                      </Text>
                    </>
                  )}
                </HStack>
              </VStack>

              <FormControl isDisabled={backendStatus !== "online"}>
                <FormLabel color="gray.300" fontWeight="medium">
                  Benutzername
                </FormLabel>
                <InputGroup>
                  <InputLeftElement pointerEvents="none">
                    <Icon as={FiUser} color="gray.400" />
                  </InputLeftElement>
                  <Input
                    placeholder="Dein Pennergame Benutzername"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    onKeyPress={handleKeyPress}
                    size="lg"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _placeholder={{ color: "gray.400" }}
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{
                      borderColor: "teal.400",
                      boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                    }}
                  />
                </InputGroup>
              </FormControl>

              <FormControl isDisabled={backendStatus !== "online"}>
                <FormLabel color="gray.300" fontWeight="medium">
                  Passwort
                </FormLabel>
                <InputGroup>
                  <InputLeftElement pointerEvents="none">
                    <Icon as={FiLock} color="gray.400" />
                  </InputLeftElement>
                  <Input
                    type="password"
                    placeholder="Dein Pennergame Passwort"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyPress={handleKeyPress}
                    size="lg"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _placeholder={{ color: "gray.400" }}
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{
                      borderColor: "teal.400",
                      boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                    }}
                  />
                </InputGroup>
              </FormControl>

              <FormControl isDisabled={backendStatus !== "online"}>
                <FormLabel color="gray.300" fontWeight="medium">
                  <Icon as={FiGlobe} mr={2} />
                  Stadt auswählen
                </FormLabel>
                <Select
                  value={city}
                  onChange={(e) => handleCityChange(e.target.value)}
                  size="lg"
                  bg="gray.700"
                  border="1px solid"
                  borderColor="whiteAlpha.300"
                  color="white"
                  _hover={{ borderColor: "teal.400" }}
                  _focus={{
                    borderColor: "teal.400",
                    boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                  }}
                >
                  {cities.map((cityOption) => (
                    <option key={cityOption.key} value={cityOption.key}>
                      {cityOption.name}
                    </option>
                  ))}
                </Select>
                <Text fontSize="xs" color="gray.500" mt={1}>
                  Wähle die Pennergame-Stadt aus, mit der du dich anmelden möchtest
                </Text>
              </FormControl>

              {/* Advanced Settings - User Agent */}
              <Box w="100%" borderTop="1px solid" borderColor="whiteAlpha.200" pt={2}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onToggle}
                  w="100%"
                  justifyContent="space-between"
                  rightIcon={<Icon as={isOpen ? FiChevronUp : FiChevronDown} />}
                  leftIcon={<Icon as={FiSettings} />}
                  color="gray.400"
                  _hover={{ color: "gray.200", bg: "whiteAlpha.100" }}
                >
                  Erweiterte Einstellungen
                </Button>
                <Collapse in={isOpen} animateOpacity>
                  <Box pt={4}>
                    <FormControl isDisabled={backendStatus !== "online"}>
                      <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                        User-Agent
                      </FormLabel>
                      <Input
                        placeholder="z.B. Mozilla/5.0 oder PennerBot"
                        value={userAgent}
                        onChange={(e) => setUserAgent(e.target.value)}
                        size="md"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        fontSize="sm"
                        _placeholder={{ color: "gray.400" }}
                        _hover={{ borderColor: "teal.400" }}
                        _focus={{
                          borderColor: "teal.400",
                          boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                        }}
                      />
                      <Text fontSize="xs" color="gray.500" mt={2}>
                        Der User-Agent wird vor dem Login gesetzt und bei allen Requests verwendet
                      </Text>
                    </FormControl>
                  </Box>
                </Collapse>
              </Box>

              <Button
                colorScheme="teal"
                size="lg"
                w="100%"
                onClick={handleLogin}
                isLoading={loading}
                loadingText="Anmelden..."
                isDisabled={backendStatus !== "online"}
                leftIcon={<Icon as={FiLogIn} />}
                className="btn-glow"
                _hover={{
                  transform: "translateY(-2px)",
                  boxShadow: "0 8px 25px rgba(56, 178, 172, 0.5)",
                }}
                transition="all 0.3s"
                fontWeight="bold"
              >
                Jetzt anmelden
              </Button>

              {backendStatus === "offline" && (
                <Box
                  p={3}
                  bg="red.900"
                  borderRadius="md"
                  borderWidth="1px"
                  borderColor="red.700"
                >
                  <HStack spacing={2}>
                    <Icon as={FiServer} color="red.400" boxSize={4} />
                    <Text fontSize="sm" color="red.300">
                      Backend-Server ist nicht erreichbar. Bitte starte den Server und versuche es erneut.
                    </Text>
                  </HStack>
                </Box>
              )}

              <Text fontSize="xs" color="gray.500" textAlign="center">
                Deine Zugangsdaten werden sicher an Pennergame.de übermittelt
              </Text>
            </VStack>
          </Box>

          <Text fontSize="sm" color="gray.500" textAlign="center">
            © 2025 PennerBot - Automatisierung für Pennergame.de
          </Text>
        </VStack>
      </Container>
    </Box>
  );
};
