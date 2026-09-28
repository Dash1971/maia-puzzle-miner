from __future__ import annotations

import json
from pathlib import Path

import chess

from maia_puzzle_miner.domain import puzzle_from_row
from maia_puzzle_miner.pipeline import scan
from maia_puzzle_miner.policy.maia3 import historical_tokens, mirror_move, move_index
from maia_puzzle_miner.store import AssessmentStore

FIXTURE = Path(__file__).parent / "fixtures" / "puzzles.csv"


class FakePolicy:
    model_id = "fake-v1"

    def probabilities(self, board: chess.Board, elo: int) -> dict[str, float]:
        moves = sorted(move.uci() for move in board.legal_moves)
        weights = {move: 1.0 for move in moves}
        if "a1b1" in weights:
            weights["a1b1"] = 0.01
        return weights


def test_maia3_move_vocabulary_and_black_mirroring() -> None:
    assert move_index("e2e4", False) == 796
    assert move_index("e7e5", True) == 796
    assert move_index("a7a8q", False) == 4096
    assert move_index("h7h8n", False) == 4351
    assert mirror_move("e7e8q") == "e2e1q"


def test_maia3_current_position_encoding() -> None:
    board = chess.Board()
    board.push_uci("e2e4")
    tokens = historical_tokens(board)
    assert tokens.shape == (1, 64, 97)
    for history in range(8):
        assert tokens[0, chess.E2, history * 12 + 6] == 0
        assert tokens[0, chess.E5, history * 12 + 6] == 1
    assert not tokens[:, :, 96].any()


def test_reconstructs_presented_position_and_solution() -> None:
    row = {
        "PuzzleId": "x",
        "FEN": "7k/8/8/8/8/8/8/K7 b - - 0 1",
        "Moves": "h8g8 a1b1",
        "Rating": "1500",
        "RatingDeviation": "80",
        "Popularity": "90",
        "NbPlays": "200",
        "Themes": "quietMove",
    }
    puzzle = puzzle_from_row(row)
    board = chess.Board(puzzle.presented_fen)
    assert puzzle.setup_move == "h8g8"
    assert puzzle.correct_move == "a1b1"
    assert chess.Move.from_uci(puzzle.correct_move) in board.legal_moves


def test_scan_is_resumable_and_exports_selected(tmp_path: Path) -> None:
    database = tmp_path / "puzzles.sqlite"
    first = scan(FIXTURE, database, [1500], FakePolicy(), 0.05)
    second = scan(FIXTURE, database, [1500], FakePolicy(), 0.05)

    assert first.read == 2
    assert first.assessed == 2
    assert first.selected == 1
    assert second.assessed == 0
    assert second.skipped == 2

    store = AssessmentStore(database)
    try:
        selected = list(store.selected_json())
    finally:
        store.close()
    assert len(selected) == 1
    assert selected[0]["puzzle_id"] == "sample01"
    assert selected[0]["assessment"]["correct_rank"] > 1
    json.dumps(selected[0])

    store = AssessmentStore(database)
    try:
        grouped = list(store.selected_grouped_json(min_selected_elos=1, limit=1))
    finally:
        store.close()
    assert len(grouped) == 1
    assert grouped[0]["puzzle_id"] == "sample01"
    assert len(grouped[0]["assessments"]) == 1
