// Type Definitions for PennerBot Dashboard

export interface ActivityStatus {
  skill_running: boolean;
  skill_seconds_remaining: number | null;
  fight_running: boolean;
  fight_seconds_remaining: number | null;
  bottles_running: boolean;
  bottles_seconds_remaining: number | null;
}

export interface Status {
  logged_in: boolean;
  bot_running: boolean;
  activities?: ActivityStatus;
}

export interface Penner {
  username: string;
  rank: number;
  points: number;
  money: string;
  promille: number;
  att: number;
  deff: number;
  cleanliness: number;
  container_filled_percent: number;
  container_donors: number;
  container_donations_today: number;
  container_total_donations: number;
  // 24h Trends
  rank_trend?: string;
  points_trend?: string;
  money_trend?: string;
  // City information
  city?: string;
  city_url?: string;
}

export interface Log {
  id: number | string;
  timestamp: string;
  message: string;
  level?: string;
}

export interface Plunder {
  id: number;
  name: string;
  count: number;
  value?: number;
}

export interface RunningSkill {
  name: string;
  skill_type: "att" | "def" | "agi";
  level: number;
  seconds_remaining: number;
  end_timestamp: number;
  start_timestamp: number;
  expected_points: number;
}

export interface AvailableSkill {
  display_name: string;
  skill_type: "att" | "def" | "agi";
  current_level: number;
  max_level: number | null;
  next_level_cost: string;
  duration: string;
  can_start: boolean;
}

export interface SkillsData {
  running_skill: RunningSkill | null;
  available_skills: {
    att?: AvailableSkill;
    def?: AvailableSkill;
    agi?: AvailableSkill;
  };
}

export interface Drink {
  name: string;
  item_id: string;
  count: number;
  promille: string;
  effect: number;
}

export interface DrinksData {
  drinks: Drink[];
  current_promille: number;
}

export interface Food {
  name: string;
  item_id: string;
  count: number;
  promille: string;
  effect: number;
}

export interface FoodData {
  food: Food[];
  current_promille: number;
}

export interface BotConfig {
  is_running: boolean;
  bottles_enabled: boolean;
  bottles_duration_minutes: number;
  bottles_pause_minutes: number;
  bottles_autosell_enabled: boolean;
  bottles_min_price: number;
  last_started?: string;
  last_stopped?: string;
}

export type PageType = 
  | "dashboard" 
  | "settings"
  | "stats" 
  | "tasks" 
  | "inventory" 
  | "howto" 
  | "debug";
