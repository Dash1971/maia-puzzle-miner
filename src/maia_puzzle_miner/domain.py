from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

import chess


@dataclass(frozen=True)
class Puzzle:
    puzzle_id: str
    source_fen: str
    presented_fen: str
    setup_move: str
    solution_moves: tuple[str, ...]
    rating: int
    rating_deviation: int
    popularity: int
    plays: int
    themes: tuple[str, ...]
    game_url: str
    opening_tags: tuple[str, ...]

    @property
    def correct_move(self) -> str:
        return self.solution_moves[0]

    def as_json_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["solution_moves"] = list(self.solution_moves)
        value["themes"] = list(self.themes)
        value["opening_tags"] = list(self.opening_tags)
        return value


@dataclass(frozen=True)
class Assessment:
    puzzle: Puzzle
    target_elo: int
    model: str
    correct_probability: float
    correct_rank: int
    top_move: str
    top_probability: float
    surprise_bits: float
    selected: bool


def puzzle_from_row(row: Mapping[str, str]) -> Puzzle:
    moves = tuple(row["Moves"].split())
    if len(moves) < 2:
        raise ValueError(f"puzzle {row.get('PuzzleId', '<unknown>')} has fewer than two moves")

    board = chess.Board(row["FEN"])
    setup = chess.Move.from_uci(moves[0])
    if setup not in board.legal_moves:
        raise ValueError(f"puzzle {row['PuzzleId']} has illegal setup move {moves[0]}")
    board.push(setup)

    correct = chess.Move.from_uci(moves[1])
    if correct not in board.legal_moves:
        raise ValueError(f"puzzle {row['PuzzleId']} has illegal correct move {moves[1]}")

    return Puzzle(
        puzzle_id=row["PuzzleId"],
        source_fen=row["FEN"],
        presented_fen=board.fen(),
        setup_move=moves[0],
        solution_moves=moves[1:],
        rating=int(row["Rating"]),
        rating_deviation=int(row["RatingDeviation"]),
        popularity=int(row["Popularity"]),
        plays=int(row["NbPlays"]),
        themes=tuple(filter(None, row.get("Themes", "").split())),
        game_url=row.get("GameUrl", ""),
        opening_tags=tuple(filter(None, row.get("OpeningTags", "").split())),
    )
