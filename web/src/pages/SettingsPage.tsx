import { useState, useEffect, useRef } from "react";
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
  Stack,
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
  fight_enabled: boolean;
  fight_pause_minutes: number;
  rotation_enabled: boolean;
  rotation_start_with: string;
}

type BotConfigKey = keyof BotConfigSettings;
type BotConfigValue = BotConfigSettings[BotConfigKey];

const BOTTLE_DURATION_OPTIONS = [60, 180, 360, 540, 720];

const CITIES = [
  { key: "hamburg", name: "Hamburg", url: "https://www.pennergame.de" },
  { key: "vatikan", name: "Vatikan", url: "https://vatikan.pennergame.de" },
  { key: "sylt", name: "Sylt", url: "https://sylt.pennergame.de" },
  { key: "malle", name: "Malle", url: "https://malle.pennergame.de" },
  {
    key: "reloaded",
    name: "Hamburg Reloaded",
    url: "https://reloaded.pennergame.de",
  },
  { key: "koeln", name: "Köln", url: "https://koeln.pennergame.de" },
  { key: "berlin", name: "Berlin", url: "https://berlin.pennergame.de" },
  { key: "muenchen", name: "München", url: "https://muenchen.pennergame.de" },
];

const TRAINING_SKILLS = [
  { value: "att", label: "⚔️ Angriff" },
  { value: "def", label: "🛡️ Verteidigung" },
  { value: "agi", label: "⚡ Geschicklichkeit" },
];

const DEFAULT_BOT_CONFIG: BotConfigSettings = {
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
  fight_enabled: false,
  fight_pause_minutes: 1,
  rotation_enabled: false,
  rotation_start_with: "bottles",
};

const toBoolean = (value: unknown, fallback: boolean): boolean => {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value !== 0;
  if (typeof value === "string") return value === "true" || value === "1";
  return fallback;
};

const toNumber = (value: unknown, fallback: number): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const toString = (value: unknown, fallback: string): string =>
  typeof value === "string" ? value : fallback;

const normalizeBotConfig = (
  config: Partial<Record<BotConfigKey, unknown>> = {},
  fallback: BotConfigSettings = DEFAULT_BOT_CONFIG,
): BotConfigSettings => ({
  bottles_enabled: toBoolean(config.bottles_enabled, fallback.bottles_enabled),
  bottles_duration_minutes: toNumber(
    config.bottles_duration_minutes,
    fallback.bottles_duration_minutes,
  ),
  bottles_pause_minutes: toNumber(
    config.bottles_pause_minutes,
    fallback.bottles_pause_minutes,
  ),
  bottles_autosell_enabled: toBoolean(
    config.bottles_autosell_enabled,
    fallback.bottles_autosell_enabled,
  ),
  bottles_min_price: toNumber(config.bottles_min_price, fallback.bottles_min_price),
  training_enabled: toBoolean(config.training_enabled, fallback.training_enabled),
  training_skills: toString(config.training_skills, fallback.training_skills),
  training_att_max_level: toNumber(
    config.training_att_max_level,
    fallback.training_att_max_level,
  ),
  training_def_max_level: toNumber(
    config.training_def_max_level,
    fallback.training_def_max_level,
  ),
  training_agi_max_level: toNumber(
    config.training_agi_max_level,
    fallback.training_agi_max_level,
  ),
  training_pause_minutes: toNumber(
    config.training_pause_minutes,
    fallback.training_pause_minutes,
  ),
  training_autodrink_enabled: toBoolean(
    config.training_autodrink_enabled,
    fallback.training_autodrink_enabled,
  ),
  training_target_promille: toNumber(
    config.training_target_promille,
    fallback.training_target_promille,
  ),
  fight_enabled: toBoolean(config.fight_enabled, fallback.fight_enabled),
  fight_pause_minutes: toNumber(
    config.fight_pause_minutes,
    fallback.fight_pause_minutes,
  ),
  rotation_enabled: toBoolean(config.rotation_enabled, fallback.rotation_enabled),
  rotation_start_with: toString(
    config.rotation_start_with,
    fallback.rotation_start_with,
  ),
});

const formatDuration = (minutes: number): string => {
  if (minutes < 60) return `${minutes} Min`;
  if (minutes < 1440) return `${minutes / 60} Std`;
  return `${minutes / 1440} Tage`;
};

export const SettingsPage = () => {
  const [userAgent, setUserAgent] = useState("PennerBot");
  const [city, setCity] = useState("hamburg");
  const [botConfig, setBotConfig] =
    useState<BotConfigSettings>(DEFAULT_BOT_CONFIG);
  const [bottlesExpanded, setBottlesExpanded] = useState(false);
  const [trainingExpanded, setTrainingExpanded] = useState(false);
  const [fightExpanded, setFightExpanded] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [savingKeys, setSavingKeys] = useState<Set<BotConfigKey>>(new Set());
  const saveSequenceRef = useRef(0);
  const pendingConfigRef = useRef<
    Partial<Record<BotConfigKey, { value: BotConfigValue; sequence: number }>>
  >({});

  const getPendingConfig = (
    excludeKey?: BotConfigKey,
    excludeSequence?: number,
  ): Partial<BotConfigSettings> => {
    return Object.fromEntries(
      Object.entries(pendingConfigRef.current)
        .filter(([key, pending]) => {
          return !(
            key === excludeKey &&
            pending?.sequence === excludeSequence
          );
        })
        .map(([key, pending]) => [key, pending?.value]),
    ) as Partial<BotConfigSettings>;
  };

  const isSaving = (key: BotConfigKey): boolean => savingKeys.has(key);

  const saveConfig = async (
    key: BotConfigKey,
    value: boolean | number | string,
  ) => {
    const sequence = ++saveSequenceRef.current;
    pendingConfigRef.current[key] = { value, sequence };
    setBotConfig((current) => ({ ...current, [key]: value }));
    setSavingKeys((current) => new Set(current).add(key));

    try {
      const response = await fetch(getApiUrl("/bot/config"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ [key]: value }),
      });
      if (!response.ok) {
        console.error("Failed to save config, response:", response.status);
      } else {
        const result = await response.json();
        if (result.config) {
          const normalized = normalizeBotConfig(
            result.config as Partial<Record<BotConfigKey, unknown>>,
          );
          setBotConfig({
            ...normalized,
            ...getPendingConfig(key, sequence),
          });
        }
        console.log(
          "Config saved successfully:",
          key,
          "=",
          value,
          "-> response:",
          result,
        );
      }
    } catch (error) {
      console.error("Failed to save:", key, error);
    } finally {
      if (pendingConfigRef.current[key]?.sequence === sequence) {
        delete pendingConfigRef.current[key];
      }
      setSavingKeys((current) => {
        const next = new Set(current);
        next.delete(key);
        return next;
      });
    }
  };

  useEffect(() => {
    loadSettings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSettings = async () => {
    setInitialLoading(true);
    try {
      const configResponse = await fetch(getApiUrl("/bot/config"), {
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" },
      });
      if (configResponse.ok) {
        const data = await configResponse.json();
        if (data.config) {
          const normalized = normalizeBotConfig(
            data.config as Partial<Record<BotConfigKey, unknown>>,
          );
          setBotConfig({ ...normalized, ...getPendingConfig() });
          setBottlesExpanded(normalized.bottles_enabled);
          setTrainingExpanded(normalized.training_enabled);
          setFightExpanded(normalized.fight_enabled);
        }
      }

      const settingsResponse = await fetch(getApiUrl("/settings"), {
        cache: "no-store",
        headers: { "Cache-Control": "no-cache" },
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
      <VStack align="stretch" gap={6} className="fade-in">
        <Heading size="lg" color="white">
          Einstellungen
        </Heading>
        <DashboardCard title="Bot-Konfiguration" icon={FiSettings}>
          <VStack align="center" py={8}>
            <Spinner size="xl" color="teal.400" />
            <Text color="gray.400" mt={4}>
              Lade Einstellungen...
            </Text>
          </VStack>
        </DashboardCard>
      </VStack>
    );
  }

  return (
    <VStack align="stretch" gap={6} className="fade-in">
      <Heading size="lg" color="white">
        Einstellungen
      </Heading>

      <DashboardCard title="Bot Automatisierung" icon={FiSettings}>
        <VStack align="stretch" gap={4}>
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
              <HStack gap={3}>
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
                isDisabled={isSaving("bottles_enabled")}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => {
                  e.stopPropagation();
                  saveConfig("bottles_enabled", e.target.checked);
                }}
              />
            </HStack>

            <Collapse
              in={bottlesExpanded && botConfig.bottles_enabled}
              animateOpacity
            >
              <VStack align="stretch" gap={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Sammeldauer
                  </FormLabel>
                  <Select
                    value={botConfig.bottles_duration_minutes}
                    onChange={(e) =>
                      saveConfig(
                        "bottles_duration_minutes",
                        parseInt(e.target.value),
                      )
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
                </FormControl>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Pause zwischen Sammelrunden
                  </FormLabel>
                  <Input
                    type="number"
                    value={botConfig.bottles_pause_minutes}
                    onChange={(e) =>
                      saveConfig(
                        "bottles_pause_minutes",
                        parseInt(e.target.value) || 1,
                      )
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
                </FormControl>

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
                      isDisabled={isSaving("bottles_autosell_enabled")}
                      onChange={(e) =>
                        saveConfig("bottles_autosell_enabled", e.target.checked)
                      }
                    />
                  </HStack>
                  <Collapse
                    in={botConfig.bottles_autosell_enabled}
                    animateOpacity
                  >
                    <FormControl>
                      <FormLabel
                        color="gray.300"
                        fontWeight="medium"
                        fontSize="sm"
                      >
                        Mindestpreis (Cent)
                      </FormLabel>
                      <Select
                        value={botConfig.bottles_min_price}
                        onChange={(e) =>
                          saveConfig(
                            "bottles_min_price",
                            parseInt(e.target.value),
                          )
                        }
                        size="md"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "teal.400" }}
                      >
                        {[15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25].map(
                          (price) => (
                            <option key={price} value={price}>
                              {price} Cent
                            </option>
                          ),
                        )}
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
              <HStack gap={3}>
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
                isDisabled={isSaving("training_enabled")}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => {
                  e.stopPropagation();
                  saveConfig("training_enabled", e.target.checked);
                }}
              />
            </HStack>

            <Collapse
              in={trainingExpanded && botConfig.training_enabled}
              animateOpacity
            >
              <VStack align="stretch" gap={4} mt={4} pl={8}>
                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Aktive Skills
                  </FormLabel>
                  <CheckboxGroup
                    value={JSON.parse(botConfig.training_skills)}
                    onChange={(values) => {
                      if (values.length > 0) {
                        saveConfig("training_skills", JSON.stringify(values));
                      }
                    }}
                  >
                    <Stack gap={2}>
                      {TRAINING_SKILLS.map((skill) => (
                        <Checkbox
                          key={skill.value}
                          value={skill.value}
                          colorScheme="teal"
                          size="md"
                        >
                          <Text color="gray.200" fontSize="sm">
                            {skill.label}
                          </Text>
                        </Checkbox>
                      ))}
                    </Stack>
                  </CheckboxGroup>
                </FormControl>

                <Box
                  p={3}
                  bg="whiteAlpha.50"
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="purple.400"
                >
                  <Text
                    color="gray.200"
                    fontWeight="medium"
                    fontSize="sm"
                    mb={3}
                  >
                    📊 Max Level pro Skill
                  </Text>
                  <VStack align="stretch" gap={3}>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="xs">
                        ⚔️ Angriff - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_att_max_level}
                        onChange={(e) =>
                          saveConfig(
                            "training_att_max_level",
                            Math.max(
                              1,
                              Math.min(999, parseInt(e.target.value) || 1),
                            ),
                          )
                        }
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
                      <FormLabel color="gray.300" fontSize="xs">
                        🛡️ Verteidigung - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_def_max_level}
                        onChange={(e) =>
                          saveConfig(
                            "training_def_max_level",
                            Math.max(
                              1,
                              Math.min(999, parseInt(e.target.value) || 1),
                            ),
                          )
                        }
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
                      <FormLabel color="gray.300" fontSize="xs">
                        ⚡ Geschicklichkeit - Max Level
                      </FormLabel>
                      <Input
                        type="number"
                        value={botConfig.training_agi_max_level}
                        onChange={(e) =>
                          saveConfig(
                            "training_agi_max_level",
                            Math.max(
                              1,
                              Math.min(999, parseInt(e.target.value) || 1),
                            ),
                          )
                        }
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
                      isDisabled={isSaving("training_autodrink_enabled")}
                      onChange={(e) =>
                        saveConfig(
                          "training_autodrink_enabled",
                          e.target.checked,
                        )
                      }
                    />
                  </HStack>
                  <Collapse
                    in={botConfig.training_autodrink_enabled}
                    animateOpacity
                  >
                    <FormControl>
                      <FormLabel
                        color="gray.300"
                        fontWeight="medium"
                        fontSize="sm"
                      >
                        Ziel-Promille
                      </FormLabel>
                      <HStack gap={2}>
                        <Input
                          type="number"
                          step="0.1"
                          value={botConfig.training_target_promille}
                          onChange={(e) =>
                            saveConfig(
                              "training_target_promille",
                              Math.max(
                                2.0,
                                Math.min(
                                  4.0,
                                  parseFloat(e.target.value) || 3.5,
                                ),
                              ),
                            )
                          }
                          min={2.0}
                          max={4.0}
                          size="md"
                          bg="gray.700"
                          border="1px solid"
                          borderColor="whiteAlpha.300"
                          color="white"
                        />
                        <Text color="gray.400" fontSize="sm">
                          ‰
                        </Text>
                      </HStack>
                    </FormControl>
                  </Collapse>
                </Box>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Pause zwischen Weiterbildungen
                  </FormLabel>
                  <Input
                    type="number"
                    value={botConfig.training_pause_minutes}
                    onChange={(e) =>
                      saveConfig(
                        "training_pause_minutes",
                        parseInt(e.target.value) || 1,
                      )
                    }
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

          <Box>
            <HStack
              justify="space-between"
              p={3}
              bg="whiteAlpha.50"
              borderRadius="md"
              cursor="pointer"
              onClick={() => setFightExpanded(!fightExpanded)}
              _hover={{ bg: "whiteAlpha.100" }}
              transition="background 0.2s"
            >
              <HStack gap={3}>
                <Icon
                  as={fightExpanded ? FiChevronDown : FiChevronRight}
                  color="teal.400"
                  boxSize={5}
                />
                <Text color="gray.200" fontWeight="medium" fontSize="md">
                  ⚔️ Kämpfen
                </Text>
              </HStack>
              <Switch
                size="lg"
                colorScheme="teal"
                isChecked={botConfig.fight_enabled}
                isDisabled={isSaving("fight_enabled")}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => {
                  e.stopPropagation();
                  saveConfig("fight_enabled", e.target.checked);
                }}
              />
            </HStack>

            <Collapse
              in={fightExpanded && botConfig.fight_enabled}
              animateOpacity
            >
              <VStack align="stretch" gap={4} mt={4} pl={8}>
                <Box
                  p={3}
                  bg="red.900"
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="red.400"
                >
                  <Text color="red.200" fontSize="sm" mb={2}>
                    ⚠️ <strong>Wichtiger Hinweis:</strong> Kämpfe können riskant
                    sein. Aktiviere diese Funktion nur, wenn du die Risiken
                    verstehst.
                  </Text>
                  <Text color="red.200" fontSize="sm">
                    Der Bot greift automatisch den schwächsten verfügbaren
                    Gegner an. Stelle sicher, dass dein Charakter stark genug
                    ist, um zu gewinnen.
                  </Text>
                </Box>

                <FormControl>
                  <FormLabel color="gray.300" fontWeight="medium" fontSize="sm">
                    Pause zwischen Kämpfen
                  </FormLabel>
                  <Input
                    type="number"
                    value={botConfig.fight_pause_minutes}
                    onChange={(e) =>
                      saveConfig(
                        "fight_pause_minutes",
                        Math.max(
                          1,
                          Math.min(60, parseInt(e.target.value) || 1),
                        ),
                      )
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
                </FormControl>

                <Box
                  p={3}
                  bg="whiteAlpha.50"
                  borderRadius="md"
                  borderLeft="3px solid"
                  borderColor="orange.400"
                >
                  <HStack justify="space-between" mb={3}>
                    <HStack gap={2}>
                      <Text color="gray.200" fontWeight="medium" fontSize="sm">
                        🔄 Automatisch abwechseln
                      </Text>
                      <Text color="gray.400" fontSize="xs">
                        (Kampf ↔ Flaschen sammeln)
                      </Text>
                    </HStack>
                    <Switch
                      size="md"
                      colorScheme="orange"
                      isChecked={botConfig.rotation_enabled}
                      isDisabled={
                        isSaving("rotation_enabled") ||
                        !botConfig.fight_enabled ||
                        !botConfig.bottles_enabled
                      }
                      onChange={(e) => {
                        if (
                          !botConfig.fight_enabled ||
                          !botConfig.bottles_enabled
                        ) {
                          alert(
                            "Bitte aktiviere sowohl Kämpfen als auch Flaschen sammeln, um die Rotation zu nutzen.",
                          );
                          return;
                        }
                        saveConfig("rotation_enabled", e.target.checked);
                      }}
                    />
                  </HStack>
                  <Collapse in={botConfig.rotation_enabled} animateOpacity>
                    <FormControl>
                      <FormLabel color="gray.300" fontSize="sm">
                        Beginnen mit
                      </FormLabel>
                      <Select
                        value={botConfig.rotation_start_with}
                        onChange={(e) =>
                          saveConfig("rotation_start_with", e.target.value)
                        }
                        size="sm"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="whiteAlpha.300"
                        color="white"
                        _hover={{ borderColor: "orange.400" }}
                      >
                        <option value="fight">⚔️ Kampf</option>
                        <option value="bottles">🍾 Flaschen sammeln</option>
                      </Select>
                    </FormControl>
                  </Collapse>
                  <Text color="gray.400" fontSize="xs" mt={2}>
                    {!botConfig.fight_enabled || !botConfig.bottles_enabled
                      ? "Aktiviere Kampf und Flaschen sammeln, um die Rotation nutzen zu können."
                      : "Der Bot wechselt automatisch zwischen Kampf und Flaschen sammeln."}
                  </Text>
                </Box>
              </VStack>
            </Collapse>
          </Box>
        </VStack>
      </DashboardCard>

      <DashboardCard title="Allgemeine Einstellungen" icon={FiSettings}>
        <VStack align="stretch" gap={4}>
          <FormControl>
            <FormLabel color="gray.300" fontWeight="medium">
              Stadt
            </FormLabel>
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
            />
          </FormControl>
        </VStack>
      </DashboardCard>

      <Box py={4} textAlign="center">
        <Text fontSize="sm" color="gray.500">
          ✨ Einstellungen werden automatisch gespeichert
        </Text>
        {savingKeys.size > 0 && <Spinner size="sm" color="teal.400" mt={2} />}
      </Box>
    </VStack>
  );
};
