# Deployment

The repository is self-contained. Keep these files in the same directory:

- `zombie_killer.py`
- `zombie_tray.ps1`
- `start-zombie-killer-admin.bat`
- `requirements.txt`

Install `psutil`, then double-click the BAT file. It requests elevation through
Windows UAC and starts the PowerShell tray hidden. A session-local named mutex
prevents a second tray for the same user.

The tray's manual menu action executes one bounded `reap --yes` cycle with the
same safety gates as the continuous worker. `-Preview` can be supplied directly
to `zombie_tray.ps1` for an observation-only run.

Logs and state are stored beside the scripts and excluded by `.gitignore`.
Keep them private because command-line arguments may contain local data.
