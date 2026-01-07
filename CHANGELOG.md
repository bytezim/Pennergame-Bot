# Changelog

## [0.0.3] - 2026-01-07

### Added
- manage.sh: Added Linux/Mac management script for PyInstaller builds
- pyproject.toml: Added PyInstaller and pyinstaller-hooks-contrib as dev dependencies

### Changed
- manage.ps1: Updated to install pyinstaller-hooks-contrib for better hook support
- pennerbot.spec: Added hidden imports for jaraco modules, excluded pkg_resources/jaraco to fix runtime errors
- gui_launcher.py: Improved GUI launcher functionality
- server.py: Enhanced server implementation

## [0.0.2] - 2026-01-06

### Added
- CHANGELOG.md: Added changelog for tracking project changes
- gui_launcher.py: Added GUI launcher for easier application startup

### Removed
- Makefile: Removed outdated build configuration

### Changed
- launcher.py: Updated launcher script for improved functionality
- manage.ps1: Modified PowerShell management script
- pennerbot.spec: Updated PyInstaller spec file
- pyproject.toml: Updated project version and dependencies
- server.py: Enhanced server implementation
- src/constants.py: Updated constants
- src/core.py: Improved core logic
- src/db.py: Database optimizations
- src/models.py: Model updates
- src/parse.py: Parsing improvements
- web/serve.py: Web server updates
- web/src/App.tsx: Frontend improvements
- web/src/pages/LoginPage.tsx: Login page enhancements

## [0.0.1] - 2026-01-03

### Added
- Initial release with comprehensive Pennergame automation bot
- Web-based dashboard for monitoring and configuration
- Automated bottle collection system with configurable pricing
- Training automation for character skills (attack, defense, agility)
- Auto-sell functionality for inventory management
- Real-time event logging and monitoring
- Database integration for persistent data storage
- RESTful API endpoints for frontend communication
- Server-Sent Events (SSE) for real-time updates
- Docker containerization support
- Windows executable build configuration

### Technical Features
- Modular architecture with separate core, tasks, and web components
- SQLAlchemy ORM with SQLite database support
- APScheduler for task scheduling and management
- HTTPX and AioHTTP for web scraping and API calls
- FastAPI web framework for backend services
- TypeScript React frontend with Vite build system
- Comprehensive error handling and logging
- Security measures and input validation
- Performance monitoring and optimization
- Query optimization for database operations
- Cache management for improved performance

### Configuration
- Configurable bottle collection timing and pricing
- Adjustable training parameters and skill priorities
- Customizable promille limits for safe gameplay
- Log retention and cleanup settings
- Cache TTL configuration for different data types
- Database connection and retention settings
- CORS and security configuration
- UI display limits and monitoring settings

---

## Version History

- **[0.0.3]** - 2026-01-07: Added manage.sh script, PyInstaller improvements with pyinstaller-hooks-contrib, fixed runtime errors
- **[0.0.2]** - 2026-01-06: Minor updates and improvements, added GUI launcher, removed Makefile
- **[0.0.1]** - 2026-01-03: Initial release with full automation features

## Support

For questions or issues regarding changes, please refer to the project's
[GitHub repository](https://github.com/bytezim/Pennergame-Bot) or
[documentation](https://github.com/bytezim/Pennergame-Bot/blob/main/README.md).

---

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
