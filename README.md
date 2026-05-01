# Starloco Launcher

Launcher for Dofus Retro. Handles login, local zaap server, and game client launch.

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Lint](https://img.shields.io/badge/lint-ruff-orange)
![Stars](https://img.shields.io/github/stars/tiboitel/starloco-launcher)

## Overview

The launcher authenticates against a remote auth API and passes a game token to the Dofus client via a local TCP zaap. The client then connects directly to the game server using that token.

Key capabilities:
- Credential login via remote auth API
- Local zaap server (127.0.0.1) for token handoff to the game client
- Game client spawning with autologin arguments
- Configurable game executable path
- Warm RPG-themed UI (640x480, borderless)

## Install

```bash
# Core dependencies
pip install .

# With development tools
pip install -e ".[dev]"
```

## Run

```bash
python -m src
```

Or, after installation:

```bash
python -m src
```

## Architecture

```
starloco-launcher/
src/
  api/       # Remote auth API client
  client/    # Game process spawning
  ui/        # Launcher UI (customtkinter)
  zaap/      # Local TCP zaap server (ZaapConnect protocol)
  config.py  # JSON config load/save
config/     # Runtime configuration
docs/       # Architecture, flows, backlog
```

### UI

CustomTkinter window with borderless drag support. Single card layout (640x480) with gold header.

- **Login panel**: account, password, remember me, PLAY button
- **Settings panel**: game executable selection, back navigation

### Zaap Server

TCP server on `127.0.0.1`. Implements the minimal ZaapConnect protocol:

1. Client connects and sends `connect <game_type> <version>`
2. Client sends `auth_getGameToken`
3. Zaap responds with the auth token from login
4. Connection closes

### Client Launcher

Spawns the game process with autologin arguments. Sets the local zaap port so the client can fetch its token.

## Key Flows

### Login

1. User enters credentials
2. API client POSTs to remote auth endpoint
3. Auth API returns game token
4. UI stores token, triggers game launch

### Token Handoff

1. Zaap server is already listening on `127.0.0.1`
2. Login succeeds, token stored in zaap
3. Game client spawned with zaap port argument
4. Client connects to zaap, requests token
5. Zaap sends stored token, client connects to game server

## Development

### Lint

```bash
ruff check .
ruff check . --fix
```

### Project Config

`pyproject.toml`:
- Python >= 3.10
- Dependencies: `customtkinter`
- Dev: `ruff`

### Module Interface

`src/__init__.py` re-exports the public API:

```python
from src.api import AuthResponse, login
from src.config import get, load, put, save
```

### Key Entry Points

| Component | Entry Point | Purpose |
|-----------|-------------|---------|
| UI | `src/ui/main.py` | Login window, launcher UI |
| Zaap | `src/zaap/server.py` | TCP server start/listen |
| Client | `src/client/launcher.py` | Game process spawn |
| Config | `src/config.py` | JSON load/save |
| API | `src/api/client.py` | Auth POST request |
| Package | `src/__main__.py` | `python -m src` entry point |