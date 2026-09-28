from __future__ import annotations

from collections import deque
from collections.abc import Mapping

import chess


class Maia3PolicyProvider:
    """Thin adapter around the pinned CSSLab Maia-3 package.

    Imports are delayed so parsing/export commands work without the heavy optional extra.
    The adapter intentionally reads the full legal-move policy instead of UCI MultiPV,
    because the correct move may be far outside the top candidates.
    """

    def __init__(self, model: str = "maia3-5m", device: str | None = None) -> None:
        try:
            import torch
            from maia3.uci import Maia3UCIEngine, parse_args
        except ImportError as exc:
            raise RuntimeError(
                "Maia-3 support is not installed; run pip install -e '.[maia3]'"
            ) from exc

        args = ["--model", model, "--no-use-amp"]
        if device:
            args.extend(["--device", device])
        self._torch = torch
        self._engine = Maia3UCIEngine(parse_args(args))
        self._engine.ensure_model_loaded()
        self.model_id = model

    def probabilities(self, board: chess.Board, elo: int) -> Mapping[str, float]:
        from maia3.dataset import get_legal_moves_mask, tokenize_board
        from maia3.utils import mirror_move

        engine = self._engine
        engine.board = board.copy(stack=False)
        engine.history = deque([tokenize_board(engine.board)], maxlen=engine.cfg.history)
        engine.self_elo = elo
        engine.oppo_elo = elo

        legal_mask = get_legal_moves_mask(engine.board, engine.all_moves_dict)
        tokens = engine._tokens_from_history(engine.history).unsqueeze(0).to(engine.cfg.device)
        self_elos = self._torch.tensor([elo], dtype=self._torch.long, device=engine.cfg.device)

        with self._torch.no_grad():
            logits, _, _ = engine.model(tokens, self_elos, self_elos)
        masked = logits[0].float().masked_fill(~legal_mask.to(engine.cfg.device), float("-inf"))
        probs = self._torch.softmax(masked, dim=-1).tolist()

        result: dict[str, float] = {}
        for move in engine.board.legal_moves:
            canonical = move.uci() if engine.board.turn == chess.WHITE else mirror_move(move.uci())
            result[move.uci()] = float(probs[engine.all_moves_dict[canonical]])
        return result
