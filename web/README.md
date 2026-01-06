# PennerBot Frontend (Tauri + React + Vite)

This is the desktop frontend for PennerBot, built with Tauri 2, React, and Vite.

## Prerequisites (Windows)

- Rust/Cargo (required for `npm run tauri dev/build`)
  - Install once, then open a new terminal:
  - `winget install --id Rustlang.Rustup -e`
  - `rustup default stable`
  - `cargo --version`
- Node.js (recommended: v22.12.0 or newer 22.x LTS)
  - Install NVM for Windows: `winget install CoreyButler.NVMforWindows`
  - New terminal, then:
    - `nvm install 22.12.0`
    - `nvm use 22.12.0`
    - `node -v`
    - `npm -v`

## Install

From this `web/` folder:

```
# optional clean
Remove-Item -Recurse -Force .\node_modules; Remove-Item -Force .\package-lock.json

npm install
```

## Run

- Dev (Desktop):
```
npm run tauri dev
```
- Dev (Web only):
```
npm run dev
```

Backend must be running on http://127.0.0.1:8000. The Vite dev server proxies `/api` to the backend (see `vite.config.ts`).

## Troubleshooting (Windows, EPERM with esbuild)

- Error like `EPERM spawnSync ... esbuild.exe` during `npm install` typically means Windows blocked executing binaries inside `node_modules`.
- Common causes:
  - Install location is a network or mapped drive (e.g., `T:`). Windows policies often block executing binaries there.
  - Antivirus/Defender is locking files during install.

Workarounds:

1) Prefer a local drive path (e.g., `C:\dev\pypennergamebot\web`). Move/copy the project there and run `npm install` again.
2) Temporarily disable AV scanning or add an exclusion for this folder.
3) Run terminal as Administrator for the clean and install steps.
4) Ensure Node 22.12+ is active to satisfy Vite's engine requirement and avoid extra warnings.

If you move the project, adjust your paths accordingly. Tauri works best from a local drive.# Tauri + React + Typescript

This template should help get you started developing with Tauri, React and Typescript in Vite.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
