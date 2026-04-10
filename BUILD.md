# 🏗️ PennerBot Build Guide

Anleitung zum Erstellen einer ausführbaren Windows-EXE mit Backend und Frontend.

## 📋 Voraussetzungen

- Windows 10/11
- Python 3.11+
- Node.js 18+
- Virtual Environment aktiviert

## 🚀 Quick Start

```powershell
# 1. Initial Setup (einmalig)
.\manage.ps1 setup

# 2. Virtual Environment aktivieren
.\venv\Scripts\Activate.ps1

# 3. Build-Dependencies installieren (einmalig)
.\manage.ps1 build-setup

# 4. Windows EXE erstellen
.\manage.ps1 windows-build

# 5. EXE ausführen
.\dist\PennerBot.exe
```

## 📦 Build-Kommandos

### Standard Build (mit Konsole)
```powershell
.\manage.ps1 windows-build
```
- Zeigt Konsolen-Fenster mit Logs
- Gut für Debugging
- Größe: ~60-100 MB

### Clean Build (empfohlen bei Problemen)
```powershell
.\manage.ps1 windows-build -Clean
```
- Löscht alte Build-Artefakte
- Erstellt Frontend neu
- Erstellt EXE neu

### Frontend-Build überspringen
```powershell
.\manage.ps1 windows-build -SkipFrontendBuild
```
- Nutzt bestehendes `web/dist/`
- Schneller für Backend-only Änderungen
- Nur wenn Frontend bereits gebaut wurde

### Windowed Build (ohne Konsole)
```powershell
# Bearbeite pennerbot.spec und setze: console=False
# Dann:
.\manage.ps1 windows-build
```

## 🔧 Build-Prozess Details

### Was passiert beim Build:

1. **Frontend Build** (`npm run build`)
   - Vite erstellt optimiertes Production-Build
   - Output: `web/dist/`
   - Minified JavaScript, CSS, Assets

2. **PyInstaller Packaging**
   - Analysiert Python-Dependencies
   - Packt Python Runtime + Packages
   - Bindet Frontend-Build ein (`web/dist`)
   - Bindet Source-Code ein (`src/`)
   - Erstellt Single-File EXE

3. **Output**
   - `dist/PennerBot.exe` - Finale ausführbare Datei
   - `build/` - Temporäre Build-Dateien (kann gelöscht werden)

### Enthaltene Komponenten:

- ✅ FastAPI Backend Server (Port 8000)
- ✅ Aiohttp Frontend Server (Port 1420)
- ✅ React Frontend (Chakra UI)
- ✅ SQLite Datenbank (wird beim ersten Start erstellt)
- ✅ Python 3.11 Runtime
- ✅ Alle Python-Dependencies

## 📁 Dateistruktur

```
PennerBot/
├── launcher.py          # Entry-Point für EXE
├── pennerbot.spec       # PyInstaller Konfiguration
├── manage.ps1           # Management Script
├── BUILD.md             # Diese Datei
├── dist/
│   └── PennerBot.exe    # ← Fertige Windows-Binary
├── build/               # Temp-Dateien (kann gelöscht werden)
├── web/
│   └── dist/            # Frontend Production-Build
└── src/                 # Backend Source-Code
```

## 🎯 Nach dem Build

### Ausführen der EXE:
```powershell
.\dist\PennerBot.exe
```

### Was passiert beim Start:
1. Backend-Server startet auf `http://127.0.0.1:8000`
2. Frontend-Server startet auf `http://127.0.0.1:1420`
3. Browser öffnet automatisch `http://127.0.0.1:1420`
4. SQLite-Datenbank wird erstellt (falls nicht vorhanden)

### Datenbank-Location:
- Im gleichen Ordner wie `PennerBot.exe`
- Datei: `pennergame.db`


### Verteilung:
Die EXE kann eigenständig verteilt werden:
- ✅ Keine Python-Installation nötig
- ✅ Keine Dependencies installieren
- ✅ Einfach doppelklicken zum Starten
- ⚠️ Beim ersten Start wird `pennergame.db` erstellt

## 🐛 Troubleshooting

### Build schlägt fehl - "Frontend build not found"
```powershell
# Frontend manuell bauen:
cd web
npm install
npm run build
cd ..
```

### Build schlägt fehl - "PyInstaller not found"
```powershell
# Sicherstellen dass venv aktiviert ist:
.\venv\Scripts\Activate.ps1

# Build-Setup erneut ausführen:
.\manage.ps1 build-setup
```

### EXE startet nicht - "Import Error"
```powershell
# Clean Build durchführen:
.\manage.ps1 windows-build -Clean
```

### EXE zu groß (>150 MB)
Normal! Enthält:
- Python Runtime (~30 MB)
- Alle Dependencies (~40-60 MB)
- Frontend Build (~10-20 MB)

Optimierungen:
- UPX ist bereits aktiviert (komprimiert EXE)
- Single-File ist praktischer als kleinere Verteilung

### Browser öffnet nicht automatisch
- Manuell öffnen: `http://127.0.0.1:1420`
- Oder in `launcher.py` Browser-Auto-Open deaktivieren

### Port bereits in Verwendung
- Backend (8000) oder Frontend (1420) läuft bereits
- Andere Instanz beenden oder Ports in `launcher.py` ändern

## 🔄 Update-Workflow

```powershell
# 1. Code-Änderungen machen (Backend oder Frontend)

# 2. Tests durchführen
.\manage.ps1 dev

# 3. Neue EXE erstellen
.\manage.ps1 windows-build -Clean

# 4. Testen
.\dist\PennerBot.exe
```

## 📊 Build-Zeiten (ca.)

- Frontend Build: 10-30 Sekunden
- PyInstaller Analysis: 30-60 Sekunden
- PyInstaller Packaging: 30-90 Sekunden
- **Gesamt: 2-4 Minuten**

## 🎨 Icon anpassen

1. Icon-Datei erstellen (`.ico`, 256x256)
2. In `web/public/favicon.ico` speichern
3. In `pennerbot.spec` aktivieren:
   ```python
   icon='web/public/favicon.ico',
   ```
4. Neu bauen

## 🚀 Erweiterte Optionen

### Console-Window verstecken
In `pennerbot.spec` ändern:
```python
console=False,  # Kein Konsolen-Fenster
```

### Mehrere Dateien statt Single-File
In `pennerbot.spec` ändern:
```python
exe = EXE(
    pyz,
    a.scripts,
    # Kommentiere folgende Zeilen aus:
    # a.binaries,
    # a.zipfiles,
    # a.datas,
    exclude_binaries=True,  # Hinzufügen
    ...
)

# Füge hinzu:
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='PennerBot'
)
```

### Debug-Build (für Fehlersuche)
In `pennerbot.spec` ändern:
```python
debug=True,
console=True,
```

## ✅ Checkliste vor Release

- [ ] Frontend Production-Build getestet
- [ ] Backend API-Tests erfolgreich
- [ ] Clean Build durchgeführt
- [ ] EXE auf sauberem System getestet
- [ ] Datenbank-Migration funktioniert
- [ ] Browser öffnet automatisch
- [ ] Alle Features funktional
- [ ] Icon gesetzt (optional)
- [ ] README.md aktualisiert

## 📝 Notizen

- EXE ist **nicht portable** zwischen Systemen (Windows-only)
- Datenbank (`pennergame.db`) bleibt im Arbeitsverzeichnis
- Logs gehen nach STDOUT (Konsole oder Datei umleiten)
- Temporäre Dateien in `%TEMP%` während der Laufzeit
