# C Drive Cleaner

Windows desktop utility for reclaiming C drive space by scanning and cleaning common cache and temporary file locations.

## Features

- Scan common cleanup targets and estimate reclaimable space
- Select exactly which targets to clean
- Show a running log for skipped files, permission issues, and progress
- Uses only the Python standard library

## Cleanup targets

- User temp folder
- Windows temp folder
- Windows Update download cache
- Prefetch cache
- Thumbnail cache
- Crash dumps
- Windows Error Reporting cache
- Recycle Bin

## Run

```powershell
python app.py
```

Or double-click `start_cleaner.bat`.
