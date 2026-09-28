from __future__ import annotations

import bz2
import csv
import io
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TextIO

import zstandard

from .domain import Puzzle, puzzle_from_row


@contextmanager
def open_puzzle_text(path: Path) -> Iterator[TextIO]:
    suffixes = path.suffixes
    if suffixes and suffixes[-1] == ".zst":
        with (
            path.open("rb") as raw,
            zstandard.ZstdDecompressor().stream_reader(raw) as reader,
            io.TextIOWrapper(reader, encoding="utf-8", newline="") as text,
        ):
            yield text
        return
    if suffixes and suffixes[-1] == ".bz2":
        with bz2.open(path, "rt", encoding="utf-8", newline="") as text:
            yield text
        return
    with path.open("r", encoding="utf-8", newline="") as text:
        yield text


def iter_puzzles(path: Path) -> Iterator[Puzzle]:
    with open_puzzle_text(path) as text:
        for row in csv.DictReader(text):
            yield puzzle_from_row(row)
