# PennerBot Frontend

## 📁 Projektstruktur

```
web/src/
├── components/          # Wiederverwendbare UI-Komponenten
│   ├── Sidebar.tsx      # Seitenleiste (Desktop) / Horizontal Nav (Mobile)
│   ├── TopBar.tsx       # Obere Statusleiste
│   ├── DashboardCard.tsx # Card-Wrapper für Dashboard-Elemente
│   ├── StatCard.tsx     # Statistik-Karten
│   └── index.ts         # Component Exports
│
├── pages/               # Einzelne Seiten-Komponenten
│   ├── LoginPage.tsx    # Login-Seite (Einstiegspunkt)
│   ├── DashboardPage.tsx # Haupt-Dashboard
│   ├── StatsPage.tsx    # Statistik-Übersicht
│   ├── TasksPage.tsx    # Bot-Aufgaben
│   ├── InventoryPage.tsx # Inventar
│   ├── HowToPage.tsx    # Anleitung/FAQ
│   ├── DebugPage.tsx    # Debug-Konsole
│   ├── SettingsPage.tsx # Einstellungen
│   └── index.ts         # Page Exports
│
├── types/               # TypeScript Type Definitions
│   └── index.ts         # Alle Typen (Status, Penner, Log, etc.)
│
├── utils/               # Utility-Funktionen (für später)
│
├── App.tsx              # Haupt-App mit Routing-Logik
├── App.css              # Globale Styles
└── main.tsx             # React Entry Point
```

## 🎯 Hauptfunktionen

### ✅ Login-System
- **LoginPage** wird standardmäßig angezeigt
- Nach erfolgreicher Anmeldung → Weiterleitung zum Dashboard
- Session-Persistenz über Backend-API

### 📱 Responsive Design
- **Desktop**: Vertikale Sidebar (250px) links
- **Mobile**: Horizontale Navigation unter dem Header (sticky)
- Automatische Anpassung mit Chakra UI Breakpoints

### 🧩 Modulare Komponenten
- **DashboardCard**: Wiederverwendbare Card mit Icon und Header
- **StatCard**: Statistik-Anzeige mit Icon und Trend
- **Sidebar**: Responsive Navigation
- **TopBar**: Status-Anzeige mit Login & Bot Status

## 🚀 Verwendung

### Neue Seite hinzufügen

1. Erstelle `web/src/pages/NeuePage.tsx`:
```tsx
import { VStack, Heading } from "@chakra-ui/react";

export const NeuePage = () => {
  return (
    <VStack align="stretch" spacing={6}>
      <Heading size="lg" color="white">Neue Seite</Heading>
      {/* Inhalt */}
    </VStack>
  );
};
```

2. Exportiere in `pages/index.ts`:
```tsx
export { NeuePage } from './NeuePage';
```

3. Füge Route in `App.tsx` hinzu:
```tsx
case "neuepage":
  return <NeuePage />;
```

4. Füge Menüeintrag in `Sidebar.tsx` hinzu:
```tsx
{ id: "neuepage", label: "Neue Seite", icon: FiStar }
```

### Neue Komponente erstellen

1. Erstelle `components/NeueKomponente.tsx`
2. Exportiere in `components/index.ts`
3. Importiere wo benötigt: `import { NeueKomponente } from '../components'`

## 🎨 Styling-Richtlinien

- Verwende Chakra UI Komponenten
- Nutze CSS-Klassen aus `App.css`:
  - `.fade-in` - Einblend-Animation
  - `.slide-in` - Slide-Animation
  - `.btn-glow` - Button Glow-Effekt
  - `.gradient-text` - Gradient-Text
  - `.card-hover` - Card Hover-Effekt
  - `.activity-log-item` - Log-Item Hover

- Farben aus CSS-Variablen:
  - `--accent-teal` (#38b2ac)
  - `--accent-blue` (#4299e1)
  - `--text-primary` (#f7fafc)
  - `--bg-dark` (#1a202c)

## 📦 TypeScript-Typen

Alle Typen in `types/index.ts`:
- `Status` - Login & Bot Status
- `Penner` - Spieler-Daten
- `Log` - Aktivitäts-Logs
- `PageType` - Seiten-Navigation

## 🔧 API-Integration

Alle API-Calls in den jeweiligen Seiten/Komponenten:
- `/api/status` - Login & Bot Status
- `/api/login` - Login
- `/api/bot/start` - Bot starten
- `/api/bot/stop` - Bot stoppen
- `/api/settings` - Einstellungen laden/speichern

