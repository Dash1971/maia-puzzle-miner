# Prior-art search and design notes

Checked 2026-09-28.

## Result

No open-source tool was found that streams the Lichess puzzle corpus and selects puzzles
by the rating-conditioned Maia probability of the known correct move.

Closest work:

- [Maia Chess](https://www.maiachess.com/puzzles) serves Maia-powered puzzles, but a
  corpus-mining implementation for this criterion was not found.
- [Testing Maia's Puzzle Performance](https://lichess.org/@/jk_182/blog/testing-maias-puzzle-performance/UPmqO0Rg)
  evaluates Maia models on popular Lichess puzzles; it studies solve performance rather
  than publishing a reusable low-policy candidate miner.
- [Estimating the Difficulty of Chess Puzzles by Combining Fine-Tuned Maia-2 with
  Hand-Crafted and Engine Features](https://annals-csis.org/Volume_43/drp/pdf/6497.pdf)
  uses Maia-2 for difficulty prediction, a related research task but not this pipeline.
- [chess-puzzle-difficulty-prediction](https://github.com/jasonJathanna/chess-puzzle-difficulty-prediction)
  derives Stockfish features from Lichess puzzles.
- [lichess-puzzle-checker](https://github.com/gr-g/lichess-puzzle-checker) identifies
  questionable puzzles using engine evaluations.
- [lichess-puzzle-mixer](https://github.com/DSerejo/lichess-puzzle-mixer) imports and
  filters the offline corpus by themes.
- [Generating Creative Chess Puzzles](https://arxiv.org/abs/2510.23881) explicitly
  optimizes for counterintuitive puzzles, but generates novel positions with a
  Stockfish/AlphaZero-derived signal rather than mining Lichess with rating-conditioned
  Maia move probabilities.

Searches covered GitHub repositories and the web for combinations of Maia, Lichess
puzzles, human move probability, puzzle difficulty, and counterintuitive puzzle mining.
The conclusion is necessarily “no close public implementation found,” not proof that no
private or poorly indexed implementation exists.

## Selection metric

For the solver's first correct move `m*` in presented position `s` at rating `r`:

```text
surprise_bits = -log2(P_Maia(m* | s, r))
```

Store alongside it:

- correct-move probability and rank;
- Maia's top human move and probability;
- Lichess puzzle rating, themes, popularity, and play count;
- complete known solution line;
- model identifier and target Elo.

High surprise is useful when the puzzle is objectively sound. Later ranking should add:

1. Stockfish uniqueness and evaluation-loss checks;
2. Maia probability curves across several Elo values;
3. theme diversity and near-duplicate suppression;
4. minimum Lichess play/popularity evidence;
5. manual instructional-quality review.
