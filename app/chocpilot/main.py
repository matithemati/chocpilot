"""Punkt wejścia: chocpilot [--minimized] [--config PLIK] [--verbose] [--simulate]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chocpilot", description="ChocPilot – konfiguracja macropada"
    )
    parser.add_argument("--minimized", action="store_true", help="start w zasobniku / pasku menu")
    parser.add_argument("--config", type=Path, help="ścieżka pliku konfiguracji")
    parser.add_argument("--verbose", action="store_true", help="szczegółowy dziennik na konsoli")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="tryb deweloperski: symulator urządzenia zamiast płytki",
    )
    parser.add_argument("--version", action="version", version=f"ChocPilot {__version__}")
    # macOS dopisuje -psn_… przy starcie z Findera (starsze systemy) – ignorujemy nieznane opcje.
    args, _unknown = parser.parse_known_args(argv)

    from .gui.app import run

    return run(
        simulate=args.simulate,
        minimized=args.minimized,
        config_path=args.config,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
