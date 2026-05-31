# DiscordAccountBackup

`DiscordAccountBackup` is a Windows-first Python CLI/TUI project with dependency bootstrapping built in.

## Requirements

- Python 3.10+
- Windows PowerShell / Command Prompt

## Quick Start (Windows)

```bat
run.bat
```

`run.bat` will:
1. Request administrator privileges.
2. Detect `.venv\Scripts\python.exe` or fall back to `python`.
3. Install dependencies from `requirements.txt`.
4. Launch `main.py`.

## Run From Source

Direct runs also perform dependency checks and auto-install missing packages when possible:

```powershell
python main.py --help
python main.py
```

## CLI Usage

```powershell
python main.py backup --help
python main.py restore --help
python main.py tokens
python main.py startup-add --help
python main.py startup-remove
```

## Project Layout

- `main.py`: entrypoint, runtime dependency bootstrap, CLI/TUI dispatch
- `run.bat`: elevated Windows launcher
- `config.yml`: runtime settings
- `requirements.txt`: Python dependencies
- `discord_backup/`: app modules (CLI, TUI, HTTP client, config, models, startup helpers)
