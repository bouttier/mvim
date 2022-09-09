from argparse import ArgumentParser
from pathlib import Path

from . import MVim


def main():
    parser = ArgumentParser(
        description="Rename files and directories by " "editing their names with vim."
    )
    parser.add_argument(
        "-a",
        "--all",
        dest="all_files",
        action="store_true",
        help="do not ignore entries starting with “.”.",
    )
    parser.add_argument(
        "-s",
        "--follow-symlinks",
        dest="follow_symlinks",
        action="store_true",
        help="follow symlinks.",
    )
    parser.add_argument(
        "-f", "--force", dest="force", action="store_true", help="bypass “Are you sure?” messages."
    )
    parser.add_argument(
        "-r",
        "--recursive",
        dest="recursive",
        action="store_true",
        help="remove directories and their contents " "recursively.",
    )
    parser.add_argument(
        "-w",
        "--windows",
        dest="windows",
        action="store_true",
        help="open old and new filenames in two windows side by side.",
    )
    parser.add_argument(
        "-d", "--diff", dest="diff", action="store_true", help="same as -w but in diff mode."
    )
    parser.add_argument(
        "-m", "--meld", dest="meld", action="store_true", help="same as -d but open with meld."
    )
    parser.add_argument(
        "-c",
        "--command",
        dest="cmd",
        default=None,
        help="use custom editor command (can be combined with -d).",
    )
    parser.add_argument(
        "files", metavar="FILE", nargs="*", type=Path, help="file or directory to rename"
    )

    args = parser.parse_args()

    files = args.files
    if not files:
        files.append(Path("."))

    try:
        MVim(**vars(args))
    except KeyboardInterrupt:
        exit(1)
