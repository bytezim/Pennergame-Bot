# PennerBot Management Script

param(
    [string]$Action = "help",
    [switch]$Background,
    [switch]$Clean,
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"

# -----------------------
# Helper: colored output
function Write-ColoredOutput {
    param([string]$Message, [string]$Color = "White")
    switch ($Color) {
        "Red" { Write-Host $Message -ForegroundColor Red }
        "Green" { Write-Host $Message -ForegroundColor Green }
        "Yellow" { Write-Host $Message -ForegroundColor Yellow }
        "Blue" { Write-Host $Message -ForegroundColor Blue }
        "Cyan" { Write-Host $Message -ForegroundColor Cyan }
        default { Write-Host $Message }
    }
}

# -----------------------
# All functions (unchanged logic, slightly cleaned)
function Show-Help {
    Write-ColoredOutput "PennerBot Management Script" "Blue"
    Write-ColoredOutput "===========================" "Blue"
    Write-Host ""
    Write-ColoredOutput "Usage: .\manage.ps1 [ACTION]" "Yellow"
    Write-Host ""
    Write-ColoredOutput "Available Actions:" "Green"
    Write-Host "  setup         - Install all dependencies (Python venv + Node.js + Web Server)"
    Write-Host "  backend       - Start Python FastAPI backend only"
    Write-Host "  frontend      - Start React frontend only"
    Write-Host "  dev           - Start both backend and frontend (development mode)"
    Write-Host "  webserver     - Start Python web server for production build"
    Write-Host "  build         - Build the frontend for production"
    Write-Host "  build-setup   - Install PyInstaller for Windows binary builds"
    Write-Host "  windows-build - Create Windows GUI EXE (backend + frontend)"
    Write-Host "  clean         - Clean all build artifacts and dependencies"
    Write-Host "  test          - Run Python tests"
    Write-Host "  format        - Format Python code with black and isort"
    Write-Host "  venv          - Create/recreate Python virtual environment"
    Write-Host "  help          - Show this help message"
    Write-Host ""
    Write-ColoredOutput "Examples:" "Yellow"
    Write-Host "  .\manage.ps1 setup                    # First time setup"
    Write-Host "  .\manage.ps1 dev                      # Start development environment"
    Write-Host "  .\manage.ps1 build-setup              # Install build tools (once)"
    Write-Host "  .\manage.ps1 windows-build            # Create Windows EXE"
    Write-Host "  .\manage.ps1 windows-build -Clean     # Clean build from scratch"
    Write-Host ""
    Write-ColoredOutput "Windows Build:" "Cyan"
        Write-Host "  1. .\manage.ps1 build-setup           # Install PyInstaller"
        Write-Host "  2. .\manage.ps1 windows-build         # Create PennerBot GUI exe"
        Write-Host "  3. .\dist\PennerBot.exe               # Run the GUI application"
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-Winget {
    if (-not (Test-Command "winget")) {
        Write-ColoredOutput "✗ winget not found! Please install App Installer from Microsoft Store." "Red"
        Write-ColoredOutput "https://www.microsoft.com/p/app-installer/9nblggh4nns1" "Cyan"
        Write-ColoredOutput "Alternatively, update Windows to the latest version." "Cyan"
        exit 1
    }
}

function Install-WithWinget {
    param(
        [string]$PackageId,
        [string]$DisplayName,
        [string]$TestCommand = "",
        [string]$AdditionalArgs = ""
    )
    
    Test-Winget
    
    Write-ColoredOutput "Installing $DisplayName with winget..." "Yellow"
    Write-ColoredOutput "Package ID: $PackageId" "Cyan"
    
    if ($AdditionalArgs) {
        winget install --id $PackageId --accept-package-agreements --accept-source-agreements $AdditionalArgs
    } else {
        winget install --id $PackageId --accept-package-agreements --accept-source-agreements
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "✓ $DisplayName installed successfully!" "Green"
    } elseif ($LASTEXITCODE -eq -1978335189) {
        Write-ColoredOutput "✓ $DisplayName already installed!" "Green"
    } else {
        Write-ColoredOutput "⚠ $DisplayName installation completed with code: $LASTEXITCODE" "Yellow"
        Write-ColoredOutput "Continuing with setup..." "Cyan"
    }
    
    # Refresh PATH environment variable
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Install-Python {
    Write-ColoredOutput "Checking for Python..." "Blue"
    
    if (Test-Command "python") {
        $pythonVersion = python --version 2>&1
        Write-ColoredOutput "✓ Python found: $pythonVersion" "Green"
        return
    }
    
    Write-ColoredOutput "Python not found. Installing Python 3.12..." "Yellow"
    Install-WithWinget -PackageId "Python.Python.3.12" -DisplayName "Python 3.12" -TestCommand "python"
    
    # Verify installation
    Start-Sleep -Seconds 2
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (Test-Command "python") {
        $pythonVersion = python --version 2>&1
        Write-ColoredOutput "✓ Python installed successfully: $pythonVersion" "Green"
    } else {
        Write-ColoredOutput "⚠ Python command not found after installation. You may need to restart your terminal." "Yellow"
        Write-ColoredOutput "Attempting to continue..." "Cyan"
    }
}

function Install-NodeJS {
    Write-ColoredOutput "Checking for Node.js..." "Blue"
    
    if (Test-Command "node") {
        $nodeVersion = node --version 2>&1
        Write-ColoredOutput "✓ Node.js found: $nodeVersion" "Green"
        return
    }
    
    Write-ColoredOutput "Node.js not found. Installing Node.js 20 LTS..." "Yellow"
    Install-WithWinget -PackageId "OpenJS.NodeJS.LTS" -DisplayName "Node.js 20 LTS" -TestCommand "node"
    
    # Verify installation
    Start-Sleep -Seconds 2
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (Test-Command "node") {
        $nodeVersion = node --version 2>&1
        Write-ColoredOutput "✓ Node.js installed successfully: $nodeVersion" "Green"
    } else {
        Write-ColoredOutput "⚠ Node.js command not found after installation. You may need to restart your terminal." "Yellow"
        Write-ColoredOutput "Attempting to continue..." "Cyan"
    }
}

function Install-Git {
    Write-ColoredOutput "Checking for Git..." "Blue"
    
    if (Test-Command "git") {
        $gitVersion = git --version 2>&1
        Write-ColoredOutput "✓ Git found: $gitVersion" "Green"
        return
    }
    
    Write-ColoredOutput "Git not found. Installing Git..." "Yellow"
    Install-WithWinget -PackageId "Git.Git" -DisplayName "Git" -TestCommand "git"
    
    # Verify installation
    Start-Sleep -Seconds 2
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (Test-Command "git") {
        $gitVersion = git --version 2>&1
        Write-ColoredOutput "✓ Git installed successfully: $gitVersion" "Green"
    } else {
        Write-ColoredOutput "⚠ Git command not found after installation. You may need to restart your terminal." "Yellow"
    }
}

function Install-VisualCppBuildTools {
    Write-ColoredOutput "Checking for Microsoft Visual C++ Build Tools..." "Blue"
    
    Test-Winget
    
    Write-ColoredOutput "Installing Visual C++ Build Tools with winget..." "Yellow"
    Write-ColoredOutput "This may take several minutes..." "Cyan"
    
    # Install Visual Studio Build Tools 2022 with C++ workload
    winget install --id Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "✓ Visual C++ Build Tools installed successfully!" "Green"
    } elseif ($LASTEXITCODE -eq -1978335189) {
        Write-ColoredOutput "✓ Visual C++ Build Tools already installed!" "Green"
    } else {
        Write-ColoredOutput "⚠ Build Tools installation completed with code: $LASTEXITCODE" "Yellow"
        Write-ColoredOutput "Continuing with setup..." "Cyan"
    }
}

$VENV_PATH = "venv"
$VENV_PYTHON = "$VENV_PATH\Scripts\python.exe"
$VENV_ACTIVATE = "$VENV_PATH\Scripts\Activate.ps1"

function New-VirtualEnvironment {
    Write-ColoredOutput "Creating Python virtual environment..." "Blue"
    if (Test-Path $VENV_PATH) {
        Write-ColoredOutput "Virtual environment already exists. Removing old one..." "Yellow"
        Remove-Item -Recurse -Force $VENV_PATH
    }
    Write-Host "Creating virtual environment with: python -m venv $VENV_PATH"
    python -m venv $VENV_PATH
    if (-not (Test-Path $VENV_ACTIVATE)) {
        Write-ColoredOutput "Failed to create virtual environment!" "Red"
        Write-Host "Please check if Python is correctly installiert and accessible."
        exit 1
    }
    Write-ColoredOutput "Virtual environment created successfully!" "Green"
}

function Install-PythonPackages {
    Write-ColoredOutput "Installing Python dependencies in virtual environment..." "Yellow"
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment Python not found!" "Red"
        exit 1
    }
    Write-Host "Using Python: $VENV_PYTHON"
    Write-Host "Upgrading pip..."
    & $VENV_PYTHON -m pip install --upgrade pip
    if ($LASTEXITCODE -ne 0) {
        Write-ColoredOutput "Failed to upgrade pip!" "Red"
        exit 1
    }
    Write-Host "Installing project dependencies..."
    & $VENV_PYTHON -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        Write-ColoredOutput "Failed to install Python packages!" "Red"
        exit 1
    }
    
    # Install web server dependencies
    Write-Host "Installing web server dependencies..."
    if (Test-Path "web\requirements.txt") {
        & $VENV_PYTHON -m pip install -r "web\requirements.txt"
        if ($LASTEXITCODE -ne 0) {
            Write-ColoredOutput "Warning: Failed to install web server dependencies!" "Yellow"
        } else {
            Write-ColoredOutput "Web server dependencies installed!" "Green"
        }
    }
    
    Write-ColoredOutput "Python packages installed successfully!" "Green"
}

function Install-Dependencies {
    Write-ColoredOutput "Setting up development environment..." "Blue"
    Write-ColoredOutput "==========================================" "Blue"
    Write-Host ""
    
    # Check and install all required tools with winget
    Write-ColoredOutput "Step 1/5: Checking and installing system dependencies..." "Cyan"
    Install-Python
    Install-NodeJS
    Install-Git
    Install-VisualCppBuildTools
    
    Write-Host ""
    Write-ColoredOutput "Step 2/5: Creating Python virtual environment..." "Cyan"
    # Create virtual environment and install packages
    New-VirtualEnvironment
    
    Write-Host ""
    Write-ColoredOutput "Step 3/5: Installing Python packages..." "Cyan"
    Install-PythonPackages
    
    Write-Host ""
    Write-ColoredOutput "Step 4/5: Installing Node.js dependencies..." "Cyan"
    # Install Node.js dependencies
    Push-Location "web"
    try {
        npm install
        if ($LASTEXITCODE -ne 0) {
            Write-ColoredOutput "Failed to install Node.js packages!" "Red"
            exit 1
        }
        Write-ColoredOutput "✓ Node.js packages installed successfully!" "Green"
    }
    finally {
        Pop-Location
    }
    
    Write-Host ""
    Write-ColoredOutput "Step 5/5: Verifying installation..." "Cyan"
    Write-Host "✓ Python: $(python --version 2>&1)"
    Write-Host "✓ Node.js: $(node --version 2>&1)"
    Write-Host "✓ npm: $(npm --version 2>&1)"
    if (Test-Command "git") {
        Write-Host "✓ Git: $(git --version 2>&1)"
    }
    
    Write-Host ""
    Write-ColoredOutput "==========================================" "Blue"
    Write-ColoredOutput "✓ Setup complete!" "Green"
    Write-ColoredOutput "==========================================" "Blue"
    Write-Host ""
    Write-ColoredOutput "Virtual environment created at: $VENV_PATH" "Cyan"
    Write-ColoredOutput "You can now run: .\manage.ps1 dev" "Green"
    Write-Host ""
    Write-ColoredOutput "Note: If commands are not found, please restart your terminal or run:" "Yellow"
    Write-ColoredOutput "  `$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')" "Yellow"
}

function Start-Backend {
    Write-ColoredOutput "Starting Python FastAPI backend..." "Blue"
    Write-ColoredOutput "Backend will be available at: http://127.0.0.1:8000" "Yellow"
    Write-ColoredOutput "API docs available at: http://127.0.0.1:8000/docs" "Yellow"
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    Write-ColoredOutput "Using virtual environment..." "Green"
    & $VENV_PYTHON -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
}

function Start-Frontend {
    Write-ColoredOutput "Starting React frontend..." "Blue"
    Write-ColoredOutput "Frontend will be available at: http://localhost:1420" "Yellow"
    Push-Location "web"
    try {
        npm run dev
    }
    finally {
        Pop-Location
    }
}

function Start-Development {
    Write-ColoredOutput "Starting full development environment..." "Blue"
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    $backendCmd = "cd '$PWD'; Write-Host 'Starting Backend...' -ForegroundColor Green; & '$VENV_PYTHON' -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
    Start-Sleep -Seconds 2
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\web'; Write-Host 'Starting Frontend...' -ForegroundColor Green; npm run dev"
    Write-ColoredOutput "Development environment started!" "Green"
    Write-ColoredOutput "Backend: http://127.0.0.1:8000" "Yellow"
    Write-ColoredOutput "Frontend: http://localhost:1420" "Yellow"
    Write-ColoredOutput "API Docs: http://127.0.0.1:8000/docs" "Yellow"
}

function Build-Production {
    Write-ColoredOutput "Building frontend for production..." "Blue"
    Push-Location "web"
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) {
            Write-ColoredOutput "Failed to build frontend!" "Red"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    Write-ColoredOutput "Build complete! Check web/dist/ folder" "Green"
}

function Start-WebServer {
    Write-ColoredOutput "Starting Python web server for production build..." "Blue"
    
    # Check if build exists
    if (-not (Test-Path "web\dist")) {
        Write-ColoredOutput "Production build not found! Building first..." "Yellow"
        Build-Production
    }
    
    # Check if venv exists
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    
    # Check if aiohttp is installed
    $aiohttp = & $VENV_PYTHON -c "import aiohttp" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-ColoredOutput "Installing web server dependencies..." "Yellow"
        & $VENV_PYTHON -m pip install -r "web\requirements.txt"
    }
    
    Write-ColoredOutput "Web Server: http://127.0.0.1:1420" "Yellow"
    Write-ColoredOutput "Backend API: http://127.0.0.1:8000" "Yellow"
    Write-ColoredOutput "" "White"
    Write-ColoredOutput "Make sure the backend is running!" "Cyan"
    Write-ColoredOutput "Press Ctrl+C to stop the server" "Cyan"
    
    Push-Location "web"
    try {
        & $VENV_PYTHON serve.py
    }
    finally {
        Pop-Location
    }
}

function Remove-AllArtifacts {
    Write-ColoredOutput "Cleaning build artifacts and dependencies..." "Yellow"
    if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
    if (Test-Path "src/__pycache__") { Remove-Item -Recurse -Force "src/__pycache__" }
    if (Test-Path "*.egg-info") { Remove-Item -Recurse -Force "*.egg-info" }
    if (Test-Path "src/*.egg-info") { Remove-Item -Recurse -Force "src/*.egg-info" }
    if (Test-Path $VENV_PATH) { 
        Write-ColoredOutput "Removing virtual environment..." "Yellow"
        Remove-Item -Recurse -Force $VENV_PATH 
    }
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
    if (Test-Path "web/node_modules") { Remove-Item -Recurse -Force "web/node_modules" }
    if (Test-Path "web/dist") { Remove-Item -Recurse -Force "web/dist" }
    if (Test-Path "web/build") { Remove-Item -Recurse -Force "web/build" }
    #if (Test-Path "web/package-lock.json") { Remove-Item -Force "web/package-lock.json" }
    if (Test-Path "htmlcov") { Remove-Item -Recurse -Force "htmlcov" }
    if (Test-Path ".pytest_cache") { Remove-Item -Recurse -Force ".pytest_cache" }
    
    Write-ColoredOutput "Cleanup complete!" "Green"
}

function Invoke-Tests {
    Write-ColoredOutput "Running Python tests..." "Blue"
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    & $VENV_PYTHON -m pytest test.py -v
}

function Format-PythonCode {
    Write-ColoredOutput "Formatting Python code..." "Blue"
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    & $VENV_PYTHON -m black .
    & $VENV_PYTHON -m isort .
    Write-ColoredOutput "Code formatting complete!" "Green"
}

function Install-BuildTools {
    Write-ColoredOutput "Installing PyInstaller for Windows builds..." "Blue"
    
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    
    Write-ColoredOutput "Installing PyInstaller..." "Yellow"
    & $VENV_PYTHON -m pip install pyinstaller
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColoredOutput "✓ PyInstaller installed successfully!" "Green"
        Write-ColoredOutput "" "White"
        Write-ColoredOutput "You can now build with: .\manage.ps1 windows-build" "Cyan"
    } else {
        Write-ColoredOutput "Failed to install PyInstaller!" "Red"
        exit 1
    }
}

function Build-WindowsBinary {
    param(
        [switch]$Clean,
        [switch]$SkipFrontendBuild
    )
    
    Write-ColoredOutput ("=" * 60) "Cyan"
    Write-ColoredOutput "🏗️  Building PennerBot Windows GUI Binary" "Yellow"
    Write-ColoredOutput ("=" * 60) "Cyan"
    Write-Host ""
    
    # Check if venv exists
    if (-not (Test-Path $VENV_PYTHON)) {
        Write-ColoredOutput "Virtual environment not found! Run '.\manage.ps1 setup' first." "Red"
        exit 1
    }
    
    # Check if PyInstaller is installed
    $pyinstaller = & $VENV_PYTHON -c "import PyInstaller" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-ColoredOutput "PyInstaller not found! Installing..." "Yellow"
        Install-BuildTools
    }
    
    # Clean old builds
    if ($Clean) {
        Write-ColoredOutput "🧹 Cleaning old builds..." "Yellow"
        if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
        if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
        Write-ColoredOutput "✓ Clean complete" "Green"
        Write-Host ""
    }
    
    # Build Frontend
    if (-not $SkipFrontendBuild) {
        Write-ColoredOutput "⚛️  Building Frontend..." "Cyan"
        Push-Location "web"
        try {
            if (-not (Test-Path "node_modules")) {
                Write-ColoredOutput "Installing npm dependencies..." "Yellow"
                npm install
                if ($LASTEXITCODE -ne 0) {
                    Write-ColoredOutput "Failed to install npm dependencies!" "Red"
                    exit 1
                }
            }
            
            Write-ColoredOutput "Creating production build..." "Yellow"
            npm run build
            
            if ($LASTEXITCODE -ne 0) {
                Write-ColoredOutput "Frontend build failed!" "Red"
                exit 1
            }
            
            Write-ColoredOutput "✓ Frontend built successfully" "Green"
            Write-Host ""
        }
        finally {
            Pop-Location
        }
    } else {
        Write-ColoredOutput "⏭️  Skipping frontend build" "Yellow"
    }
    
    # Check if frontend build exists
    if (-not (Test-Path "web\dist\index.html")) {
        Write-ColoredOutput "Frontend build not found!" "Red"
        Write-ColoredOutput "Run without -SkipFrontendBuild or build manually:" "Yellow"
        Write-ColoredOutput "  cd web; npm run build" "Yellow"
        exit 1
    }
    
    # Build with PyInstaller
    Write-ColoredOutput "🔨 Building executable with PyInstaller..." "Cyan"
    Write-ColoredOutput "This may take 2-4 minutes..." "Yellow"
    Write-Host ""
    
    & $VENV_PYTHON -m PyInstaller pennerbot.spec --clean
    
    if ($LASTEXITCODE -ne 0) {
        Write-ColoredOutput "Build failed!" "Red"
        Write-Host ""
        Write-ColoredOutput "Try a clean build: .\manage.ps1 windows-build -Clean" "Yellow"
        exit 1
    }
    
    Write-Host ""
    Write-ColoredOutput ("=" * 60) "Green"
    Write-ColoredOutput "✅ Build Complete!" "Green"
    Write-ColoredOutput ("=" * 60) "Green"
    Write-Host ""
    Write-ColoredOutput "📍 Executable location: " -NoNewline "Cyan"
    Write-ColoredOutput "dist\PennerBot.exe" "Yellow"
    Write-Host ""
    Write-ColoredOutput "🚀 Run with: " -NoNewline "Cyan"
    Write-ColoredOutput ".\dist\PennerBot.exe" "Yellow"
    Write-Host ""
    
    # Calculate file size
    if (Test-Path "dist\PennerBot.exe") {
        $exeSize = (Get-Item "dist\PennerBot.exe").Length / 1MB
        Write-ColoredOutput "📊 File size: " -NoNewline "Cyan"
        Write-ColoredOutput ("{0:N2} MB" -f $exeSize) "Yellow"
        Write-Host ""
        Write-ColoredOutput "💡 Tip: See BUILD.md for more options and troubleshooting" "Cyan"
    }
}

# -----------------------
# Fix for positional parameters & robustness:
# If the caller used positional args (.\script.ps1 setup) PowerShell *sometimes* doesn't bind -Action.
# So we fallback to $args[0] if present.
if ((-not $PSBoundParameters.ContainsKey('Action') -or [string]::IsNullOrEmpty($Action)) -and $args.Count -gt 0) {
    $Action = $args[0]
}

# Normalise and run
$Action = if ($null -eq $Action) { "help" } else { $Action.ToLower() }

switch ($Action) {
    "setup" { Install-Dependencies }
    "backend" { Start-Backend }
    "frontend" { Start-Frontend }
    "dev" { Start-Development }
    "webserver" { Start-WebServer }
    "build" { Build-Production }
    "build-setup" { Install-BuildTools }
    "windows-build" { 
        $buildParams = @{}
        if ($PSBoundParameters.ContainsKey('Clean')) { $buildParams['Clean'] = $true }
        if ($PSBoundParameters.ContainsKey('SkipFrontendBuild')) { $buildParams['SkipFrontendBuild'] = $true }
        Build-WindowsBinary @buildParams
    }
    "clean" { Remove-AllArtifacts }
    "test" { Invoke-Tests }
    "format" { Format-PythonCode }
    "venv" { New-VirtualEnvironment }
    "help" { Show-Help }
    default {
        Write-ColoredOutput "Unknown action: $Action" "Red"
        Show-Help
        exit 1
    }
}
