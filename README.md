# MKV → Jellyfin Transcoder

A Python tool that batch-transcodes MKV files (ripped with MakeMKV) into Jellyfin-ready MP4s using HandBrakeCLI. Supports both movies and TV shows, automatically naming and organising output to match Jellyfin's expected library structure.

---

## Features

- Transcodes movies and TV shows in one run
- Outputs files in Jellyfin-compatible naming (`Show Name - S01E01.mp4`)
- Resumes safely – skips files that have already been transcoded
- Partial/failed outputs are cleaned up automatically (no corrupt files left behind)
- Runs in the background via `nohup` so a screen timeout or SSH disconnect won't kill the job
- Logs everything to `transcode.log` with timestamps
- Preset file path and preset name are configurable via environment variables (no code edits needed on other machines)

---

## Requirements

| Dependency | Notes |
|---|---|
| Python 3.10+ | Needed for `int \| None` type hints |
| HandBrake (CLI) | Must be on your `PATH` as `HandBrakeCLI` |
| A HandBrake preset | Created in the HandBrake GUI and exported as JSON |

### Installing HandBrake

**Flatpak (Linux – recommended for most distros):**
```bash
flatpak install flathub fr.handbrake.ghb
# The CLI is only accessible inside the Flatpak sandbox.
# Install the native package below if you need CLI access from the terminal.
```

**Native package (gives you HandBrakeCLI on PATH):**
```bash
# Ubuntu / Debian
sudo add-apt-repository ppa:stebbins/handbrake-releases
sudo apt update && sudo apt install handbrake-cli

# Fedora
sudo dnf install HandBrake-cli

# Arch
sudo pacman -S handbrake

# macOS (Homebrew)
brew install handbrake

# Windows
# Download the HandBrakeCLI.exe from https://handbrake.fr/downloads2.php
# and add its folder to your PATH environment variable.
```

Verify the install:
```bash
HandBrakeCLI --version
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

No Python dependencies beyond the standard library are required.

### 2. Create your HandBrake preset

1. Open the HandBrake GUI.
2. Configure your encode settings (resolution, codec, quality, audio, subtitles, etc.).
3. Go to **Presets → Add Preset**, name it (e.g. `Ripper`), and save.
4. Export the preset: **Presets → Export Presets** → save as `presets.json` anywhere convenient.

### 3. Configure the preset path

By default the script looks for your preset at:

```
~/.var/app/fr.handbrake.ghb/config/ghb/presets.json
```

If yours is in a different location, set the environment variable before running:

```bash
export HB_PRESET_FILE="/path/to/your/presets.json"
export HB_PRESET_NAME="Ripper"
```

Or pass them inline (see the Running section below).

---

## Directory structure

Place your input files inside the `Input/` folder next to `transcode.py`:

```
transcode.py
run.sh
Input/
    Movie Title (2024).mkv         ← movies go directly in Input/
    Another Movie.mkv
    Shows/
        Breaking Bad/
            Season 01/
                title_t00.mkv
                title_t01.mkv
            Season 02/
                title_t00.mkv
        The Office/
            Season 01/
                title_t00.mkv
```

Season folders must start with the word `Season` (case-insensitive). Episode files are sorted by their MakeMKV `_tNN` title number; if none is present they are sorted alphabetically.

### Output structure

After transcoding, files appear in `Output/` in Jellyfin-ready format:

```
Output/
    Movie Title (2024)/
        Movie Title (2024).mp4
    Breaking Bad/
        Season 01/
            Breaking Bad - S01E01.mp4
            Breaking Bad - S01E02.mp4
        Season 02/
            Breaking Bad - S02E01.mp4
    The Office/
        Season 01/
            The Office - S01E01.mp4
```

Processed source files are moved to `Input/Completed/` so you know what's been done without deleting the originals.

---

## Running

### Quick start (foreground)

```bash
python3 transcode.py
```

The process will stop if your terminal closes or your screen times out.

### Recommended: background with nohup (survives terminal close)

Make the wrapper script executable once:

```bash
chmod +x run.sh
```

Then run:

```bash
./run.sh
```

This launches the transcoder in the background using `nohup`. You can close your terminal, lock your screen, or disconnect an SSH session and the job will keep running.

**Monitor progress:**
```bash
tail -f transcode.log
```

**Check if it's still running:**
```bash
cat transcode.pid          # shows the PID
kill -0 $(cat transcode.pid) && echo "Running" || echo "Finished"
```

**Stop early:**
```bash
kill $(cat transcode.pid)
```

### With custom preset settings

```bash
HB_PRESET_FILE="/path/to/presets.json" HB_PRESET_NAME="MyPreset" ./run.sh
```

## Resume behaviour

If a transcode is interrupted (power cut, manual kill, etc.):

- Any partially written output file is deleted automatically (the script writes to a `.tmp.mp4` first, then renames it on success).
- On the next run the script skips any `.mp4` that already exists in `Output/` and picks up where it left off.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `HandBrakeCLI not found` | Install HandBrake (native/CLI package) and confirm `HandBrakeCLI --version` works |
| `Preset not found` error from HandBrake | Check `HB_PRESET_FILE` points to the right JSON and `HB_PRESET_NAME` matches exactly |
| Flatpak HandBrake – CLI not on PATH | Install the native `handbrake-cli` package alongside the Flatpak GUI |
| Episodes in wrong order | Ensure MakeMKV ripped files have `_tNN` in their names, or rename them so alphabetical order matches episode order |
| Show not detected | Confirm the show folder lives inside `Input/Shows/` and season folders start with `Season` |
| Script stops when screen locks | Use `./run.sh` instead of running `python3 transcode.py` directly |

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HB_PRESET_FILE` | `~/.var/app/fr.handbrake.ghb/config/ghb/presets.json` | Path to your exported HandBrake preset JSON |
| `HB_PRESET_NAME` | `Ripper` | Name of the preset to use within the JSON file |

---

## Licence

MIT – do whatever you like with it.