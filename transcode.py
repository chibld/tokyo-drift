import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "Input"
DEST_DIR = BASE_DIR / "Output"
COMP_SUBDIR = "Completed"
SHOWS_SUBDIR = "Shows"


PRESET_FILE = os.environ.get("HB_PRESET_FILE", str(Path.home() / ".var/app/fr.handbrake.ghb/config/ghb/presets.json"))
PRESET_NAME = os.environ.get("HB_PRESET_NAME", "Ripper")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "transcode.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def handbrake_cli() -> str:
    for name in ("HandBrakeCLI", "handbrakecli", "HandbrakeCLI"):
        if shutil.which(name):
            return name
    raise FileNotFoundError(
        "HandBrakeCLI not found on PATH. Install HandBrake and ensure the CLI "
        "binary is accessible."
    )


def transcode_file(src: Path, dest: Path) -> None:
    if dest.exists():
        log.info("Skipping (already exists): %s", dest)
        return

    tmp = dest.with_suffix(".tmp.mp4")
    try:
        cmd = [
            handbrake_cli(),
            "-i", str(src),
            "-o", str(tmp),
            "--preset-import-file", PRESET_FILE,
            "--preset", PRESET_NAME,
        ]
        log.info("Transcoding: %s -> %s", src.name, dest.name)
        subprocess.run(cmd, check=True)
        tmp.rename(dest)
        log.info("Done: %s", dest)
    except subprocess.CalledProcessError as exc:
        log.error("HandbrakeCLI failed (exit %s) for %s", exc.returncode, src)
        tmp.unlink(missing_ok=True)
        raise
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def season_number(dir_name: str) -> int | None:
    match = re.search(r"\d+", dir_name)
    return int(match.group()) if match else None


# def title_number(filename: str) -> int:
#     match = re.search(r"_t(\d+)\.mkv$", filename, re.IGNORECASE)
#     return int(match.group(1)) if match else 999


def file_sort_key(filename: str) -> tuple[int, int]:
    disc_match = re.search(r"disc\s*(\d+)", filename, re.IGNORECASE)
    disc = int(disc_match.group(1)) if disc_match else 0
    title_match = re.search(r"_t(\d+)\.mkv$", filename, re.IGNORECASE)
    title = int(title_match.group(1)) if title_match else 999
    return (disc, title)


def disc_number(dir_name: str) -> int:
    match = re.search(r"disc\s*(\d+)", dir_name, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def process_show(show_name: str, show_src: Path) -> None:
    season_dirs = sorted(
        d for d in show_src.iterdir()
        if d.is_dir() and d.name.lower().startswith("season")
    )

    seasons: dict[int, list[Path]] = {}
    for season_dir in season_dirs:
        snum = season_number(season_dir.name)
        if snum is None:
            log.warning("Skipping %s - couldn't parse season number", season_dir.name)
            continue
        seasons.setdefault(snum, []).append(season_dir)

    for snum in seasons:
        seasons[snum].sort(key=lambda d: disc_number(d.name))

    for snum, disc_dirs in sorted(seasons.items()):
        all_mkv_files =[]
        for disc_dir in disc_dirs:
            disc_mkvs = sorted(
                [f for f in disc_dir.iterdir() if f.suffix.lower() == ".mkv"],
                key=lambda f: file_sort_key(f.name),
            )
            all_mkv_files.extend(disc_mkvs)

        if not all_mkv_files:
            log.warning("Skipping season %d - no MKV files found", snum)
            continue

        season_str = f"Season {snum:02d}"
        dest_season = DEST_DIR / show_name / season_str
        ensure_dir(dest_season)

        for ep_num, src_file in enumerate(all_mkv_files, start=1):
            ep_str = f"S{snum:02d}E{ep_num:02d}"
            dest_name = f"{show_name} - {ep_str}.mp4"
            dest_file = dest_season / dest_name
            try:
                transcode_file(src_file, dest_file)
            except Exception:
                log.error("Failed to transcode %s - continuing with next file", src_file)

    comp_dir = SRC_DIR / COMP_SUBDIR
    ensure_dir(comp_dir)
    dest_comp = comp_dir / show_name
    if dest_comp.exists():
        shutil.rmtree(dest_comp)
    shutil.move(str(show_src), str(dest_comp))
    log.info("Moved '%s' to Completed", show_name)


def process_shows() -> None:
    shows_dir = SRC_DIR / SHOWS_SUBDIR
    if not shows_dir.is_dir():
        return

    for entry in sorted(shows_dir.iterdir()):
        if entry.is_dir():
            log.info("Processing show: %s", entry.name)
            try:
                process_show(entry.name, entry)
            except Exception:
                log.exception("Unhandled error processing show '%s'", entry.name)


def process_movies() -> None:
    ensure_dir(DEST_DIR)
    comp_dir = SRC_DIR / COMP_SUBDIR
    ensure_dir(comp_dir)

    for src_file in sorted(SRC_DIR.iterdir()):
        if not src_file.is_file() or src_file.suffix.lower() != ".mkv":
            continue

        base = src_file.stem
        dest_subdir = DEST_DIR / base
        ensure_dir(dest_subdir)
        dest_file = dest_subdir / (base + ".mp4")

        try:
            transcode_file(src_file, dest_file)
        except Exception:
            log.error("Failed to transcode movie %s - skipping", src_file.name)
            continue

        dest_comp_file = comp_dir / src_file.name
        if dest_comp_file.exists():
            dest_comp_file.unlink()
        shutil.move(str(src_file), str(dest_comp_file))
        log.info("Moved '%s' to Completed", src_file.name)



def main() -> None:
    log.info("=== Transcode session started ===")
    log.info("Input:  %s", SRC_DIR)
    log.info("Output: %s", DEST_DIR)
    log.info("Preset: %s  (%s)", PRESET_NAME, PRESET_FILE)

    try:
        handbrake_cli()
    except FileNotFoundError as exc:
        log.critical(str(exc))
        sys.exit(1)

    process_movies()
    process_shows()

    log.info("=== Transcode session complete ===")


if __name__ == "__main__":
    main()