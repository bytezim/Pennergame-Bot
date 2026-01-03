# Development Guide

This guide helps you quickly set up and develop the PennerBot project, which consists of:
- **Python Backend** (FastAPI server)
- **React Frontend** (Vite + TypeScript + Chakra UI)

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- Git
- Windows 10/11

### 1. First Time Setup
```bash
# Clone and navigate to the project
git clone <your-repo-url>
cd penner

# Install all dependencies (Python + Node.js)
.\manage.ps1 setup
```

### 2. Start Development Environment
```bash
# Start both backend and frontend
.\manage.ps1 dev
```

This will open two new terminal windows:
- **Backend**: http://127.0.0.1:8000 (API docs at /docs)
- **Frontend**: http://localhost:1420

## Development Commands

### PowerShell Management Script (`manage.ps1`)
```powershell
# Full development environment (recommended)
.\manage.ps1 dev

# Individual services
.\manage.ps1 backend   # Start only Python backend
.\manage.ps1 frontend  # Start only React frontend

# Build and maintenance
.\manage.ps1 build     # Build frontend for production
.\manage.ps1 test      # Run Python tests
.\manage.ps1 format    # Format Python code (black + isort)
.\manage.ps1 clean     # Clean all build artifacts
.\manage.ps1 setup     # Install/update dependencies

# Windows Binary Build
.\manage.ps1 build-setup     # Install PyInstaller (one-time)
.\manage.ps1 windows-build   # Create PennerBot.exe
```


## Manual Development (Alternative)

### Backend Development
```bash
# Install Python dependencies
python -m pip install -e ".[dev]"

# Start FastAPI development server
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Development
```bash
# Navigate to web directory
cd web

# Install Node.js dependencies
npm install

# Start Vite development server
npm run dev
```

## Project Structure

```
penner/
├── src/                 # Python backend source
│   ├── core.py         # Main bot logic
│   ├── db.py           # Database operations
│   ├── models.py       # Data models
│   └── ...
├── web/                # React frontend
│   ├── src/            # React source code
│   ├── dist/           # Production build
│   └── package.json
├── server.py           # FastAPI server entry point
├── launcher.py         # Windows EXE entry point
├── pyproject.toml      # Python project configuration
├── manage.ps1          # Management script (PowerShell)
├── BUILD.md            # Windows binary build guide
└── README.md
```

## Development Workflow

1. **Start Development**: `.\manage.ps1 dev`
2. **Make Changes**: Edit files in `src/` (Python) or `web/src/` (React)
3. **Auto-Reload**: Both servers automatically reload on file changes
4. **Test**: `.\manage.ps1 test`
5. **Format Code**: `.\manage.ps1 format`
6. **Build Frontend**: `.\manage.ps1 build`
7. **Build Windows EXE**: `.\manage.ps1 windows-build` (see BUILD.md)

## API Documentation

When the backend is running, you can access:
- **API Docs**: http://127.0.0.1:8000/docs (Swagger UI)
- **ReDoc**: http://127.0.0.1:8000/redoc
- **OpenAPI JSON**: http://127.0.0.1:8000/openapi.json

## Frontend Development

The frontend is a React application with:
- **TypeScript** for type safety
- **Vite** for fast development and building
- **Tauri** for desktop app packaging

### Key Frontend Commands
```bash
cd web

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Build Tauri desktop app
npm run tauri build
```

## Troubleshooting

### Port Conflicts
- Backend runs on port 8000
- Frontend runs on port 1420
- Change ports in the scripts if needed

### Python Environment Issues
```bash
# Ensure you're using the right Python
python --version

# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall
```

### Node.js Issues
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
cd web
rm -rf node_modules
npm install
```

### CORS Issues
The FastAPI server includes CORS middleware for development. If you encounter CORS issues, check the settings in `server.py`.

## Production Deployment

### Backend
```bash
# Install production dependencies
pip install -e .

# Run with production ASGI server
uvicorn server:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd web

# Build for production
npm run build

# Files will be in web/dist/
```

### Windows Binary (Single EXE)
```bash
# One-time setup
.\manage.ps1 build-setup

# Build Windows executable
.\manage.ps1 windows-build

# Executable will be in dist/PennerBot.exe
# See BUILD.md for detailed build options
```

# Executable will be in web/src-tauri/target/release/
```

## Contributing

1. Use `.\setup.ps1 format` before committing
2. Run `.\setup.ps1 test` to ensure tests pass
3. Follow the existing code style
4. Update this README if you add new features

## Need Help?

Run `.\setup.ps1 help` or `setup.bat help` to see all available commands.