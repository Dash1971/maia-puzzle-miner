from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path

from .domain import Assessment

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS assessments (
    puzzle_id TEXT NOT NULL,
    target_elo INTEGER NOT NULL,
    model TEXT NOT NULL,
    correct_move TEXT NOT NULL,
    correct_probability REAL NOT NULL,
    correct_rank INTEGER NOT NULL,
    top_move TEXT NOT NULL,
    top_probability REAL NOT NULL,
    surprise_bits REAL NOT NULL,
    selected INTEGER NOT NULL CHECK (selected IN (0, 1)),
    puzzle_json TEXT,
    PRIMARY KEY (puzzle_id, target_elo, model)
);
CREATE INDEX IF NOT EXISTS idx_assessments_selected_surprise
ON assessments(selected, surprise_bits DESC);
"""


class AssessmentStore:
    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.commit()
        self.connection.close()

    def contains(self, puzzle_id: str, elo: int, model: str) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM assessments WHERE puzzle_id = ? AND target_elo = ? AND model = ?",
            (puzzle_id, elo, model),
        ).fetchone()
        return row is not None

    def put(self, item: Assessment) -> None:
        puzzle_json = json.dumps(item.puzzle.as_json_dict(), separators=(",", ":"))
        self.connection.execute(
            """
            INSERT OR REPLACE INTO assessments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.puzzle.puzzle_id,
                item.target_elo,
                item.model,
                item.puzzle.correct_move,
                item.correct_probability,
                item.correct_rank,
                item.top_move,
                item.top_probability,
                item.surprise_bits,
                int(item.selected),
                puzzle_json if item.selected else None,
            ),
        )

    def commit(self) -> None:
        self.connection.commit()

    def selected_json(self) -> Iterator[dict[str, object]]:
        rows = self.connection.execute(
            """
            SELECT puzzle_json, target_elo, model, correct_probability, correct_rank,
                   top_move, top_probability, surprise_bits
            FROM assessments WHERE selected = 1
            ORDER BY surprise_bits DESC, puzzle_id, target_elo
            """
        )
        for row in rows:
            puzzle = json.loads(row[0])
            puzzle["assessment"] = {
                "target_elo": row[1],
                "model": row[2],
                "correct_probability": row[3],
                "correct_rank": row[4],
                "top_move": row[5],
                "top_probability": row[6],
                "surprise_bits": row[7],
            }
            yield puzzle
