# 📦 PennerBot

<div align="center">

![PennerBot](/doc/Screenshot.png?raw=true "PennerBot")

**Ein moderner Pennergame-Automatisierungsbot mit FastAPI & React**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3+-blue.svg)](https://typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-5.0+-purple.svg)](https://vitejs.dev)
[![Tauri](https://img.shields.io/badge/Tauri-2.0+-orange.svg)](https://tauri.app)
[![Chakra UI](https://img.shields.io/badge/Chakra%20UI-2.8+-teal.svg)](https://chakra-ui.com)
[![SQLite](https://img.shields.io/badge/SQLite-3.0+-blue.svg)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://docker.com)

**🎯 Automatisierung für Pennergame.de - Browser-Bot mit Desktop-Interface**

**Current version:** 0.0.4 — defaults updated (bottles/autosell/autodrink/training)

</div>

---

## 🎯 Überblick

PennerBot ist eine **vollständige Desktop-Anwendung** für die Automatisierung von Pennergame.de-Aktivitäten. Das Projekt kombiniert ein robustes Python-Backend (FastAPI) mit einem modernen React-Frontend.

### 🌟 Hauptfunktionen
- 🎮 **Browser-Automatisierung** für Pennergame.de
- 💻 **Native Desktop-App** (Windows .exe) ohne Browser-Installation
- 🌐 **Modernes Web-Dashboard** mit Echtzeit-Updates
- 📊 **Responsive Dark-Theme UI** mit Chakra UI
- 💾 **SQLite-Datenbank** für lokale Datenspeicherung
- 🐳 **Docker-Support** für einfache Deployment
-  **Developer-friendly** mit TypeScript & Hot-Reload

### 🛠️ Technologie-Stack

#### Backend
- **FastAPI** - Moderne Python Web-API
- **SQLAlchemy** - ORM für Datenbankzugriffe
- **BeautifulSoup4** - HTML-Parsing für Web-Scraping
- **httpx** - Async HTTP-Client
- **APScheduler** - Task-Scheduling
- **aiohttp** - Asynchrone Netzwerk-Bibliothek

#### Frontend & Desktop
- **React 18** - UI-Framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Ultra-schneller Build-Tool
- **Tauri 2.0** - Native Desktop-App Framework
- **Chakra UI** - Komponenten-Bibliothek
- **Framer Motion** - Animationen
- **React Icons** - Icon-Bibliothek
- **Recharts** - Datenvisualisierung

#### Development & Deployment
- **Python 3.11+** - Programmiersprache
- **Node.js 20+** - JavaScript Runtime
- **Docker** - Container-Deployment
- **PyInstaller** - EXE-Erstellung
- **SQLite** - Integrierte Datenbank

> ⚠️ **WICHTIGER HINWEIS:** Dies ist ein **Lernprojekt**

### 🌟 Aktuelle Features
- ✅ **Automatisiertes Flaschensammeln**
- ✅ **Weiterbildungen** (ATT, DEF, AGI)
- ✅ **Modernes Web-Dashboard** mit Echtzeit-Updates
- ✅ **Responsive Dark-Theme UI**
- ✅ **Lokale SQLite-Datenbank**

### 🚧 Geplante Features
- 📍 Unterstützung weiterer Städte
- 🏠 Automatisches Haustier-Streunen
- ⚔️ Kampf-Automatisierung
- 🍞 Ausnüchtern mit Brot
- 🛒 Automatischer Nachkauf
- ❓❓❓

![Dashboard](/doc/Screenshot_Dash.png?raw=true "Dashboard")
![Settings](/doc/Screenshot_Settings.png?raw=true "Settings")
![Statistics](/doc/Screenshot_Stats.png?raw=true "Statistics")
![Tasks](/doc/Screenshot_Tasks.png?raw=true "Tasks")
![Debug](/doc/Screenshot_Debug.png?raw=true "Debug")

---

## 🚀 Schnellstart

### Option 1: Windows EXE (Empfohlen) ⚡

**Der einfachste Weg:**

1. 📥 Lade `PennerBot.exe` von [Releases](../../releases) herunter
2. 🖱️ Doppelklick auf `PennerBot.exe`
3. 🌐 Browser öffnet automatisch - **Fertig!** 🎉

**Was passiert:**
- 🔧 Backend-Server startet auf `http://127.0.0.1:8000`
- 🎨 Frontend-Server startet auf `http://127.0.0.1:1420`
- 🌐 Browser öffnet automatisch die Benutzeroberfläche
- 💾 Datenbank `pennergame.db` wird erstellt

**Systemanforderungen:**
- 🖥️ Windows 10/11
- ✅ Keine weiteren Dependencies erforderlich!

---

### Option 2: Development Setup 👨‍💻

Für Entwickler, die das Projekt lokal aufsetzen möchten.

#### Voraussetzungen
- 🖥️ Windows 10/11 mit winget
- 🔧 **Optional**: Python 3.11+, Node.js 18+, Git (werden automatisch installiert!)

#### Automatische Installation
```powershell
# Repository klonen
git clone <repo-url>
cd penner

# Installation starten
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted
.\manage.ps1 setup
```

**Das `setup` Kommando installiert automatisch:**
- ✅ Python, Node.js, Git (falls fehlend)
- ✅ Visual C++ Build Tools
- ✅ Python Virtual Environment
- ✅ Alle Python & Node.js Packages

#### Starten im Development Mode
```powershell
.\manage.ps1 dev
```

📚 **Detaillierte Entwickler-Anleitung:** [DEVELOPMENT.md](DEVELOPMENT.md)

---

## 🎮 Verwendung

### 1. Bot starten
1. 🚀 Öffne `PennerBot.exe` (oder `.\manage.ps1 dev` für Entwickler)
2. ⏳ Warte bis der Browser automatisch öffnet
3. 🔑 Gib deine Pennergame.de Zugangsdaten ein
4. ▶️ Klicke "Anmelden"

### 2. Bot-Steuerung
| Aktion | Beschreibung |
|--------|--------------|
| ▶️ **Start/Stop** | Grüner/Roter Button oben rechts |
| ⚙️ **Einstellungen** | Sidebar → "Einstellungen" |
| 📋 **Logs** | Sidebar → "Logs" |
| 📊 **Statistiken** | Sidebar → "Statistiken" |

### 3. Ausloggen
1. 👤 Klicke auf deinen Benutzernamen (oben rechts)
2. ✅ Bestätige Logout

---

## 🏗️ Selber bauen

Möchtest du die EXE selbst erstellen?

### Vorbereitung
```powershell
# Repository klonen
git clone <repo-url>
cd penner

# Dependencies installieren
.\manage.ps1 setup

# PyInstaller Setup
.\manage.ps1 build-setup
```

### Windows EXE bauen
```powershell
# Standard Build
.\manage.ps1 windows-build

# Clean Build (bei Problemen)
.\manage.ps1 windows-build -Clean

# Ergebnis finden in:
.\dist\PennerBot.exe  # ~60-100 MB
```

📖 **Detaillierte Anleitung:** [BUILD.md](BUILD.md)

---

## 📚 Dokumentation

### Benutzer-Dokumentation
| 📄 Datei | 📝 Beschreibung |
|---------|-----------------|
| [README.md](README.md) | Übersicht & Features (diese Datei) |
| [QUICK_START.md](QUICK_START.md) | Schnellstart-Anleitung |

### Entwickler-Dokumentation
| 📄 Datei | 📝 Beschreibung |
|---------|-----------------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Entwicklungs-Guide & Best Practices |
| [BUILD.md](BUILD.md) | Windows-Binary Build-Anleitung |

---

## 🔧 Troubleshooting

### ❌ EXE startet nicht
- 🛡️ **Windows Defender**: Ausnahme für die EXE hinzufügen
- 🔌 **Port belegt**: Andere Instanzen beenden

### ❌ Backend nicht erreichbar
- ⏱️ **Warte 5 Sekunden**: Backend braucht Zeit zum Starten
- 🔌 **Port 8000 belegt**: Andere Dienste auf Port 8000 beenden

### ❌ Browser öffnet nicht
- 🌐 Manuell öffnen: `http://127.0.0.1:1420`

### ❌ Datenbank-Fehler
- 🗑️ Lösche `pennergame.db` und starte neu

---

## 🛡️ Sicherheit & Haftung

> ⚠️ **WICHTIGE SICHERHEITSHINWEISE:**
- 🔒 Zugangsdaten werden **nur lokal** in `pennergame.db` gespeichert
- 🌐 Keine Verbindung zu externen Servern (außer Pennergame.de)
- 🎓 **Nur für Bildungszwecke** gedacht
- ⚖️ Nutzung auf eigene Gefahr
- 🚫 Keine Haftung für Account-Sperrungen

---

## 🤝 Mitwirkung

Dieses Projekt ist **Open Source** und freut sich über Mitwirkende!

### Wie du helfen kannst:
1. 📝 **Erstelle ein [Issue](../../issues)** mit deinem Vorschlag
2. 🍴 **Forke das Repository** und arbeite an neuen Features
3. 📍 **Erweitere die Unterstützung** für andere Städte
4. 🔧 **Verbessere die Code-Qualität** und Dokumentation

### Aktuelle Entwicklungsbereiche:
- 📍 Unterstützung weiterer Städte
- 🛠️ Verbesserung der Fehlerbehandlung
- ⚡ Performance-Optimierung
- 🎨 Erweiterte Dashboard-Features

### 💬 Community
- 💭 **Discord**: [discord.gg/2sz9AghVAw](https://discord.gg/2sz9AghVAw)
- 🐛 **Issues**: [GitHub Issues](../../issues)

---

## 📊 Projekt-Status

| Feature | Status | Beschreibung |
|---------|--------|--------------|
| 🏗️ **Projekt-Struktur** | ✅ Fertig | FastAPI + React + SQLite |
| 🍾 **Flaschen sammeln** | ✅ Fertig | Automatisiert |
| 📚 **Weiterbildungen** | ✅ Fertig | ATT, DEF, AGI |
| 🏠 **Haustier-Streunen** | 🚧 Geplant | In Entwicklung |
| ⚔️ **Kampf-System** | 🚧 Geplant | Geplant |
---

## 📜 Lizenz

Dieses Projekt steht unter der **MIT License**.  
📄 Siehe [LICENSE](LICENSE) für Details.

---

<div align="center">

**Haftungsausschluss:**  
*Dieses Projekt ist nicht mit Pennergame.de affiliiert. Nutzung erfolgt auf eigene Verantwortung.*

[![Made with ❤️](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://github.com)

</div>
