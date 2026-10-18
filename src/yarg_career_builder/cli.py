"""Command-line interface for the YARG career builder.

Usage:
    python -m yarg_career_builder.cli scan
    python -m yarg_career_builder.cli build
    python -m yarg_career_builder.cli regenerate-sources
"""

import argparse
import os
import sys
from collections import Counter

from .core.config import load_settings, load_sources
from .core.pipeline import scan_report, build_career, PublicBlockError, NoSongsError
from .core.sources import (
    find_yarg_installs,
    build_sources_from_install,
    write_sources_file,
    source_info,
    _read_tag_version,
    _resolve_channel,
)
from .paths import SOURCES_PATH


def cmd_scan(settings, sources):
    report = scan_report(settings, sources)
    music_root = report["music_root"]
    target = report["target"]
    tier_count = report["tier_count"]

    print(f"Found {len(report['songs'])} song folders under {music_root}")
    print(f"Career target: {target} songs across {tier_count} tiers "
          f"(set source_selection.filter to sources whose combined count is near {target})\n")
    if report["no_source"]:
        print(f"  ({report['no_source']} songs have no 'icon' in song.ini and cannot be tuple-referenced)\n")

    print(f"{'source':<16} {'type':<9} {'songs':>6}  {'public':<7} name")
    print("-" * 78)
    for row in report["rows"]:
        print(f"{row['source']:<16} {row['type']:<9} {row['count']:>6}  "
              f"{'yes' if row['public'] else 'no':<7} {row['name']}")


def cmd_build(settings, sources):
    try:
        result = build_career(settings, sources)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)
    except PublicBlockError as exc:
        print("\nPUBLIC CAREER BLOCKED: the following sources are not allowed in a public career")
        print("(Guitar Hero / Rock Band / other game setlists are not allowed; use general customs or YARC content):")
        for src, titles in sorted(exc.violations.items()):
            info = source_info(sources, src)
            label = info["name"] if info else "unknown"
            print(f"  - {src} ({label}): {len(titles)} song(s)")
        print("\nSet visibility to 'private' or restrict source_selection to allowed sources.")
        sys.exit(1)
    except NoSongsError:
        print("\nNo songs selected. Nothing to do.")
        sys.exit(1)

    excluded = result["excluded"]
    print(f"Scanned {result['songs_scanned']} song folders.")
    if excluded["missing_meta"]:
        print(f"  - excluded {len(excluded['missing_meta'])} songs missing name/artist/charter/icon (cannot form a tuple).")
    if excluded["no_guitar"]:
        print(f"  - skipped {len(excluded['no_guitar'])} songs with no {settings['difficulty'].get('field')} part.")

    breakdown = result["breakdown"]
    filled = result["filled"]
    name = result["career"].get("name")
    print(f"\nBuilt '{name}' with {len(result['selected'])} songs across {len(filled)} tiers.")
    print("Per source:")
    for src, n in sorted(breakdown.items(), key=lambda kv: -kv[1]):
        info = source_info(sources, src)
        label = info["name"] if info else "?"
        print(f"  - {src:<14} {n:>4} songs   ({label})")
    for cfg, chunk in filled:
        print(f"  - {cfg['name']:<26} {len(chunk)} songs")
    print(f"\nWrote:\n  {result['json_path']}\n  {result['preset_path']}")


def cmd_regenerate_sources(settings, sources):
    """Rebuild sources.json from a YARG install's OpenSource registry."""
    install_dir = (settings.get("yarg", {}) or {}).get("install_dir") or ""

    chosen = None
    chosen_channel = None
    if install_dir and os.path.isfile(os.path.join(install_dir, "YARG.exe")):
        chosen = install_dir
    else:
        if install_dir:
            print(f"Configured yarg.install_dir not found ({install_dir}). Auto-detecting...")
        installs = find_yarg_installs()
        if len(installs) == 1:
            chosen = installs[0]["path"]
            chosen_channel = installs[0]["channel"]
        elif len(installs) > 1:
            print("Found multiple YARG installs:")
            for i, inst in enumerate(installs, 1):
                print(f"  {i}. {inst['path']}   ({inst['channel']}, {inst['version']})")
            sel = input("Pick one (number) or press Enter to abort: ").strip()
            if sel.isdigit() and 1 <= int(sel) <= len(installs):
                chosen = installs[int(sel) - 1]["path"]
                chosen_channel = installs[int(sel) - 1]["channel"]
            else:
                print("Aborted.")
                sys.exit(1)
        else:
            print("No YARG install found automatically.")
            chosen = input(
                "Enter the full path to the YARG installation folder (the one containing YARG.exe): "
            ).strip().strip('"')

    if not chosen or not os.path.isfile(os.path.join(chosen, "YARG.exe")):
        print("ERROR: no valid YARG install (must contain YARG.exe).")
        sys.exit(1)

    version = _read_tag_version(chosen)
    channel = chosen_channel or _resolve_channel(os.path.basename(os.path.dirname(chosen)), version)
    print(f"Using install: {chosen}  ({channel}, {version})")

    new_sources = build_sources_from_install(chosen)
    write_sources_file(new_sources, SOURCES_PATH)

    counts = Counter(v["type"] for v in new_sources.values())
    print(f"Wrote {SOURCES_PATH} with {len(new_sources)} source ids.")
    print("Per type: " + ", ".join(f"{t}={n}" for t, n in sorted(counts.items())))
    print("Tip: set 'yarg.install_dir' in settings.json to skip auto-detection next time.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="YARG career builder")
    parser.add_argument("command", choices=["scan", "build", "regenerate-sources"], help="what to do")
    args = parser.parse_args(argv)

    settings = load_settings()
    sources = load_sources()

    if args.command == "scan":
        cmd_scan(settings, sources)
    elif args.command == "build":
        cmd_build(settings, sources)
    elif args.command == "regenerate-sources":
        cmd_regenerate_sources(settings, sources)


if __name__ == "__main__":
    main()
