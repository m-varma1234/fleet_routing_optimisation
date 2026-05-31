"""
CLI script to bulk-download VRP benchmark datasets into data/raw/.

Usage:
    python -m src.utils.download_data --solomon C101 R101 RC201
    python -m src.utils.download_data --augerat A-n32-k5 B-n31-k5
    python -m src.utils.download_data --all-solomon
"""

import argparse
import ssl
import urllib.request
from pathlib import Path

_ssl_ctx = ssl._create_unverified_context()

SOLOMON_INSTANCES = [
    "C101","C102","C103","C104","C105","C106","C107","C108","C109",
    "C201","C202","C203","C204","C205","C206","C207","C208",
    "R101","R102","R103","R104","R105","R106","R107","R108","R109","R110","R111","R112",
    "R201","R202","R203","R204","R205","R206","R207","R208","R209","R210","R211",
    "RC101","RC102","RC103","RC104","RC105","RC106","RC107","RC108",
    "RC201","RC202","RC203","RC204","RC205","RC206","RC207","RC208",
]

_SOLOMON_BASE = "https://raw.githubusercontent.com/iRB-Lab/py-ga-VRPTW/master/data/text/"
_AUGERAT_BASE = "https://vrp.gdb.tools/datasets/"
_RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"


def _download_file(url: str, dest: Path) -> bool:
    """Fetch url into dest. Returns True on success, False on failure."""
    try:
        with urllib.request.urlopen(url, context=_ssl_ctx) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"FAILED ({e})")
        return False


def download_solomon(names: list[str]) -> None:
    dest = _RAW_DIR / "solomon"
    dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = dest / f"{name}.txt"
        if path.exists():
            print(f"  {name}: already cached, skipping.")
            continue
        print(f"  {name} ... ", end="", flush=True)
        if _download_file(f"{_SOLOMON_BASE}{name}.txt", path):
            print("OK")


def download_augerat(names: list[str]) -> None:
    dest = _RAW_DIR / "augerat"
    dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        path = dest / f"{name}.vrp"
        if path.exists():
            print(f"  {name}: already cached, skipping.")
            continue
        print(f"  {name} ... ", end="", flush=True)
        if _download_file(f"{_AUGERAT_BASE}{name}.vrp", path):
            print("OK")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download VRP benchmark data.")
    parser.add_argument("--solomon", nargs="+", metavar="NAME",
                        help="Solomon VRPTW instances to download (e.g. C101 R201)")
    parser.add_argument("--augerat", nargs="+", metavar="NAME",
                        help="Augerat CVRP instances to download (e.g. A-n32-k5)")
    parser.add_argument("--all-solomon", action="store_true",
                        help="Download all 56 Solomon 100-customer instances")
    args = parser.parse_args()

    if not any([args.solomon, args.augerat, args.all_solomon]):
        parser.print_help()
        return

    if args.all_solomon:
        print("Downloading all 56 Solomon instances ...")
        download_solomon(SOLOMON_INSTANCES)

    if args.solomon:
        print("Downloading Solomon instances ...")
        download_solomon(args.solomon)

    if args.augerat:
        print("Downloading Augerat instances ...")
        download_augerat(args.augerat)


if __name__ == "__main__":
    main()
