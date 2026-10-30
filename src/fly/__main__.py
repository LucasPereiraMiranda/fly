from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="fly")
    parser.add_subparsers(dest="command", required=True)
    parser.parse_args(argv)


if __name__ == "__main__":
    main()
