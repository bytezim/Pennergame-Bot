# 📦 PennerBot

⚠️ **BEISPIEL** ⚠️

Dies ist ein **Demonstrationsprojekt** für einen Pennergame-Bot. Es funktioniert derzeit **ausschließlich für die Stadt Hamburg** in Pennergame und ist nicht für den produktiven Einsatz gedacht.

![Demo](/screenshot.jpg?raw=true "Demo")

**Wer Lust hat, mit mir zusammen daran weiterzuarbeiten, soll sich per [Issue](../../issues) melden!**

---

## Download & Installation

### Option 1: Windows EXE (Empfohlen) ⚡

**Einfachster Weg:**
1. Lade `PennerBot.exe` von [Releases](../../releases) herunter
2. Doppelklick auf `PennerBot.exe`
3. Browser öffnet automatisch - Fertig! 🎉

**Was wird benötigt:**
- Windows 10/11
- Nichts weiter! (Python/Node.js **nicht** erforderlich)

**Was passiert:**
- Backend-Server startet auf http://127.0.0.1:8000
- Frontend-Server startet auf http://127.0.0.1:1420
- Browser öffnet automatisch die Benutzeroberfläche
- Datenbank `pennergame.db` wird erstellt

---

### Option 2: Development Setup 👨‍💻

Für Entwickler, die zu viel Zeit haben.

**Voraussetzungen:**
- Windows 10/11 mit winget (App Installer)
- **Optional**: Python 3.11+, Node.js 18+, Git (werden automatisch installiert!)

**Automatische Installation (Empfohlen):**
```powershell
git clone <repo-url>
cd penner
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy Unrestricted
.\manage.ps1 setup
```

Das `setup` Kommando:
- ✅ Prüft alle Dependencies (Python, Node.js, Git)
- ✅ Installiert fehlende Tools **automatisch mit winget**
- ✅ Installiert Visual C++ Build Tools
- ✅ Erstellt Python Virtual Environment
- ✅ Installiert alle Python & Node.js Packages

**Starten:**
```powershell
.\manage.ps1 dev
```

Siehe [DEVELOPMENT.md](DEVELOPMENT.md) für Details.

---

## Features

### 🤖 Bot-Automatisierung
- ✅ Automatisches Flaschen sammeln
- ⚠️ **Funktioniert nur für Hamburg in Pennergame**


### 🎨 Modern UI
- ✅ Responsive Dark-Theme Design
- ✅ Echtzeit Bot-Status
- ✅ Live-Logs
- ✅ Dashboard mit Statistiken

### ⚙️ Einstellungen
- ✅ User-Agent anpassbar
- ✅ Bot-Interval konfigurierbar
- ✅ Persistente SQLite-Datenbank

---

## Verwendung

### 1. Bot starten
1. Öffne `PennerBot.exe` (oder `.\manage.ps1 dev` für Dev-Mode)
2. Warte bis Browser öffnet
3. Gib Pennergame.de Zugangsdaten ein
4. Klicke "Anmelden"

### 2. Bot-Steuerung
- **Start/Stop**: Grüner/Roter Button oben rechts
- **Einstellungen**: Sidebar → "Einstellungen"
- **Logs**: Sidebar → "Logs"
- **Statistiken**: Sidebar → "Statistiken"

### 3. Ausloggen
- Klicke auf deinen Benutzernamen (oben rechts)
- Bestätige Logout

---

## 🤝 Mitwirkung am Demo-Projekt

Dies ist ein **Demo-Projekt** für die Automatisierung von Pennergame-Aktivitäten. Es ist **nicht für den produktiven Einsatz** gedacht und funktioniert derzeit **ausschließlich für die Stadt Hamburg**.

### Aktueller Status
- ✅ Bot-Funktionalität für Hamburg implementiert
- ✅ Web-Dashboard mit Echtzeit-Updates
- ✅ Automatisches Flaschen sammeln
- ⚠️ **Nur für Hamburg getestet und funktionsfähig**
- ⚠️ **Andere Städte werden aktuell nicht unterstützt**

### Wie du helfen kannst
Falls du Interesse hast, an diesem Projekt mitzuarbeiten:

1. **Erstelle ein [Issue](../../issues)** mit deinem Vorschlag
2. **Forke das Repository** und arbeite an neuen Features
3. **Erweitere die Unterstützung** für andere Städte
4. **Verbessere die Code-Qualität** und Dokumentation

### Aktuelle Entwicklungsbereiche
- Unterstützung für weitere Städte in Pennergame
- Verbesserung der Fehlerbehandlung
- Optimierung der Performance
- Erweiterte Dashboard-Features

---

## 🏗️ Selber bauen

Du möchtest die EXE selbst erstellen?

### Einmalige Vorbereitung
```powershell
# Repository klonen
git clone <repo-url>
cd penner

# Dependencies installieren
.\manage.ps1 setup

# PyInstaller installieren
.\manage.ps1 build-setup
```

### Windows EXE bauen
```powershell
# Standard Build
.\manage.ps1 windows-build

# Clean Build (empfohlen bei Problemen)
.\manage.ps1 windows-build -Clean

# Ergebnis
.\dist\PennerBot.exe  # Fertige EXE (~60-100 MB)
```

**Detaillierte Anleitung:** Siehe [BUILD.md](BUILD.md)

---

## Dokumentation

### 📚 Benutzer-Dokumentation
| Datei | Beschreibung |
|-------|-------------|
| [README.md](README.md) | Dieses Dokument - Übersicht & Features |
| [QUICK_START.md](QUICK_START.md) | Schnellstart für User & Entwickler |

### 👨‍💻 Entwickler-Dokumentation
| Datei | Beschreibung |
|-------|-------------|
| [DEVELOPMENT.md](DEVELOPMENT.md) | Entwicklungs-Guide & Best Practices |
| [BUILD.md](BUILD.md) | Windows-Binary Build-Anleitung |

---

## Troubleshooting

### EXE startet nicht
- **Windows Defender**: Ausnahme hinzufügen
- **Port belegt**: Andere Instanz beenden

### Backend nicht erreichbar
- **Warte 5 Sekunden**: Backend braucht Zeit zum Starten
- **Port 8000 belegt**: Andere Dienste beenden

### Browser öffnet nicht
- Manuell öffnen: http://127.0.0.1:1420

### Datenbank-Fehler
- `pennergame.db` löschen und neu starten

---

## Sicherheit & Haftung

⚠️ **Wichtig:**
- Zugangsdaten werden **nur lokal** in `pennergame.db` gespeichert
- Keine Verbindung zu externen Servern (außer Pennergame.de)
- **Nur für Bildungszwecke**
- Nutzung auf eigene Gefahr
- Keine Haftung für Account-Sperrungen

---

## Support

### Probleme melden
- [GitHub Issues](../../issues)
- Logs beifügen (Sidebar → "Debug")

### Feature-Requests
- [GitHub Issues](../../issues) mit Label "enhancement"

---

## Lizenz

MIT License - Siehe [LICENSE](LICENSE)

**Haftungsausschluss:**
Dieses Projekt ist nicht mit Pennergame.de affiliiert. Nutzung erfolgt auf eigene Verantwortung.
