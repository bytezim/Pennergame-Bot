# 🚀 PennerBot - Quick Start Guide

Schnellstart für End-User und Entwickler.

## Variante 1: Windows EXE (für End-User) 🪟

### Download & Start
1. Lade `PennerBot.exe` herunter
2. Doppelklick auf `PennerBot.exe`
3. Browser öffnet automatisch
4. Fertig! 🎉

**Was passiert:**
- Backend startet auf Port 8000
- Frontend startet auf Port 1420
- Browser öffnet `http://127.0.0.1:1420`
- Datenbank wird erstellt (`pennergame.db`)

---

## Variante 2: Development Setup (für Entwickler) 👨‍💻

### Voraussetzungen
- Python 3.11+
- Node.js 18+
- Git

### 1. Setup Dependencies

```powershell
# Repository klonen
git clone <repo-url>
cd penner

# Dependencies installieren (einmalig)
.\manage.ps1 setup
```

### 2. Start Development Environment

```powershell
# Beide Server starten (Backend + Frontend)
.\manage.ps1 dev
```

Dies öffnet:
- **Backend**: http://127.0.0.1:8000 (FastAPI server)
- **Frontend**: http://localhost:1420 (React dev server mit Hot-Reload)
- **API Docs**: http://127.0.0.1:8000/docs (Swagger UI)

---

## 🎮 Verfügbare Kommandos

### Management Script (`manage.ps1`)

```powershell
.\manage.ps1 setup         # Dependencies installieren
.\manage.ps1 dev           # Entwicklungsumgebung starten
.\manage.ps1 backend       # Nur Backend starten
.\manage.ps1 frontend      # Nur Frontend starten
.\manage.ps1 build         # Frontend Production-Build
.\manage.ps1 test          # Python Tests ausführen
.\manage.ps1 format        # Python Code formatieren
.\manage.ps1 clean         # Build-Artefakte löschen
.\manage.ps1 build-setup   # PyInstaller installieren
.\manage.ps1 windows-build # Windows EXE erstellen
.\manage.ps1 help          # Hilfe anzeigen
```

### VS Code Integration

- **Ctrl+Shift+P** → "Tasks: Run Task" → Choose from available tasks
- **F5** → Start debugging (multiple debug configurations available)
- Auto-formatting and import organization on save

### Alternative: VS Code Tasks

1. Open Command Palette (`Ctrl+Shift+P`)
2. Type "Tasks: Run Task"
3. Choose from:
   - "Setup: Install All Dependencies"
   - "Dev: Start Full Environment"
   - "Backend: Start Python FastAPI"
   - "Frontend: Start React Dev Server"
   - And many more...

## 🏗️ Project Structure Overview

```
pypennergamebot/
├── 🐍 Python Backend
│   ├── server.py           # FastAPI server
│   └── src/               # Backend source code
├── ⚛️ React Frontend
│   └── web/               # React + TypeScript + Tauri
├── 🛠️ Development Tools
│   ├── manage.ps1      # Main development script
│   ├── manage.ps1      # Batch alternative (same script)
│   └── .vscode/           # VS Code configuration
└── 📖 Documentation
    ├── DEVELOPMENT.md      # Detailed dev guide
    └── README.md           # Project overview
```

## 🔄 Typical Development Workflow

1. **Start**: `.\manage.ps1 dev`
2. **Code**: Edit files in `src/` (Python) or `web/src/` (React)
3. **Auto-reload**: Both servers reload automatically
4. **Test**: `.\manage.ps1 test`
5. **Format**: `.\manage.ps1 format` (before committing)
6. **Build**: `.\manage.ps1 build` (for production)

## 🎨 Features

### Backend (Python + FastAPI)

- ✅ Auto-reload on file changes
- ✅ Interactive API documentation (Swagger UI)
- ✅ CORS enabled for frontend communication
- ✅ Debug configurations ready
- ✅ Automatic code formatting (Black + isort)
- ✅ Test runner integration

### Frontend (React + TypeScript + Vite)

- ✅ Hot module replacement (HMR)
- ✅ TypeScript support
- ✅ Tauri desktop app capability
- ✅ Fast build system (Vite)
- ✅ Modern React 19

### Development Experience

- ✅ One-command setup and start
- ✅ Parallel backend/frontend development
- ✅ VS Code task integration
- ✅ Debug configurations
- ✅ Auto-formatting on save
- ✅ Comprehensive error handling

## 🚨 Troubleshooting

### PowerShell Execution Policy

If you get execution policy errors:

```powershell
# Unblock the script (one time only)
Unblock-File -Path ".\manage.ps1"
```

### Port Conflicts

- Backend uses port 8000
- Frontend uses port 1420
- Modify the scripts if these ports are in use

### Python Environment Issues

```powershell
# Check Python version
python --version

# Reinstall dependencies
.\manage.ps1 setup
```

### Node.js Issues

```powershell
# Check Node version
node --version

# Clean and reinstall
.\manage.ps1 clean
.\manage.ps1 setup
```

## 🎯 Next Steps

1. Run `.\manage.ps1 setup` to install dependencies
2. Run `.\manage.ps1 dev` to start development
3. Open browser to http://localhost:1420 for frontend
4. Open http://127.0.0.1:8000/docs for API documentation
5. Start coding! 🎉


## 📚 More Information

- Read `DEVELOPMENT.md` for detailed development guide
- Check VS Code tasks (Ctrl+Shift+P → "Tasks")
- Use `.\manage.ps1 help` for command reference

Happy coding! 🚀
