#!/bin/bash
# PennerBot Management Script (Linux/Mac)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Venv paths
VENV_PATH="venv"
VENV_PYTHON="$VENV_PATH/bin/python"
VENV_ACTIVATE="$VENV_PATH/bin/activate"

# Helper function for colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Show help
show_help() {
    print_color "blue" "PennerBot Management Script"
    print_color "blue" "==========================="
    echo ""
    print_color "yellow" "Usage: ./manage.sh [ACTION]"
    echo ""
    print_color "green" "Available Actions:"
    echo "  setup         - Install all dependencies (Python venv + Node.js + Web Server)"
    echo "  backend       - Start Python FastAPI backend only"
    echo "  frontend      - Start React frontend only"
    echo "  dev           - Start both backend and frontend (development mode)"
    echo "  webserver     - Start Python web server for production build"
    echo "  build         - Build the frontend for production"
    echo "  build-setup   - Install PyInstaller for binary builds"
    echo "  linux-build   - Create Linux GUI AppImage/Binary (backend + frontend)"
    echo "  mac-build     - Create macOS DMG/Binary (backend + frontend)"
    echo "  clean         - Clean all build artifacts and dependencies"
    echo "  test          - Run Python tests"
    echo "  format        - Format Python code with black and isort"
    echo "  venv          - Create/recreate Python virtual environment"
    echo "  help          - Show this help message"
    echo ""
    print_color "yellow" "Examples:"
    echo "  ./manage.sh setup                    # First time setup"
    echo "  ./manage.sh dev                      # Start development environment"
    echo "  ./manage.sh build-setup              # Install build tools (once)"
    echo "  ./manage.sh linux-build              # Create Linux binary"
    echo "  ./manage.sh linux-build --clean      # Clean build from scratch"
    echo ""
    print_color "cyan" "Linux Build:"
    echo "  1. ./manage.sh build-setup           # Install PyInstaller"
    echo "  2. ./manage.sh linux-build           # Create PennerBot binary"
    echo "  3. ./dist/PennerBot                  # Run the GUI application"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Create virtual environment
new_venv() {
    print_color "blue" "Creating Python virtual environment..."
    if [ -d "$VENV_PATH" ]; then
        print_color "yellow" "Virtual environment already exists. Removing old one..."
        rm -rf "$VENV_PATH"
    fi
    python -m venv "$VENV_PATH"
    if [ ! -f "$VENV_ACTIVATE" ]; then
        print_color "red" "Failed to create virtual environment!"
        exit 1
    fi
    print_color "green" "Virtual environment created successfully!"
}

# Install Python packages
install_python_packages() {
    print_color "yellow" "Installing Python dependencies in virtual environment..."
    if [ ! -f "$VENV_PYTHON" ]; then
        print_color "red" "Virtual environment Python not found!"
        exit 1
    fi
    print_color "yellow" "Upgrading pip..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    print_color "yellow" "Installing project dependencies..."
    "$VENV_PYTHON" -m pip install -e ".[dev]"
    print_color "green" "Python packages installed successfully!"
}

# Install PyInstaller in venv
install_build_tools() {
    print_color "blue" "Installing PyInstaller for binary builds..."
    
    if [ ! -f "$VENV_PYTHON" ]; then
        print_color "red" "Virtual environment not found! Run './manage.sh setup' first."
        exit 1
    fi
    
    print_color "yellow" "Installing PyInstaller..."
    "$VENV_PYTHON" -m pip install pyinstaller pyinstaller-hooks-contrib
    
    if [ $? -eq 0 ]; then
        print_color "green" "✓ PyInstaller installed successfully!"
        echo ""
        print_color "cyan" "You can now build with: ./manage.sh linux-build or ./manage.sh mac-build"
    else
        print_color "red" "Failed to install PyInstaller!"
        exit 1
    fi
}

# Build Linux binary
build_linux_binary() {
    local clean=false
    local skip_frontend=false
    
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --clean)
                clean=true
                shift
                ;;
            --skip-frontend-build)
                skip_frontend=true
                shift
                ;;
        esac
    done
    
    print_color "cyan" "============================================================"
    print_color "yellow" "🏗️  Building PennerBot Linux GUI Binary"
    print_color "cyan" "============================================================"
    echo ""
    
    # Check if venv exists
    if [ ! -f "$VENV_PYTHON" ]; then
        print_color "red" "Virtual environment not found! Run './manage.sh setup' first."
        exit 1
    fi
    
    # Check if PyInstaller is installed
    if ! "$VENV_PYTHON" -c "import PyInstaller" 2>/dev/null; then
        print_color "yellow" "PyInstaller not found! Installing..."
        install_build_tools
    fi
    
    # Clean old builds
    if [ "$clean" = true ]; then
        print_color "yellow" "🧹 Cleaning old builds..."
        rm -rf build dist
        print_color "green" "✓ Clean complete"
        echo ""
    fi
    
    # Build Frontend
    if [ "$skip_frontend" = false ]; then
        print_color "cyan" "⚛️  Building Frontend..."
        cd web
        if [ ! -d "node_modules" ]; then
            print_color "yellow" "Installing npm dependencies..."
            npm install
        fi
        
        print_color "yellow" "Creating production build..."
        npm run build
        cd ..
        
        if [ $? -ne 0 ]; then
            print_color "red" "Frontend build failed!"
            exit 1
        fi
        
        print_color "green" "✓ Frontend built successfully"
        echo ""
    else
        print_color "yellow" "⏭️  Skipping frontend build"
    fi
    
    # Check if frontend build exists
    if [ ! -f "web/dist/index.html" ]; then
        print_color "red" "Frontend build not found!"
        print_color "yellow" "Run without --skip-frontend-build or build manually:"
        print_color "yellow" "  cd web && npm run build"
        exit 1
    fi
    
    # Build with PyInstaller
    print_color "cyan" "🔨 Building executable with PyInstaller..."
    print_color "yellow" "This may take 2-4 minutes..."
    echo ""
    
    "$VENV_PYTHON" -m PyInstaller pennerbot.spec --clean
    
    if [ $? -ne 0 ]; then
        print_color "red" "Build failed!"
        echo ""
        print_color "yellow" "Try a clean build: ./manage.sh linux-build --clean"
        exit 1
    fi
    
    echo ""
    print_color "green" "============================================================"
    print_color "green" "✅ Build Complete!"
    print_color "green" "============================================================"
    echo ""
    print_color "cyan" "📍 Executable location: "
    print_color "yellow" "dist/PennerBot"
    echo ""
    print_color "cyan" "🚀 Run with: "
    print_color "yellow" "./dist/PennerBot"
    echo ""
    
    # Calculate file size
    if [ -f "dist/PennerBot" ]; then
        exe_size=$(du -h "dist/PennerBot" | cut -f1)
        print_color "cyan" "📊 File size: "
        print_color "yellow" "$exe_size"
        echo ""
        print_color "cyan" "💡 Tip: See BUILD.md for more options and troubleshooting"
    fi
}

# Clean all artifacts
clean_artifacts() {
    print_color "yellow" "Cleaning build artifacts and dependencies..."
    rm -rf __pycache__ src/__pycache__ *.egg-info src/*.egg-info
    rm -rf build dist
    rm -rf web/node_modules web/dist web/build
    rm -rf htmlcov .pytest_cache .coverage
    print_color "green" "Cleanup complete!"
}

# Run tests
run_tests() {
    print_color "blue" "Running Python tests..."
    if [ ! -f "$VENV_PYTHON" ]; then
        print_color "red" "Virtual environment not found! Run './manage.sh setup' first."
        exit 1
    fi
    "$VENV_PYTHON" -m pytest test.py -v
}

# Format Python code
format_python_code() {
    print_color "blue" "Formatting Python code..."
    if [ ! -f "$VENV_PYTHON" ]; then
        print_color "red" "Virtual environment not found! Run './manage.sh setup' first."
        exit 1
    fi
    "$VENV_PYTHON" -m black .
    "$VENV_PYTHON" -m isort .
    print_color "green" "Code formatting complete!"
}

# Main
ACTION=${1:-help}

case $ACTION in
    setup)
        echo "Setup not implemented for Linux yet - use manage.ps1 or manual setup"
        ;;
    backend|frontend|dev|webserver|build)
        echo "This action requires Node.js/web setup. See BUILD.md"
        ;;
    build-setup)
        install_build_tools
        ;;
    linux-build)
        shift
        build_linux_binary "$@"
        ;;
    mac-build)
        echo "macOS build not implemented yet"
        ;;
    clean)
        clean_artifacts
        ;;
    test)
        run_tests
        ;;
    format)
        format_python_code
        ;;
    venv)
        new_venv
        install_python_packages
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_color "red" "Unknown action: $ACTION"
        show_help
        exit 1
        ;;
esac
