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

    def selected_grouped_json(
        self, min_selected_elos: int = 1, limit: int | None = None
    ) -> Iterator[dict[str, object]]:
        limit_clause = "" if limit is None else "LIMIT ?"
        parameters: tuple[int, ...] = (
            (min_selected_elos,) if limit is None else (min_selected_elos, limit)
        )
        rows = self.connection.execute(
            f"""
            WITH eligible AS (
                SELECT puzzle_id,
                       AVG(surprise_bits) AS average_surprise_bits,
                       SUM(selected) AS selected_elo_bands
                FROM assessments
                GROUP BY puzzle_id
                HAVING SUM(selected) >= ?
                ORDER BY average_surprise_bits DESC, puzzle_id
                {limit_clause}
            )
            SELECT e.puzzle_id, e.average_surprise_bits, e.selected_elo_bands,
                   a.target_elo, a.model, a.correct_probability, a.correct_rank,
                   a.top_move, a.top_probability, a.surprise_bits, a.selected,
                   COALESCE(
                       a.puzzle_json,
                       (SELECT puzzle_json FROM assessments p
                        WHERE p.puzzle_id = e.puzzle_id AND p.puzzle_json IS NOT NULL
                        LIMIT 1)
                   ) AS puzzle_json
            FROM eligible e
            JOIN assessments a ON a.puzzle_id = e.puzzle_id
            ORDER BY e.average_surprise_bits DESC, e.puzzle_id, a.target_elo
            """,
            parameters,
        )
        current_id: str | None = None
        current: dict[str, object] | None = None
        for row in rows:
            if row[0] != current_id:
                if current is not None:
                    yield current
                current_id = row[0]
                current = json.loads(row[11])
                current.setdefault("correct_move", current["solution_moves"][0])
                current["ranking"] = {
                    "average_surprise_bits": row[1],
                    "selected_elo_bands": row[2],
                }
                current["assessments"] = []
            current["assessments"].append(
                {
                    "target_elo": row[3],
                    "model": row[4],
                    "correct_probability": row[5],
                    "correct_rank": row[6],
                    "top_move": row[7],
                    "top_probability": row[8],
                    "surprise_bits": row[9],
                    "selected": bool(row[10]),
                }
            )
        if current is not None:
            yield current
