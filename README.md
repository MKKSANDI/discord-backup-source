# Discord Backup Source (Reconstructed)

This project is a reconstructed source tree from `DiscordBackup.exe` (PyInstaller bundle built on Python 3.13).

## Project status

- package/module layout has been restored
- CLI and TUI entry flow is restored
- several behavior-heavy internals remain partial/stubbed and need manual reconstruction

## Reconstruction inputs

- extracted bytecode artifacts
- symbol/constants analysis from `*_dis.txt` files
- import graph and call-site reconstruction

## Layout

- `main.py`: entry point (`TUI` when run without args, `CLI` when args exist)
- `discord_backup/` package:
  - `cli.py`: command routing
  - `tui.py`: interactive terminal UI
  - `config.py`: config loader (`config.yml`)
  - `models.py`: dataclasses for backup/restore objects
  - `backup.py`, `restore.py`: partially reconstructed service logic
  - `token_discovery.py`: partial token discovery logic
  - `http_client.py`, `identity.py`, `results.py`, `utils.py`, etc.

## Run

```powershell
cd "D:\Moved From C\Desktop\Apps\discord backup\Unpack\discord_backup_source"
python -m pip install -r requirements.txt
python main.py --help
python main.py
```

## Known gaps

- backup/restore service internals are not complete in all paths
- some token discovery and loading/progress behaviors are placeholders
- decompiler output references are retained for manual verification and reimplementation

## Goal of this repository

Preserve the recovered source in a maintainable structure so missing paths can be completed incrementally with tests and trace validation.
