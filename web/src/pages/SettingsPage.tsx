import { useState, useEffect } from "react";
import { 
  VStack, 
  HStack,
  Text, 
  Heading, 
  FormControl, 
  FormLabel, 
  Input, 
  Button, 
  Icon, 
  useToast, 
  Spinner,
  Select,
  Switch,
  Collapse,
  Box,
  Checkbox,
  CheckboxGroup,
  Stack
} from "@chakra-ui/react";
import { DashboardCard } from "../components/DashboardCard";
import { FiSettings, FiSave, FiChevronDown, FiChevronRight } from "react-icons/fi";
import { getApiUrl } from "../utils/api";

interface BotConfigSettings {
  bottles_enabled: boolean;
  bottles_duration_minutes: number;
  bottles_pause_minutes: number;
  bottles_autosell_enabled: boolean;
  bottles_min_price: number;
  training_enabled: boolean;
  training_skills: string; // JSON string: ["att", "def", "agi"]
  training_att_max_level: number;
  training_def_max_level: number;
  training_agi_max_level: number;
  training_pause_minutes: number;
  training_autodrink_enabled: boolean;
  training_target_promille: number;
}

// Vordefinierte Zeiten für Pfandflaschensuche (in Minuten)
const BOTTLE_DURATION_OPTIONS = [10, 30, 60, 180, 360, 540, 720];

// Skill-Definitionen
const TRAINING_SKILLS = [
  { value: "att", label: "⚔️ Angriff", emoji: "⚔️" },
  { value: "def", label: "🛡️ Verteidigung", emoji: "🛡️" },
  { value: "agi", label: "⚡ Geschicklichkeit", emoji: "⚡" },
];

// Formatierung für Zeitauswahl
const formatDuration = (minutes: number): string => {
  if (minutes < 60) return `${minutes} Min`;
  if (minutes < 1440) return `${minutes / 60} Std`;
  return `${minutes / 1440} Tage`;
};

export const SettingsPage = () => {
  const [userAgent, setUserAgent] = useState("PennerBot");
  const [botConfig, setBotConfig] = useState<BotConfigSettings>({
    bottles_enabled: false,
    bottles_duration_minutes: 60,
    bottles_pause_minutes: 5,
    bottles_autosell_enabled: false,
    bottles_min_price: 25,
    training_enabled: false,
    training_skills: '["att", "def", "agi"]',
    training_att_max_level: 999,
    training_def_max_level: 999,
    training_agi_max_level: 999,
    training_pause_minutes: 5,
    training_autodrink_enabled: false,
    training_target_promille: 2.5,
  });
  const [bottlesExpanded, setBottlesExpanded] = useState(false);
  const [trainingExpanded, setTrainingExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const toast = useToast();

  // Load current settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setInitialLoading(true);
    try {
      // Load general settings
      const settingsResponse = await fetch(getApiUrl("/settings"));
      if (settingsResponse.ok) {
        const data = await settingsResponse.json();
        if (data.settings && data.settings.user_agent) {
          setUserAgent(data.settings.user_agent);
        }
      }

      // Load bot config
      const configResponse = await fetch(getApiUrl("/bot/config"));
      if (configResponse.ok) {
        const data = await configResponse.json();
        if (data.config) {
          setBotConfig({
            bottles_enabled: data.config.bottles_enabled ?? true,
            bottles_duration_minutes: data.config.bottles_duration_minutes ?? 60,
            bottles_pause_minutes: data.config.bottles_pause_minutes ?? 5,
            bottles_autosell_enabled: data.config.bottles_autosell_enabled ?? false,
            bottles_min_price: data.config.bottles_min_price ?? 20,
            training_enabled: data.config.training_enabled ?? false,
            training_skills: data.config.training_skills ?? '["att", "def", "agi"]',
            training_att_max_level: data.config.training_att_max_level ?? 999,
            training_def_max_level: data.config.training_def_max_level ?? 999,
            training_agi_max_level: data.config.training_agi_max_level ?? 999,
            training_pause_minutes: data.config.training_pause_minutes ?? 5,
            training_autodrink_enabled: data.config.training_autodrink_enabled ?? false,
            training_target_promille: data.config.training_target_promille ?? 2.5,
          });
        }
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
      toast({
        title: "Fehler",
        description: "Einstellungen konnten nicht geladen werden",
        status: "error",
        duration: 3000,
      });
    } finally {
      setInitialLoading(false);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      // Save general settings
      const settingsResponse = await fetch(getApiUrl("/settings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_agent: userAgent }),
      });

      // Save bot config
      const configResponse = await fetch(getApiUrl("/bot/config"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(botConfig),
      });

      if (settingsResponse.ok && configResponse.ok) {
        toast({
          title: "Gespeichert",
          description: "Einstellungen wurden erfolgreich gespeichert",
          status: "success",
          duration: 2000,
        });
      } else {
        throw new Error("Failed to save");
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Speichern fehlgeschlagen",
        status: "error",
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <VStack align="stretch" spacing={6} className="fade-in">
        <Heading size="lg" color="white">
          Einstellungen
        </Heading>
        <DashboardCard title="Bot-Konfiguration" icon={FiSettings}>
          <VStack align="center" py={8}>
            <Spinner size="xl" color="teal.400" />
            <Text color="gray.400" mt={4}>Lade Einstellungen...</Text>
          </VStack>
        </DashboardCard>
      </VStack>
    );
  }

  return (
    <VStack align="stretch" spacing={6} className="fade-in">
      <Heading size="lg" color="white">
        Einstellungen
      </Heading>

      {/* Bot Automation Settings - OBEN */}
      <DashboardCard title="Bot Automatisierung" icon={FiSettings}>
        <VStack align="stretch" spacing={4}>
          {/* Pfandflaschen sammeln - Aufklappbar */}
          <Box>
            <HStack
              justify="space-between"
              p={3}
              bg="whiteAlpha.50"
              borderRadius="md"
              cursor="pointer"
              onClick={() => setBottlesExpanded(!bottlesExpanded)}
              _hover={{ bg: "whiteAlpha.100" }}
              transition="background 0.2s"
            >
              <HStack spacing={3}>
                <Icon 
                  as={bottlesExpanded ? FiChevronDown : FiChevronRight} 
                  color="teal.400" 
                  boxSize={5}
                />
                <Text color="gray.200" fontWeight="medium" fontSize="md">
                  🍾 Pfandflaschen sammeln
                </Text>
              </HStack>
              <Switch
                size="lg"
                colorScheme="teal"
                isChecked={botConfig.bottles_enabled}
                onChange={(e) => {
                  e.stopPropagation();
                  setBotConfig({ ...botConfig, bottles_enabled: e.target.checked });
                }}
              />
            </HStack>

            <Collapse in={bottlesExpanded && botConfig.bottles_enabled} animateOpacity>
              <VStack align="stretch" spacing={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Sammeldauer
                  </FormLabel>
                  <Select
                    value={botConfig.bottles_duration_minutes}
                    onChange={(e) =>
                      setBotConfig({ 
                        ...botConfig, 
                        bottles_duration_minutes: parseInt(e.target.value) 
                      })
                    }
                    size="md"
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
                    {BOTTLE_DURATION_OPTIONS.map((duration) => (
                      <option key={duration} value={duration}>
                        {formatDuration(duration)}
                      </option>
                    ))}
                  </Select>
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Wie lange der Bot aktiv Pfandflaschen sammeln soll
                  </Text>
                </FormControl>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Pause zwischen Sammelrunden (Minuten)
                  </FormLabel>
                  <Input
                    type="number"
                    value={botConfig.bottles_pause_minutes}
                    onChange={(e) =>
                      setBotConfig({ 
                        ...botConfig, 
                        bottles_pause_minutes: parseInt(e.target.value) || 5 
                      })
                    }
                    min={1}
                    max={60}
                    size="md"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{
                      borderColor: "teal.400",
                      boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                    }}
                  />
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Wartezeit nach Abschluss (±20% Variation gegen Erkennung)
                  </Text>
                </FormControl>

                {/* Auto-Sell Einstellungen */}
                <Box 
                  mt={4} 
                  p={3} 
                  bg="whiteAlpha.50" 
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="teal.400"
                >
                  <HStack justify="space-between" mb={3}>
                    <Text color="gray.200" fontWeight="medium" fontSize="sm">
                      💰 Auto-Verkauf
                    </Text>
                    <Switch
                      size="md"
                      colorScheme="teal"
                      isChecked={botConfig.bottles_autosell_enabled}
                      onChange={(e) =>
                        setBotConfig({ 
                          ...botConfig, 
                          bottles_autosell_enabled: e.target.checked 
                        })
                      }
                    />
                  </HStack>

                  <Collapse in={botConfig.bottles_autosell_enabled} animateOpacity>
                    <FormControl>
                      <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                        Mindestpreis (Cent)
                      </FormLabel>
                      <Select
                        value={botConfig.bottles_min_price}
                        onChange={(e) =>
                          setBotConfig({ 
                            ...botConfig, 
                            bottles_min_price: parseInt(e.target.value) 
                          })
                        }
                        size="md"
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
                        {[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25].map((price) => (
                          <option key={price} value={price}>
                            {price} Cent
                          </option>
                        ))}
                      </Select>
                      <Text fontSize="xs" color="gray.500" mt={1}>
                        Verkaufe alle Flaschen automatisch wenn Preis ≥ {botConfig.bottles_min_price} Cent
                      </Text>
                    </FormControl>
                  </Collapse>
                </Box>
              </VStack>
            </Collapse>
          </Box>

          {/* Weiterbildungen - Aufklappbar */}
          <Box>
            <HStack
              justify="space-between"
              p={3}
              bg="whiteAlpha.50"
              borderRadius="md"
              cursor="pointer"
              onClick={() => setTrainingExpanded(!trainingExpanded)}
              _hover={{ bg: "whiteAlpha.100" }}
              transition="background 0.2s"
            >
              <HStack spacing={3}>
                <Icon 
                  as={trainingExpanded ? FiChevronDown : FiChevronRight} 
                  color="teal.400" 
                  boxSize={5}
                />
                <Text color="gray.200" fontWeight="medium" fontSize="md">
                  🎓 Weiterbildungen
                </Text>
              </HStack>
              <Switch
                size="lg"
                colorScheme="teal"
                isChecked={botConfig.training_enabled}
                onChange={(e) => {
                  e.stopPropagation();
                  setBotConfig({ ...botConfig, training_enabled: e.target.checked });
                }}
              />
            </HStack>

            <Collapse in={trainingExpanded && botConfig.training_enabled} animateOpacity>
              <VStack align="stretch" spacing={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Aktive Skills
                  </FormLabel>
                  <CheckboxGroup
                    value={JSON.parse(botConfig.training_skills)}
                    onChange={(values) => {
                      // Stelle sicher dass mindestens ein Skill aktiv ist
                      if (values.length > 0) {
                        setBotConfig({ 
                          ...botConfig, 
                          training_skills: JSON.stringify(values) 
                        });
                      }
                    }}
                  >
                    <Stack spacing={2}>
                      {TRAINING_SKILLS.map((skill) => (
                        <Checkbox 
                          key={skill.value} 
                          value={skill.value}
                          colorScheme="teal"
                          size="md"
                        >
                          <Text color="gray.200" fontSize="sm">{skill.label}</Text>
                        </Checkbox>
                      ))}
                    </Stack>
                  </CheckboxGroup>
                  <Text fontSize="xs" color="gray.500" mt={2}>
                    Der Bot trainiert zufällig zwischen den ausgewählten Skills
                  </Text>
                </FormControl>

                {/* Max Level Settings */}
                <Box 
                  p={3} 
                  bg="whiteAlpha.50" 
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="purple.400"
                >
                  <Text color="gray.200" fontWeight="medium" fontSize="sm" mb={3}>
                    📊 Max Level pro Skill
                  </Text>
                  
                  <VStack align="stretch" spacing={3}>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">
                        ⚔️ Angriff - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_att_max_level}
                        onChange={(e) =>
                          setBotConfig({ 
                            ...botConfig, 
                            training_att_max_level: Math.max(1, Math.min(999, parseInt(e.target.value) || 1))
                          })
                        }
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "teal.400" }}
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">
                        🛡️ Verteidigung - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_def_max_level}
                        onChange={(e) =>
                          setBotConfig({ 
                            ...botConfig, 
                            training_def_max_level: Math.max(1, Math.min(999, parseInt(e.target.value) || 1))
                          })
                        }
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "teal.400" }}
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">
                        ⚡ Geschicklichkeit - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_agi_max_level}
                        onChange={(e) =>
                          setBotConfig({ 
                            ...botConfig, 
                            training_agi_max_level: Math.max(1, Math.min(999, parseInt(e.target.value) || 1))
                          })
                        }
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "teal.400" }}
                      />
                    </FormControl>
                  </VStack>
                  <Text fontSize="xs" color="gray.500" mt={2}>
                    999 = Kein Limit. Training stoppt automatisch bei Erreichen des Max Levels.
                  </Text>
                </Box>

                {/* Auto-Trinken Einstellungen */}
                <Box 
                  p={3} 
                  bg="whiteAlpha.50" 
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="purple.400"
                >
                  <HStack justify="space-between" mb={3}>
                    <Text color="gray.200" fontWeight="medium" fontSize="sm">
                      🍺 Auto-Trinken vor Training
                    </Text>
                    <Switch
                      size="md"
                      colorScheme="purple"
                      isChecked={botConfig.training_autodrink_enabled}
                      onChange={(e) =>
                        setBotConfig({ 
                          ...botConfig, 
                          training_autodrink_enabled: e.target.checked 
                        })
                      }
                    />
                  </HStack>

                  <Collapse in={botConfig.training_autodrink_enabled} animateOpacity>
                    <FormControl>
                      <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                        Ziel-Promille (2.0 - 3.0‰)
                      </FormLabel>
                      <HStack spacing={2}>
                        <Input
                          type="number"
                          step="0.1"
                          value={botConfig.training_target_promille}
                          onChange={(e) => {
                            const value = parseFloat(e.target.value) || 2.5;
                            setBotConfig({ 
                              ...botConfig, 
                              training_target_promille: Math.max(2.0, Math.min(3.0, value))
                            });
                          }}
                          min={2.0}
                          max={3.0}
                          size="md"
                          bg="gray.700"
                          border="1px solid"
                          borderColor="whiteAlpha.300"
                          color="white"
                          _hover={{ borderColor: "purple.400" }}
                          _focus={{
                            borderColor: "purple.400",
                            boxShadow: "0 0 0 1px var(--chakra-colors-purple-400)",
                          }}
                        />
                        <Text color="gray.400" fontSize="sm" minW="40px">‰</Text>
                      </HStack>
                      <Text fontSize="xs" color="gray.500" mt={2}>
                        Der Bot trinkt automatisch vor jeder Weiterbildung bis zum Zielwert.
                        <br />
                        <Text as="span" color="yellow.400">⚠️ Sicher: 2.0-3.0‰</Text> | 
                        <Text as="span" color="red.400"> Krankenhaus ab 4.0‰!</Text>
                      </Text>
                    </FormControl>
                  </Collapse>
                </Box>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Pause zwischen Weiterbildungen (Minuten)
                  </FormLabel>
                  <Input
                    type="number"
                    value={botConfig.training_pause_minutes}
                    onChange={(e) =>
                      setBotConfig({ 
                        ...botConfig, 
                        training_pause_minutes: parseInt(e.target.value) || 5 
                      })
                    }
                    min={1}
                    max={60}
                    size="md"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{
                      borderColor: "teal.400",
                      boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)",
                    }}
                  />
                  <Text fontSize="xs" color="gray.500" mt={1}>
                    Wartezeit nach Abschluss einer Weiterbildung (±20% Variation)
                  </Text>
                </FormControl>
              </VStack>
            </Collapse>
          </Box>
        </VStack>
      </DashboardCard>

      {/* General Settings - UNTEN */}
      <DashboardCard title="Allgemeine Einstellungen" icon={FiSettings}>
        <VStack align="stretch" spacing={4}>
          <FormControl>
            <FormLabel color="gray.300" fontWeight="medium">
              User-Agent
            </FormLabel>
            <Input
              value={userAgent}
              onChange={(e) => setUserAgent(e.target.value)}
              placeholder="PennerBot"
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
            />
            <Text fontSize="sm" color="gray.500" mt={2}>
              Der User-Agent wird für HTTP-Anfragen an Pennergame.de verwendet
            </Text>
          </FormControl>
        </VStack>
      </DashboardCard>

      {/* Save Button */}
      <Button
        colorScheme="teal"
        size="lg"
        onClick={handleSave}
        isLoading={loading}
        leftIcon={<Icon as={FiSave} />}
        className="btn-glow"
        _hover={{ transform: "translateY(-2px)" }}
      >
        Alle Einstellungen speichern
      </Button>
    </VStack>
  );
};
