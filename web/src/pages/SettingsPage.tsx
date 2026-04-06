import { useState, useEffect } from "react";
import { 
  VStack, 
  HStack,
  Text, 
  Heading, 
  FormControl, 
  FormLabel, 
  Input, 
  Icon,
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
import { FiSettings, FiChevronDown, FiChevronRight } from "react-icons/fi";
import { getApiUrl } from "../utils/api";

interface BotConfigSettings {
  bottles_enabled: boolean;
  bottles_duration_minutes: number;
  bottles_pause_minutes: number;
  bottles_autosell_enabled: boolean;
  bottles_min_price: number;
  training_enabled: boolean;
  training_skills: string;
  training_att_max_level: number;
  training_def_max_level: number;
  training_agi_max_level: number;
  training_pause_minutes: number;
  training_autodrink_enabled: boolean;
  training_target_promille: number;
}

const BOTTLE_DURATION_OPTIONS = [10, 30, 60, 180, 360, 540, 720];

const CITIES = [
  { key: "hamburg", name: "Hamburg", url: "https://www.pennergame.de" },
  { key: "vatikan", name: "Vatikan", url: "https://vatikan.pennergame.de" },
  { key: "sylt", name: "Sylt", url: "https://sylt.pennergame.de" },
  { key: "malle", name: "Malle", url: "https://malle.pennergame.de" },
  { key: "reloaded", name: "Hamburg Reloaded", url: "https://reloaded.pennergame.de" },
  { key: "koeln", name: "Köln", url: "https://koeln.pennergame.de" },
  { key: "berlin", name: "Berlin", url: "https://berlin.pennergame.de" },
  { key: "muenchen", name: "München", url: "https://muenchen.pennergame.de" },
];

const TRAINING_SKILLS = [
  { value: "att", label: "⚔️ Angriff" },
  { value: "def", label: "🛡️ Verteidigung" },
  { value: "agi", label: "⚡ Geschicklichkeit" },
];

const formatDuration = (minutes: number): string => {
  if (minutes < 60) return `${minutes} Min`;
  if (minutes < 1440) return `${minutes / 60} Std`;
  return `${minutes / 1440} Tage`;
};

export const SettingsPage = () => {
  const [userAgent, setUserAgent] = useState("PennerBot");
  const [city, setCity] = useState("hamburg");
  const [botConfig, setBotConfig] = useState<BotConfigSettings>({
    bottles_enabled: false,
    bottles_duration_minutes: 60,
    bottles_pause_minutes: 1,
    bottles_autosell_enabled: false,
    bottles_min_price: 25,
    training_enabled: false,
    training_skills: '["att", "def", "agi"]',
    training_att_max_level: 999,
    training_def_max_level: 999,
    training_agi_max_level: 999,
    training_pause_minutes: 1,
    training_autodrink_enabled: false,
    training_target_promille: 3.5,
  });
  const [bottlesExpanded, setBottlesExpanded] = useState(false);
  const [trainingExpanded, setTrainingExpanded] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const saveConfig = async (key: keyof BotConfigSettings, value: boolean | number | string) => {
    const newConfig = { ...botConfig, [key]: value };
    setBotConfig(newConfig);
    setSavingKey(key);

    try {
      await fetch(getApiUrl("/bot/config"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newConfig),
      });
    } catch (error) {
      console.error("Failed to save:", key, error);
    } finally {
      setSavingKey(null);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setInitialLoading(true);
    try {
      const configResponse = await fetch(getApiUrl("/bot/config"), { 
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" }
      });
      if (configResponse.ok) {
        const data = await configResponse.json();
        if (data.config) {
          setBotConfig({
            bottles_enabled: data.config.bottles_enabled ?? false,
            bottles_duration_minutes: data.config.bottles_duration_minutes ?? 60,
            bottles_pause_minutes: data.config.bottles_pause_minutes ?? 1,
            bottles_autosell_enabled: data.config.bottles_autosell_enabled ?? false,
            bottles_min_price: data.config.bottles_min_price ?? 25,
            training_enabled: data.config.training_enabled ?? false,
            training_skills: data.config.training_skills ?? '["att", "def", "agi"]',
            training_att_max_level: data.config.training_att_max_level ?? 999,
            training_def_max_level: data.config.training_def_max_level ?? 999,
            training_agi_max_level: data.config.training_agi_max_level ?? 999,
            training_pause_minutes: data.config.training_pause_minutes ?? 1,
            training_autodrink_enabled: data.config.training_autodrink_enabled ?? false,
            training_target_promille: data.config.training_target_promille ?? 3.5,
          });
        }
      }

      const settingsResponse = await fetch(getApiUrl("/settings"), {
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" }
      });
      if (settingsResponse.ok) {
        const data = await settingsResponse.json();
        if (data.settings?.user_agent) setUserAgent(data.settings.user_agent);
        if (data.settings?.city) setCity(data.settings.city);
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
    } finally {
      setInitialLoading(false);
    }
  };

  if (initialLoading) {
    return (
      <VStack align="stretch" spacing={6} className="fade-in">
        <Heading size="lg" color="white">Einstellungen</Heading>
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
      <Heading size="lg" color="white">Einstellungen</Heading>

      <DashboardCard title="Bot Automatisierung" icon={FiSettings}>
        <VStack align="stretch" spacing={4}>
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
                <Icon as={bottlesExpanded ? FiChevronDown : FiChevronRight} color="teal.400" boxSize={5} />
                <Text color="gray.200" fontWeight="medium" fontSize="md">🍾 Pfandflaschen sammeln</Text>
              </HStack>
              <Switch
                size="lg"
                colorScheme="teal"
                isChecked={botConfig.bottles_enabled}
                isDisabled={savingKey === "bottles_enabled"}
                onChange={(e) => {
                  e.stopPropagation();
                  saveConfig("bottles_enabled", e.target.checked);
                }}
              />
            </HStack>

            <Collapse in={bottlesExpanded && botConfig.bottles_enabled} animateOpacity>
              <VStack align="stretch" spacing={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Sammeldauer</FormLabel>
                  <Select
                    value={botConfig.bottles_duration_minutes}
                    onChange={(e) => saveConfig("bottles_duration_minutes", parseInt(e.target.value))}
                    size="md"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{ borderColor: "teal.400", boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)" }}
                  >
                    {BOTTLE_DURATION_OPTIONS.map((duration) => (
                      <option key={duration} value={duration}>{formatDuration(duration)}</option>
                    ))}
                  </Select>
                </FormControl>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Pause zwischen Sammelrunden</FormLabel>
                  <Input
                    type="number"
                    value={botConfig.bottles_pause_minutes}
                    onChange={(e) => saveConfig("bottles_pause_minutes", parseInt(e.target.value) || 1)}
                    min={1}
                    max={60}
                    size="md"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                    _hover={{ borderColor: "teal.400" }}
                    _focus={{ borderColor: "teal.400", boxShadow: "0 0 0 1px var(--chakra-colors-teal-400)" }}
                  />
                </FormControl>

                <Box mt={4} p={3} bg="whiteAlpha.50" borderRadius="md" borderLeft="3px solid" borderColor="teal.400">
                  <HStack justify="space-between" mb={3}>
                    <Text color="gray.200" fontWeight="medium" fontSize="sm">💰 Auto-Verkauf</Text>
                    <Switch
                      size="md"
                      colorScheme="teal"
                      isChecked={botConfig.bottles_autosell_enabled}
                      onChange={(e) => saveConfig("bottles_autosell_enabled", e.target.checked)}
                    />
                  </HStack>
                  <Collapse in={botConfig.bottles_autosell_enabled} animateOpacity>
                    <FormControl>
                      <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Mindestpreis (Cent)</FormLabel>
                      <Select
                        value={botConfig.bottles_min_price}
                        onChange={(e) => saveConfig("bottles_min_price", parseInt(e.target.value))}
                        size="md"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "teal.400" }}
                      >
                        {[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25].map((price) => (
                          <option key={price} value={price}>{price} Cent</option>
                        ))}
                      </Select>
                    </FormControl>
                  </Collapse>
                </Box>
              </VStack>
            </Collapse>
          </Box>

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
                <Icon as={trainingExpanded ? FiChevronDown : FiChevronRight} color="teal.400" boxSize={5} />
                <Text color="gray.200" fontWeight="medium" fontSize="md">🎓 Weiterbildungen</Text>
              </HStack>
              <Switch
                size="lg"
                colorScheme="teal"
                isChecked={botConfig.training_enabled}
                isDisabled={savingKey === "training_enabled"}
                onChange={(e) => {
                  e.stopPropagation();
                  saveConfig("training_enabled", e.target.checked);
                }}
              />
            </HStack>

            <Collapse in={trainingExpanded && botConfig.training_enabled} animateOpacity>
              <VStack align="stretch" spacing={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Aktive Skills</FormLabel>
                  <CheckboxGroup
                    value={JSON.parse(botConfig.training_skills)}
                    onChange={(values) => {
                      if (values.length > 0) {
                        saveConfig("training_skills", JSON.stringify(values));
                      }
                    }}
                  >
                    <Stack spacing={2}>
                      {TRAINING_SKILLS.map((skill) => (
                        <Checkbox key={skill.value} value={skill.value} colorScheme="teal" size="md">
                          <Text color="gray.200" fontSize="sm">{skill.label}</Text>
                        </Checkbox>
                      ))}
                    </Stack>
                  </CheckboxGroup>
                </FormControl>

                <Box p={3} bg="whiteAlpha.50" borderRadius="md" borderLeft="3px solid" borderColor="purple.400">
                  <Text color="gray.200" fontWeight="medium" fontSize="sm" mb={3}>📊 Max Level pro Skill</Text>
                  <VStack align="stretch" spacing={3}>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">⚔️ Angriff - Max Level</FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_att_max_level}
                        onChange={(e) => saveConfig("training_att_max_level", Math.max(1, Math.min(999, parseInt(e.target.value) || 1)))}
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">🛡️ Verteidigung - Max Level</FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_def_max_level}
                        onChange={(e) => saveConfig("training_def_max_level", Math.max(1, Math.min(999, parseInt(e.target.value) || 1)))}
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">⚡ Geschicklichkeit - Max Level</FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_agi_max_level}
                        onChange={(e) => saveConfig("training_agi_max_level", Math.max(1, Math.min(999, parseInt(e.target.value) || 1)))}
                        min={1}
                        max={999}
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                      />
                    </FormControl>
                  </VStack>
                </Box>

                <Box p={3} bg="whiteAlpha.50" borderRadius="md" borderLeft="3px solid" borderColor="purple.400">
                  <HStack justify="space-between" mb={3}>
                    <Text color="gray.200" fontWeight="medium" fontSize="sm">🍺 Auto-Trinken vor Training</Text>
                    <Switch
                      size="md"
                      colorScheme="purple"
                      isChecked={botConfig.training_autodrink_enabled}
                      onChange={(e) => saveConfig("training_autodrink_enabled", e.target.checked)}
                    />
                  </HStack>
                  <Collapse in={botConfig.training_autodrink_enabled} animateOpacity>
                    <FormControl>
                      <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Ziel-Promille</FormLabel>
                      <HStack spacing={2}>
                        <Input
                          type="number"
                          step="0.1"
                          value={botConfig.training_target_promille}
                          onChange={(e) => saveConfig("training_target_promille", Math.max(2.0, Math.min(4.0, parseFloat(e.target.value) || 3.5)))}
                          min={2.0}
                          max={4.0}
                          size="md"
                          bg="gray.700"
                          border="1px solid"
                          borderColor="whiteAlpha.300"
                          color="white"
                        />
                        <Text color="gray.400" fontSize="sm">‰</Text>
                      </HStack>
                    </FormControl>
                  </Collapse>
                </Box>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">Pause zwischen Weiterbildungen</FormLabel>
                  <Input
                    type="number"
                    value={botConfig.training_pause_minutes}
                    onChange={(e) => saveConfig("training_pause_minutes", parseInt(e.target.value) || 1)}
                    min={1}
                    max={60}
                    size="md"
                    bg="gray.700"
                    border="1px solid"
                    borderColor="whiteAlpha.300"
                    color="white"
                  />
                </FormControl>
              </VStack>
            </Collapse>
          </Box>
        </VStack>
      </DashboardCard>

      <DashboardCard title="Allgemeine Einstellungen" icon={FiSettings}>
        <VStack align="stretch" spacing={4}>
          <FormControl>
            <FormLabel color="gray.300" fontWeight="medium">Stadt</FormLabel>
            <Select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              size="lg"
              bg="gray.700"
              border="1px solid"
              borderColor="whiteAlpha.300"
              color="white"
            >
              {CITIES.map((cityOption) => (
                <option key={cityOption.key} value={cityOption.key}>
                  {cityOption.name} ({cityOption.url})
                </option>
              ))}
            </Select>
          </FormControl>

          <FormControl>
            <FormLabel color="gray.300" fontWeight="medium">User-Agent</FormLabel>
            <Input
              value={userAgent}
              onChange={(e) => setUserAgent(e.target.value)}
              placeholder="PennerBot"
              size="lg"
              bg="gray.700"
              border="1px solid"
              borderColor="whiteAlpha.300"
              color="white"
            />
          </FormControl>
        </VStack>
      </DashboardCard>

      <Box py={4} textAlign="center">
        <Text fontSize="sm" color="gray.500">✨ Einstellungen werden automatisch gespeichert</Text>
        {savingKey && <Spinner size="sm" color="teal.400" mt={2} />}
      </Box>
    </VStack>
  );
};