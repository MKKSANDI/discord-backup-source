# Discord Backup

Discord Backup is a Python CLI/TUI project for collecting and restoring Discord-related backup data.

## Project structure

- `main.py`: entry point
- `run.bat`: elevated launcher for Windows
- `config.yml`: runtime options
- `discord_backup/`:
  - `cli.py`: command routing
  - `tui.py`: interactive terminal mode
  - `backup.py`: backup workflow
  - `restore.py`: restore workflow
  - `token_discovery.py`: token discovery logic
  - `config.py`, `models.py`, `http_client.py`, `identity.py`, `results.py`, `utils.py`

## Quick start

```powershell
python -m pip install -r requirements.txt
```

Run elevated on Windows:

```bat
run.bat
```

Run directly with Python:

```powershell
python main.py --help
python main.py
```

## Notes

- `run.bat` requests administrator rights before launching.
- Running with no arguments starts terminal UI mode.
- Running with arguments uses CLI mode.
