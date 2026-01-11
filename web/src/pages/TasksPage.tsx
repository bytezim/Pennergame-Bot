import { 
  VStack, 
  Text, 
  Heading, 
  Box,
  Button,
  Select,
  HStack,
  Badge,
  useToast,
  Divider,
  Icon,
  SimpleGrid,
  Progress,
  Input,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText
} from "@chakra-ui/react";
import { DashboardCard } from "../components/DashboardCard";
import { FiPackage, FiZap, FiBook } from "react-icons/fi";
import { GiBeerBottle } from "react-icons/gi";
import { useState, useEffect } from "react";
import { SkillsData, AvailableSkill, DrinksData, Drink, Status, FoodData, Food } from "../types";
import { getApiUrl } from "../utils/api";

interface TasksPageProps {
  onRefresh?: () => Promise<void>;
  status: Status | null;
}

export const TasksPage = ({ onRefresh, status }: TasksPageProps) => {
  const [timeMinutes, setTimeMinutes] = useState(10);
  const [isCollecting, setIsCollecting] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null);
  const [bottlesInfo, setBottlesInfo] = useState<any>(null);
  
  // Pfandflaschen-Inventar State
  const [bottleCount, setBottleCount] = useState<number>(0);
  const [bottlePrice, setBottlePrice] = useState<number>(0);
  const [sellAmount, setSellAmount] = useState<number>(1);
  const [isSelling, setIsSelling] = useState(false);
  
  // Konzentrationsmodus State
  const [concentrationMode, setConcentrationMode] = useState("none");
  const [isConcentrating, setIsConcentrating] = useState(false);
  const [concentrationBoost, setConcentrationBoost] = useState("0");
  const [concentrationActivity, setConcentrationActivity] = useState("Keine");
  const [isConcentrationLoading, setIsConcentrationLoading] = useState(false);
  
  // Weiterbildungs State
  const [skillsData, setSkillsData] = useState<SkillsData | null>(null);
  const [skillActionLoading, setSkillActionLoading] = useState(false);
  const [skillTimeRemaining, setSkillTimeRemaining] = useState<string>("");
  
  // Drinks State
  const [drinksData, setDrinksData] = useState<DrinksData | null>(null);
  const [drinkAmount, setDrinkAmount] = useState<{[key: string]: number}>({});
  const [isDrinkLoading, setIsDrinkLoading] = useState(false);
  
  // Food State
  const [foodData, setFoodData] = useState<FoodData | null>(null);
  const [foodAmount, setFoodAmount] = useState<{[key: string]: number}>({});
  const [isFoodLoading, setIsFoodLoading] = useState(false);
  
  const toast = useToast();

  // Auto-Update von activities via SSE
  useEffect(() => {
    if (status?.activities) {
      setIsCollecting(status.activities.bottles_running || false);
      setSecondsRemaining(status.activities.bottles_seconds_remaining || null);
    }
  }, [status?.activities]);

  // Status beim Laden prüfen
  useEffect(() => {
    checkStatusInitial();
    checkBottleInventory();
    checkConcentrationStatusInitial();
    checkSkillsStatusInitial();
    checkDrinksStatusInitial();
    checkFoodStatusInitial();
  }, []);

  // Timer Countdown
  useEffect(() => {
    if (isCollecting && secondsRemaining !== null && secondsRemaining > 0) {
      const timer = setInterval(() => {
        setSecondsRemaining(prev => prev !== null && prev > 0 ? prev - 1 : 0);
      }, 1000);
      return () => clearInterval(timer);
    }
  }, [isCollecting, secondsRemaining]);

  // Skill Timer
  useEffect(() => {
    if (skillsData?.running_skill && skillsData.running_skill.seconds_remaining > 0) {
      const interval = setInterval(() => {
        const now = Math.floor(Date.now() / 1000);
        const remaining = skillsData.running_skill!.end_timestamp - now;
        if (remaining > 0) {
          setSkillTimeRemaining(formatTimeHMS(remaining));
        } else {
          setSkillTimeRemaining("Fertig!");
          checkSkillsStatus();
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [skillsData]);

  const checkStatusInitial = async () => {
    try {
      const response = await fetch(getApiUrl("/actions/bottles/status"));
      if (response.ok) {
        const data = await response.json();
        setIsPending(data.pending);
        setIsCollecting(data.collecting);
        setSecondsRemaining(data.seconds_remaining || null);
        setBottlesInfo(data.bottles_info || null);
      }
    } catch (error) {
      console.error("Status check failed:", error);
    }
  };

  const checkConcentrationStatusInitial = async () => {
    try {
      const response = await fetch(getApiUrl("/actions/concentration/status"));
      if (response.ok) {
        const data = await response.json();
        setIsConcentrating(data.active);
        setConcentrationActivity(data.mode || "Keine");
        setConcentrationBoost(data.boost_percent || "0");
      }
    } catch (error) {
      console.error("Concentration status check failed:", error);
    }
  };

  const checkStatus = async () => {
    try {
      const response = await fetch(getApiUrl("/actions/bottles/status?force_refresh=true"));
      if (response.ok) {
        const data = await response.json();
        setIsPending(data.pending);
        setIsCollecting(data.collecting);
        setSecondsRemaining(data.seconds_remaining || null);
        setBottlesInfo(data.bottles_info || null);
      }
    } catch (error) {
      console.error("Status check failed:", error);
    }
  };

  const checkBottleInventory = async () => {
    try {
      const response = await fetch(getApiUrl("/actions/bottles/inventory"));
      if (response.ok) {
        const data = await response.json();
        setBottleCount(data.bottle_count || 0);
        setBottlePrice(data.price_cents || 0);
        setSellAmount(Math.min(1, data.bottle_count || 0));
      }
    } catch (error) {
      console.error("Bottle inventory check failed:", error);
    }
  };

  const checkSkillsStatusInitial = async () => {
    try {
      const response = await fetch(getApiUrl("/skills"));
      if (response.ok) {
        const data = await response.json();
        setSkillsData(data);
      }
    } catch (error) {
      console.error("Skills status check failed:", error);
    }
  };

  const checkSkillsStatus = async () => {
    try {
      const response = await fetch(getApiUrl("/skills"));
      if (response.ok) {
        const data = await response.json();
        setSkillsData(data);
      }
    } catch (error) {
      console.error("Skills status check failed:", error);
    }
  };

  const checkDrinksStatusInitial = async () => {
    try {
      const response = await fetch(getApiUrl("/drinks"));
      if (response.ok) {
        const data = await response.json();
        setDrinksData(data);
        // Initialisiere drinkAmount für jedes Getränk mit 1
        const initialAmounts: {[key: string]: number} = {};
        data.drinks?.forEach((drink: Drink) => {
          initialAmounts[drink.name] = 1;
        });
        setDrinkAmount(initialAmounts);
      }
    } catch (error) {
      console.error("Drinks status check failed:", error);
    }
  };

  const checkDrinksStatus = async () => {
    try {
      const response = await fetch(getApiUrl("/drinks"));
      if (response.ok) {
        const data = await response.json();
        setDrinksData(data);
      }
    } catch (error) {
      console.error("Drinks status check failed:", error);
    }
  };

  const handleCollectBottles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(getApiUrl("/actions/bottles/collect"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ time_minutes: timeMinutes })
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Erfolgreich gestartet!",
          description: data.message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        // OPTIMIERUNG: Kein checkStatus() - SSE updated automatisch + onRefresh macht refresh_status
        // Nur onRefresh für finale Synchronisation
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Aktion fehlgeschlagen",
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
      setIsLoading(false);
    }
  };

  const handleCancelBottles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(getApiUrl("/actions/bottles/cancel"), {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Abgebrochen!",
          description: data.message,
          status: "info",
          duration: 5000,
          isClosable: true,
        });
        // OPTIMIERUNG: Kein checkStatus() - SSE updated automatisch
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Abbrechen fehlgeschlagen",
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
      setIsLoading(false);
    }
  };

  const handleSellBottles = async () => {
    setIsSelling(true);
    try {
      const response = await fetch(getApiUrl("/actions/bottles/sell"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: sellAmount })
      });

      const data = await response.json();

      if (data.success) {
        // Update inventory direkt aus Response statt neuem Request
        if (data.bottles_remaining !== undefined) {
          setBottleCount(data.bottles_remaining);
        }
        if (data.current_price !== undefined) {
          setBottlePrice(data.current_price);
        }
        
        toast({
          title: "Verkauft!",
          description: data.message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        await checkStatus();
        
        // OPTIMIERUNG: Kein checkBottleInventory() mehr - Daten kommen aus Response!
        // Nur onRefresh für finale Synchronisation
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Verkauf fehlgeschlagen",
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
      setIsSelling(false);
    }
  };

  const handleEmptyCart = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(getApiUrl("/actions/bottles/empty-cart"), {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Einkaufswagen geleert!",
          description: data.message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        // OPTIMIERUNG: Keine redundanten Checks - SSE + onRefresh genügen
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Einkaufswagen leeren fehlgeschlagen",
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
      setIsLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatTimeHMS = (seconds: number): string => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const handleStartConcentration = async () => {
    setIsConcentrationLoading(true);
    try {
      const response = await fetch(getApiUrl("/actions/concentration/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: concentrationMode })
      });

      const data = await response.json();

      if (data.success) {
        // Sofort UI aktualisieren
        setIsConcentrating(true);
        
        toast({
          title: "Konzentration gestartet!",
          description: data.message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // OPTIMIERUNG: Kein checkConcentrationStatus() - SSE updated automatisch
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Konzentration konnte nicht gestartet werden",
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
      setIsConcentrationLoading(false);
    }
  };

  const handleStopConcentration = async () => {
    setIsConcentrationLoading(true);
    try {
      const response = await fetch(getApiUrl("/actions/concentration/stop"), {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (data.success) {
        // Sofort UI aktualisieren
        setIsConcentrating(false);
        
        toast({
          title: "Konzentration beendet!",
          description: data.message,
          status: "info",
          duration: 5000,
          isClosable: true,
        });
        
        // OPTIMIERUNG: Kein checkConcentrationStatus() - SSE updated automatisch
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Konzentration konnte nicht beendet werden",
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
      setIsConcentrationLoading(false);
    }
  };

  const handleStartSkill = async (skillType: "att" | "def" | "agi") => {
    setSkillActionLoading(true);
    try {
      const response = await fetch(getApiUrl("/skills/start"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill_type: skillType }),
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Weiterbildung gestartet!",
          description: data.message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        // OPTIMIERUNG: Kein checkSkillsStatus() - SSE updated automatisch
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Weiterbildung konnte nicht gestartet werden",
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
      setSkillActionLoading(false);
    }
  };

  const handleCancelSkill = async () => {
    if (!confirm("Möchtest du wirklich die Weiterbildung abbrechen?")) return;
    
    setSkillActionLoading(true);
    try {
      const response = await fetch(getApiUrl("/skills/cancel"), {
        method: "POST",
      });

      const data = await response.json();

      if (data.success) {
        toast({
          title: "Weiterbildung abgebrochen!",
          description: data.message,
          status: "info",
          duration: 5000,
          isClosable: true,
        });
        // OPTIMIERUNG: Kein checkSkillsStatus() - SSE updated automatisch
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.message || "Weiterbildung konnte nicht abgebrochen werden",
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
      setSkillActionLoading(false);
    }
  };

  const handleDrink = async (drink: Drink) => {
    const amount = drinkAmount[drink.name] || 1;
    
    setIsDrinkLoading(true);
    try {
      const response = await fetch(getApiUrl("/drinks/use"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_name: drink.name,
          item_id: drink.item_id,
          promille: drink.promille,
          amount: amount
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Aktualisiere lokalen State sofort
        setDrinksData(prev => prev ? {
          ...prev,
          current_promille: data.new_promille,
          drinks: prev.drinks.map(d => 
            d.name === drink.name 
              ? { ...d, count: Math.max(0, d.count - amount) }
              : d
          )
        } : null);
        
        toast({
          title: "Getrunken!",
          description: `${amount}x ${drink.name} getrunken. Neuer Promillewert: ${data.new_promille.toFixed(2)}‰`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // Refresh für finale Synchronisation
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.error || "Trinken fehlgeschlagen",
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
      setIsDrinkLoading(false);
    }
  };

  const handlePumpStomach = async () => {
    setIsDrinkLoading(true);
    try {
      const response = await fetch(getApiUrl("/drinks/pump"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();

      if (data.success) {
        // Aktualisiere lokalen State sofort
        setDrinksData(prev => prev ? {
          ...prev,
          current_promille: data.new_promille
        } : null);
        
        toast({
          title: "Magen ausgepumpt!",
          description: `${data.message}. Kosten: ${data.cost}. Neuer Promillewert: ${data.new_promille.toFixed(2)}‰`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // Refresh für finale Synchronisation
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.error || "Magen auspumpen fehlgeschlagen",
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
      setIsDrinkLoading(false);
    }
  };

  const checkFoodStatusInitial = async () => {
    try {
      const response = await fetch(getApiUrl("/food"));
      if (response.ok) {
        const data = await response.json();
        setFoodData(data);
        // Initialisiere foodAmount für jedes Essen mit 1
        const initialAmounts: {[key: string]: number} = {};
        data.food?.forEach((food: Food) => {
          initialAmounts[food.name] = 1;
        });
        setFoodAmount(initialAmounts);
      }
    } catch (error) {
      console.error("Food status check failed:", error);
    }
  };

  const checkFoodStatus = async () => {
    try {
      const response = await fetch(getApiUrl("/food"));
      if (response.ok) {
        const data = await response.json();
        setFoodData(data);
      }
    } catch (error) {
      console.error("Food status check failed:", error);
    }
  };

  const handleEatFood = async (food: Food) => {
    const amount = foodAmount[food.name] || 1;
    
    setIsFoodLoading(true);
    try {
      const response = await fetch(getApiUrl("/food/eat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_name: food.name,
          item_id: food.item_id,
          promille: food.promille,
          amount: amount
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Aktualisiere lokalen State sofort
        setFoodData(prev => prev ? {
          ...prev,
          current_promille: data.new_promille,
          food: prev.food.map(f => 
            f.name === food.name 
              ? { ...f, count: Math.max(0, f.count - amount) }
              : f
          )
        } : null);
        setDrinksData(prev => prev ? {
          ...prev,
          current_promille: data.new_promille
        } : null);
        
        toast({
          title: "Gegessen!",
          description: `${amount}x ${food.name} gegessen. Neuer Promillewert: ${data.new_promille.toFixed(2)}‰`,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // Refresh für finale Synchronisation
        if (onRefresh) {
          await onRefresh();
        }
      } else {
        toast({
          title: "Fehler",
          description: data.error || "Essen fehlgeschlagen",
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
      setIsFoodLoading(false);
    }
  };

  const handleSoberUp = async () => {
    setIsFoodLoading(true);
    try {
      const response = await fetch(getApiUrl("/food/sober"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const data = await response.json();

      if (data.success) {
        // Aktualisiere lokalen State sofort
        setFoodData(prev => prev ? {
          ...prev,
          current_promille: data.current_promille
        } : null);
        setDrinksData(prev => prev ? {
          ...prev,
          current_promille: data.current_promille
        } : null);
        
        const message = data.ate 
          ? `Gegessen: ${data.message}. Neuer Promillewert: ${data.current_promille.toFixed(2)}‰`
          : data.message;
        
        toast({
          title: "Ausnüchtern abgeschlossen!",
          description: message,
          status: "success",
          duration: 5000,
          isClosable: true,
        });
        
        // Refresh für finale Synchronisation (inkl. aktualisierter Inventare)
        if (onRefresh) {
          await onRefresh();
        }
        // Aktualisiere Food-Inventar
        await checkFoodStatus();
      } else {
        toast({
          title: "Fehler",
          description: data.error || "Ausnüchtern fehlgeschlagen",
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
      setIsFoodLoading(false);
    }
  };

  const getSkillProgressPercent = (): number => {
    if (!skillsData?.running_skill) return 0;
    const total = skillsData.running_skill.end_timestamp - skillsData.running_skill.start_timestamp;
    const elapsed = Math.floor(Date.now() / 1000) - skillsData.running_skill.start_timestamp;
    return Math.min(100, Math.max(0, (elapsed / total) * 100));
  };

  const renderSkillCard = (skill: AvailableSkill) => {
    const isRunning = skillsData?.running_skill?.skill_type === skill.skill_type;
    const skillNames: Record<string, string> = {
      att: "🗡️",
      def: "🛡️",
      agi: "🎯"
    };
    
    return (
      <Box 
        key={skill.skill_type} 
        p={4} 
        bg="gray.700" 
        borderRadius="md" 
        borderWidth={isRunning ? 2 : 1} 
        borderColor={isRunning ? "blue.400" : "gray.600"}
        position="relative"
      >
        <VStack align="stretch" spacing={3}>
          <HStack justify="space-between">
            <HStack>
              <Text fontSize="xl">{skillNames[skill.skill_type]}</Text>
              <Text fontWeight="bold" color="white">{skill.display_name}</Text>
            </HStack>
            <Badge colorScheme={isRunning ? "blue" : "gray"}>
              Level {skill.current_level}
              {!skill.max_level && "/∞"}
            </Badge>
          </HStack>
          
          <VStack align="stretch" spacing={1} fontSize="sm">
            <HStack justify="space-between" color="gray.300">
              <Text>Kosten:</Text>
              <Text fontWeight="semibold">{skill.next_level_cost}</Text>
            </HStack>
            <HStack justify="space-between" color="gray.300">
              <Text>Dauer:</Text>
              <Text fontWeight="semibold">{skill.duration}</Text>
            </HStack>
          </VStack>

          {!isRunning && skill.can_start && (
            <Button
              onClick={() => handleStartSkill(skill.skill_type)}
              isDisabled={skillActionLoading || !!skillsData?.running_skill}
              colorScheme="blue"
              size="sm"
              width="full"
            >
              Weiterbilden
            </Button>
          )}
          
          {isRunning && (
            <Badge colorScheme="blue" fontSize="sm" p={2} textAlign="center">
              Läuft gerade...
            </Badge>
          )}
        </VStack>
      </Box>
    );
  };

  const timeOptions = [
    { value: 60, label: "1 Stunde" },
    { value: 180, label: "3 Stunden" },
    { value: 360, label: "6 Stunden" },
    { value: 540, label: "9 Stunden" },
    { value: 720, label: "12 Stunden" }
  ];

  const concentrationModes = [
    { value: "none", label: "Keine", desc: "20% Weiterbildungsgeschwindigkeit" },
    { value: "fight", label: "Kämpfen", desc: "Normale Kampfzeiten (sonst +90min) - 15% Weiterbildungsgeschwindigkeit" },
    { value: "bottles", label: "Pfandflaschensammeln", desc: "100% Ausbeute (sonst 25%) - 10% Weiterbildungsgeschwindigkeit" }
  ];

  return (
    <VStack align="stretch" spacing={6} className="fade-in">
      <Heading size="lg" color="white">
        Bot-Aktionen
      </Heading>

      <DashboardCard title="Pfandflaschen sammeln" icon={FiPackage}>
        <VStack align="stretch" spacing={4} py={4}>
          {/* Status-Badges */}
          <HStack spacing={3}>
            {isPending && (
              <Badge colorScheme="orange" fontSize="md" px={3} py={1}>
                🛒 Einkaufswagen voll
              </Badge>
            )}
            {isCollecting && (
              <Badge colorScheme="green" fontSize="md" px={3} py={1}>
                🍾 Sammelt Flaschen...
              </Badge>
            )}
            {!isPending && !isCollecting && (
              <Badge colorScheme="gray" fontSize="md" px={3} py={1}>
                Bereit
              </Badge>
            )}
          </HStack>

          {/* Timer beim Sammeln */}
          {isCollecting && secondsRemaining !== null && (
            <Box 
              p={4} 
              bg="green.900" 
              borderRadius="md" 
              borderWidth={1} 
              borderColor="green.600"
            >
              <VStack spacing={2} align="stretch">
                <HStack justify="space-between">
                  <Text color="green.300" fontWeight="bold">
                    ⏱️ Verbleibende Zeit:
                  </Text>
                  <Text color="white" fontSize="xl" fontWeight="bold">
                    {formatTime(secondsRemaining)}
                  </Text>
                </HStack>
                <Box 
                  bg="gray.700" 
                  h="6px" 
                  borderRadius="full" 
                  overflow="hidden"
                >
                  <Box 
                    bg="green.400" 
                    h="100%" 
                    w={`${Math.max(0, Math.min(100, (secondsRemaining / (timeMinutes * 60)) * 100))}%`}
                    transition="width 1s linear"
                  />
                </Box>
              </VStack>
            </Box>
          )}

          <Divider />

          {/* Beschreibung */}
          <Box>
            <Text color="gray.300" fontSize="sm" mb={3}>
              Der Bot sammelt automatisch Pfandflaschen für die gewählte Dauer.
              Nach der Rückkehr wird der Einkaufswagen automatisch ausgeleert.
            </Text>
          </Box>

          {/* Zeit auswählen */}
          <Box>
            <Text color="gray.300" fontSize="sm" mb={2} fontWeight="semibold">
              Sammelzeit:
            </Text>
            <Select
              value={timeMinutes}
              onChange={(e) => setTimeMinutes(Number(e.target.value))}
              bg="gray.700"
              borderColor="gray.600"
              color="white"
              _hover={{ borderColor: "gray.500" }}
              size="lg"
            >
              {timeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </Select>
          </Box>

          {/* Aktions-Buttons */}
          {isCollecting ? (
            <Button
              colorScheme="red"
              size="lg"
              onClick={handleCancelBottles}
              isLoading={isLoading}
              loadingText="Breche ab..."
              width="full"
            >
              🛑 Sammeln abbrechen
            </Button>
          ) : (
            <Button
              colorScheme="green"
              size="lg"
              onClick={handleCollectBottles}
              isLoading={isLoading}
              loadingText="Starte..."
              leftIcon={<Icon as={FiPackage} />}
              width="full"
              isDisabled={isCollecting}
            >
              Flaschen sammeln starten
            </Button>
          )}

          {/* Statistiken */}
          {bottlesInfo && bottlesInfo.total_earned && (
            <Box pt={2}>
              <Text color="gray.400" fontSize="sm">
                💰 Gesamt erwirtschaftet: <Text as="span" color="green.300" fontWeight="bold">€{bottlesInfo.total_earned}</Text>
              </Text>
              {bottlesInfo.last_found && (
                <Text color="gray.400" fontSize="sm" mt={1}>
                  ✨ Letzter Fund: <Text as="span" color="purple.300" fontWeight="bold">{bottlesInfo.last_found}</Text>
                </Text>
              )}
            </Box>
          )}

          <Divider />

          {/* Pfandflaschen verkaufen Sektion */}
          <Box>
            <Text color="gray.300" fontSize="sm" fontWeight="semibold" mb={3}>
              💰 Pfandflaschen verkaufen
            </Text>
            
            <VStack align="stretch" spacing={3}>
              <HStack justify="space-between">
                <Text color="gray.400" fontSize="sm">Im Besitz:</Text>
                <Text color="white" fontWeight="bold">{bottleCount} Flaschen</Text>
              </HStack>
              
              <HStack justify="space-between">
                <Text color="gray.400" fontSize="sm">Aktueller Preis:</Text>
                <Text color="green.300" fontWeight="bold">€{(bottlePrice / 100).toFixed(2)}</Text>
              </HStack>

              {bottleCount > 0 && (
                <>
                  <HStack>
                    <Text color="gray.400" fontSize="sm">Menge:</Text>
                    <Input
                      type="number"
                      size="sm"
                      value={sellAmount}
                      onChange={(e) => setSellAmount(Math.max(1, Math.min(parseInt(e.target.value) || 1, bottleCount)))}
                      min={1}
                      max={bottleCount}
                      width="100px"
                    />
                    <Button
                      size="sm"
                      onClick={() => setSellAmount(bottleCount)}
                      variant="outline"
                      colorScheme="blue"
                    >
                      max.
                    </Button>
                  </HStack>

                  <HStack justify="space-between" bg="green.900" p={2} borderRadius="md">
                    <Text color="green.300" fontSize="sm">Erlös:</Text>
                    <Text color="white" fontWeight="bold">
                      €{((sellAmount * bottlePrice) / 100).toFixed(2)}
                    </Text>
                  </HStack>

                  <Button
                    colorScheme="green"
                    size="md"
                    onClick={handleSellBottles}
                    isLoading={isSelling}
                    loadingText="Verkaufe..."
                    width="full"
                  >
                    💰 {sellAmount} Flaschen verkaufen
                  </Button>
                </>
              )}
              
              {bottleCount === 0 && (
                <Text color="gray.500" fontSize="sm" textAlign="center" py={2}>
                  Keine Flaschen zum Verkaufen
                </Text>
              )}
            </VStack>
          </Box>

          {isPending && (
            <>
              <Divider />
              <Box>
                <Button
                  colorScheme="orange"
                  size="md"
                  onClick={handleEmptyCart}
                  isLoading={isLoading}
                  loadingText="Leere..."
                  width="full"
                  leftIcon={<Text fontSize="lg">🛒</Text>}
                >
                  Einkaufswagen leeren
                </Button>
                <Text fontSize="xs" color="orange.300" mt={2} textAlign="center">
                  Der Einkaufswagen ist voll und muss geleert werden
                </Text>
              </Box>
            </>
          )}

          {/* Status aktualisieren */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              checkStatus();
              checkBottleInventory();
            }}
            color="gray.400"
            _hover={{ color: "white" }}
          >
            Status aktualisieren
          </Button>
        </VStack>
      </DashboardCard>

      {/* Weitere Aktionen (Platzhalter) */}
      <DashboardCard title="Konzentrationsmodus" icon={FiZap}>
        <VStack align="stretch" spacing={4} py={4}>
          {/* Status-Badges */}
          <HStack spacing={3}>
            {isConcentrating ? (
              <Badge colorScheme="purple" fontSize="md" px={3} py={1}>
                🧠 Konzentriert
              </Badge>
            ) : (
              <Badge colorScheme="gray" fontSize="md" px={3} py={1}>
                Nicht aktiv
              </Badge>
            )}
            {isConcentrating && (
              <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
                +{concentrationBoost}% Boost
              </Badge>
            )}
          </HStack>

          {/* Info-Box wenn aktiv */}
          {isConcentrating && (
            <Box 
              p={4} 
              bg="purple.900" 
              borderRadius="md" 
              borderWidth={1} 
              borderColor="purple.600"
            >
              <VStack spacing={2} align="stretch">
                <HStack justify="space-between">
                  <Text color="purple.300" fontWeight="bold">
                    Weiterbildungs-Boost:
                  </Text>
                  <Text color="white" fontSize="xl" fontWeight="bold">
                    +{concentrationBoost}%
                  </Text>
                </HStack>
                <HStack justify="space-between">
                  <Text color="purple.300" fontWeight="bold">
                    Nebenbeschäftigung:
                  </Text>
                  <Text color="white" fontWeight="bold">
                    {concentrationActivity}
                  </Text>
                </HStack>
              </VStack>
            </Box>
          )}

          <Divider />

          {/* Beschreibung */}
          <Box>
            <Text color="gray.300" fontSize="sm" mb={3}>
              Der Konzentrationsmodus beschleunigt Weiterbildungen. Wähle optional eine Nebenbeschäftigung aus.
            </Text>
          </Box>

          {!isConcentrating ? (
            <>
              {/* Modus auswählen */}
              <Box>
                <Text color="gray.300" fontSize="sm" mb={2} fontWeight="semibold">
                  Nebenbeschäftigung:
                </Text>
                <Select
                  value={concentrationMode}
                  onChange={(e) => setConcentrationMode(e.target.value)}
                  bg="gray.700"
                  borderColor="gray.600"
                  color="white"
                  _hover={{ borderColor: "gray.500" }}
                  size="lg"
                >
                  {concentrationModes.map(opt => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label} - {opt.desc}
                    </option>
                  ))}
                </Select>
                <Text fontSize="xs" color="gray.500" mt={2}>
                  💡 Wähle eine Nebenbeschäftigung um Nachteile zu vermeiden
                </Text>
              </Box>

              {/* Start Button */}
              <Button
                colorScheme="purple"
                size="lg"
                onClick={handleStartConcentration}
                isLoading={isConcentrationLoading}
                loadingText="Starte..."
                leftIcon={<Icon as={FiZap} />}
                width="full"
              >
                Konzentration starten
              </Button>
            </>
          ) : (
            <>
              {/* Stop Button */}
              <Button
                colorScheme="red"
                size="lg"
                onClick={handleStopConcentration}
                isLoading={isConcentrationLoading}
                loadingText="Beende..."
                width="full"
              >
                🛑 Konzentration beenden
              </Button>

              <Box p={3} bg="orange.900" borderRadius="md" borderWidth={1} borderColor="orange.600">
                <Text fontSize="xs" color="orange.200">
                  ⚠️ Das Beenden der Konzentration bricht auch laufende Weiterbildungen ab!
                </Text>
              </Box>
            </>
          )}
        </VStack>
      </DashboardCard>

      {/* Weiterbildung */}
      <DashboardCard title="Weiterbildung (Kampfstärken)" icon={FiBook}>
        <VStack align="stretch" spacing={4} py={4}>
          {/* Laufende Weiterbildung */}
          {skillsData?.running_skill && (
            <>
              <Box 
                p={4} 
                bg="blue.900" 
                borderRadius="md" 
                borderWidth={1} 
                borderColor="blue.600"
              >
                <VStack spacing={3} align="stretch">
                  <HStack justify="space-between">
                    <VStack align="start" spacing={0}>
                      <Text color="blue.300" fontSize="sm" fontWeight="bold">
                        Läuft gerade:
                      </Text>
                      <Text color="white" fontSize="lg" fontWeight="bold">
                        {skillsData.running_skill.name} - Stufe {skillsData.running_skill.level}
                      </Text>
                    </VStack>
                    <Badge colorScheme="blue" fontSize="md" px={3} py={1}>
                      {skillTimeRemaining}
                    </Badge>
                  </HStack>
                  
                  <Box>
                    <HStack justify="space-between" mb={2}>
                      <Text color="blue.300" fontSize="sm">Fortschritt</Text>
                      <Text color="white" fontWeight="bold">{Math.round(getSkillProgressPercent())}%</Text>
                    </HStack>
                    <Progress 
                      value={getSkillProgressPercent()} 
                      colorScheme="blue" 
                      size="sm" 
                      borderRadius="full"
                    />
                  </Box>

                  <Text color="gray.300" fontSize="sm">
                    Voraussichtlich {skillsData.running_skill.expected_points} Punkte
                  </Text>

                  <Button
                    colorScheme="red"
                    size="md"
                    onClick={handleCancelSkill}
                    isLoading={skillActionLoading}
                    loadingText="Bricht ab..."
                    width="full"
                  >
                    🛑 Weiterbildung abbrechen
                  </Button>
                </VStack>
              </Box>
              <Divider />
            </>
          )}

          {/* Info-Text */}
          <Box>
            <Text color="gray.300" fontSize="sm" mb={3}>
              Trainiere Angriff, Verteidigung oder Geschicklichkeit. 
              {skillsData?.running_skill && " Du kannst nur eine Weiterbildung gleichzeitig durchführen."}
            </Text>
          </Box>

          {/* Verfügbare Weiterbildungen */}
          <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
            {skillsData?.available_skills.att && renderSkillCard(skillsData.available_skills.att)}
            {skillsData?.available_skills.def && renderSkillCard(skillsData.available_skills.def)}
            {skillsData?.available_skills.agi && renderSkillCard(skillsData.available_skills.agi)}
          </SimpleGrid>

          {/* Status aktualisieren */}
          <Button
            variant="ghost"
            size="sm"
            onClick={checkSkillsStatus}
            color="gray.400"
            _hover={{ color: "white" }}
          >
            Status aktualisieren
          </Button>
        </VStack>
      </DashboardCard>

      {/* Alkohol trinken */}
      <DashboardCard title="Promillesystem" icon={GiBeerBottle}>
        <VStack align="stretch" spacing={4}>
          <Box>
            <Text fontSize="sm" color="gray.400" mb={4}>
              Trinke Alkohol um deine Laune zu verbessern. Gute Laune verkürzt Weiterbildungen, schlechte Laune verbessert Kämpfe.
            </Text>
            
            {drinksData && (
              <Stat mb={4}>
                <StatLabel>Aktueller Promillewert</StatLabel>
                <StatNumber color={
                  drinksData.current_promille === 0 ? "red.400" :
                  drinksData.current_promille < 1.5 ? "orange.400" :
                  drinksData.current_promille < 3.0 ? "green.400" :
                  drinksData.current_promille < 3.5 ? "yellow.400" : "red.500"
                }>
                  {drinksData.current_promille.toFixed(2)}‰
                </StatNumber>
                <StatHelpText>
                  {drinksData.current_promille === 0 ? "😠 Schlechte Laune - aggressiv" :
                   drinksData.current_promille < 1.5 ? "😐 Leicht gereizt" :
                   drinksData.current_promille < 3.0 ? "😊 Gute Laune - fühlst dich wohl" :
                   drinksData.current_promille < 3.5 ? "😵 Noch geht es gut, aber übertreib es nicht!" :
                   "☠️ Lebensgefahr - Krankenhaus!"}
                </StatHelpText>
              </Stat>
            )}
            
            {drinksData && drinksData.current_promille > 0 && (
              <>
                <Button
                  size="sm"
                  colorScheme="red"
                  variant="outline"
                  onClick={handlePumpStomach}
                  isLoading={isDrinkLoading}
                  leftIcon={<Text fontSize="lg">🏥</Text>}
                  width="full"
                  mb={2}
                >
                  Magen auspumpen (€500.00)
                </Button>
                <Button
                  size="sm"
                  colorScheme="orange"
                  variant="outline"
                  onClick={handleSoberUp}
                  isLoading={isFoodLoading}
                  leftIcon={<Text fontSize="lg">🍔</Text>}
                  width="full"
                  mb={2}
                >
                  Automatisch ausnüchtern (Essen)
                </Button>
              </>
            )}
          </Box>

          <Divider />

          {drinksData && drinksData.drinks && drinksData.drinks.length > 0 ? (
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              {drinksData.drinks.map((drink) => (
                <Box
                  key={drink.name}
                  p={4}
                  bg="whiteAlpha.50"
                  borderRadius="lg"
                  borderWidth="1px"
                  borderColor="whiteAlpha.200"
                >
                  <VStack align="stretch" spacing={3}>
                    <HStack justify="space-between">
                      <Text fontWeight="bold" fontSize="lg">{drink.name}</Text>
                      <Badge colorScheme="purple">{drink.count} verfügbar</Badge>
                    </HStack>
                    
                    <Text fontSize="sm" color="gray.400">
                      Wirkung: <Text as="span" color="green.400" fontWeight="bold">+{drink.effect}‰</Text> pro Flasche
                    </Text>

                    <HStack>
                      <Text fontSize="sm" color="gray.400">Menge:</Text>
                      <Input
                        type="number"
                        size="sm"
                        width="80px"
                        min={1}
                        max={Math.min(drink.count, 100)}
                        value={drinkAmount[drink.name] || 1}
                        onChange={(e) => setDrinkAmount({
                          ...drinkAmount,
                          [drink.name]: Math.max(1, Math.min(parseInt(e.target.value) || 1, drink.count))
                        })}
                      />
                      <Button
                        size="sm"
                        colorScheme="green"
                        onClick={() => handleDrink(drink)}
                        isLoading={isDrinkLoading}
                        isDisabled={drink.count === 0}
                        leftIcon={<Icon as={GiBeerBottle} />}
                        flex={1}
                      >
                        Trinken
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              ))}
            </SimpleGrid>
          ) : (
            <Box py={8}>
              <Text color="gray.400" textAlign="center">
                Keine Getränke im Inventar. Kaufe welche im Supermarkt!
              </Text>
            </Box>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={checkDrinksStatus}
            color="gray.400"
            _hover={{ color: "white" }}
          >
            Inventar aktualisieren
          </Button>
        </VStack>
      </DashboardCard>

      {/* Essen (Promille senken) */}
      <DashboardCard title="🍔 Essen (Promille senken)" icon={FiPackage}>
        <VStack align="stretch" spacing={4}>
          <Box>
            <Text fontSize="sm" color="gray.400" mb={4}>
              Esse Nahrung um deinen Promillespiegel zu senken. Perfekt um nach dem Betrinken wieder nüchtern zu werden!
            </Text>
            
            {foodData && foodData.current_promille > 0 && (
              <Box p={3} bg="orange.900" borderRadius="md" mb={4} borderWidth={1} borderColor="orange.600">
                <VStack spacing={2}>
                  <HStack justify="space-between" width="full">
                    <Text color="orange.300" fontWeight="bold">Aktueller Promillewert:</Text>
                    <Text color="white" fontSize="lg" fontWeight="bold">
                      {foodData.current_promille.toFixed(2)}‰
                    </Text>
                  </HStack>
                  <Button
                    size="sm"
                    colorScheme="orange"
                    onClick={handleSoberUp}
                    isLoading={isFoodLoading}
                    leftIcon={<Text fontSize="lg">🍔</Text>}
                    width="full"
                  >
                    🚀 Automatisch auf 0‰ ausnüchtern
                  </Button>
                  <Text fontSize="xs" color="orange.200" textAlign="center">
                    Wählt automatisch das beste Essen basierend auf Verfügbarkeit und Effizienz
                  </Text>
                </VStack>
              </Box>
            )}
          </Box>

          <Divider />

          {foodData && foodData.food && foodData.food.length > 0 ? (
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              {foodData.food.map((food) => (
                <Box
                  key={food.name}
                  p={4}
                  bg="whiteAlpha.50"
                  borderRadius="lg"
                  borderWidth="1px"
                  borderColor="whiteAlpha.200"
                >
                  <VStack align="stretch" spacing={3}>
                    <HStack justify="space-between">
                      <Text fontWeight="bold" fontSize="lg">{food.name}</Text>
                      <Badge colorScheme="green">{food.count} verfügbar</Badge>
                    </HStack>
                    
                    <Text fontSize="sm" color="gray.400">
                      Wirkung: <Text as="span" color="orange.400" fontWeight="bold">{food.effect}‰</Text> pro Portion
                    </Text>

                    <HStack>
                      <Text fontSize="sm" color="gray.400">Menge:</Text>
                      <Input
                        type="number"
                        size="sm"
                        width="80px"
                        min={1}
                        max={Math.min(food.count, 100)}
                        value={foodAmount[food.name] || 1}
                        onChange={(e) => setFoodAmount({
                          ...foodAmount,
                          [food.name]: Math.max(1, Math.min(parseInt(e.target.value) || 1, food.count))
                        })}
                      />
                      <Button
                        size="sm"
                        colorScheme="orange"
                        onClick={() => handleEatFood(food)}
                        isLoading={isFoodLoading}
                        isDisabled={food.count === 0}
                        leftIcon={<Text fontSize="lg">🍽️</Text>}
                        flex={1}
                      >
                        Essen
                      </Button>
                    </HStack>
                  </VStack>
                </Box>
              ))}
            </SimpleGrid>
          ) : (
            <Box py={8}>
              <Text color="gray.400" textAlign="center">
                Kein Essen im Inventar. Kaufe welches im Supermarkt!
              </Text>
            </Box>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={checkFoodStatus}
            color="gray.400"
            _hover={{ color: "white" }}
          >
            Inventar aktualisieren
          </Button>
        </VStack>
      </DashboardCard>
    </VStack>
  );
};
