"""Score every captured proposal on the fixed held-out set.

GEPA writes more proposals than a single run scores. This backfills the rest so
the leaderboard is complete: N prompts, one ruler, comparable numbers.

    python score_proposals.py --lm deepseek/deepseek-flash
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _p in (_ROOT / ".pydeps", _ROOT):   # vendored dspy, then the package itself
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import peerlens as pl  # noqa: E402
from run_teach import (  # noqa: E402
    NAIVE_PROMPT,
    build_examples,
    make_metric,
    score_instruction,
    stratified_indices,
)

MOJIBAKE = {"â€”": "—", "â€“": "–", "â€™": "'", "â€œ": '"', "Â": "", "\x00": ""}


def clean(text: str) -> str:
    for bad, good in MOJIBAKE.items():
        text = text.replace(bad, good)
    return text.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lm", required=True)
    ap.add_argument("--eval-limit", type=int, default=10)
    ap.add_argument("--prompts", default="out/teaching/prompts")
    ap.add_argument("--leaderboard", default="out/teaching/leaderboard.json")
    ap.add_argument("--adapter", default="chat", choices=["xml", "chat"])
    args = ap.parse_args(argv)

    import dspy

    here = Path(__file__).resolve().parents[1]
    lm = dspy.LM(args.lm, temperature=0.0)
    adapter = (
        dspy.ChatAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
        if args.adapter == "chat"
        else dspy.XMLAdapter(use_native_function_calling=False, use_json_adapter_fallback=False)
    )
    metric_impl = make_metric()

    all_examples = build_examples(len(pl.CASES))
    idx = stratified_indices(len(all_examples), args.eval_limit)
    eval_examples = [all_examples[i] for i in idx]

    board_path = here / args.leaderboard
    board: list[dict] = []
    if board_path.exists():
        board = json.loads(board_path.read_text(encoding="utf-8"))
    known = {clean(row["text"]) for row in board if "text" in row}

    prompts_dir = here / args.prompts
    proposals = sorted(prompts_dir.glob("proposal_*.md"))
    todo = []
    for path in proposals:
        text = clean(path.read_text(encoding="utf-8"))
        if text and text not in known:
            todo.append((path.stem, text))

    print(f"scoring {len(todo)} unscored proposal(s) on {len(eval_examples)} held-out cases")
    if not todo:
        print("nothing to do - leaderboard already covers every proposal")
        return 0

    for i, (stem, text) in enumerate(todo, 1):
        score, per_case = score_instruction(text, eval_examples, lm, adapter, metric_impl)
        board.append({
            "label": f"{stem}",
            "score": score,
            "chars": len(text),
            "per_case": per_case,
            "text": text,
        })
        known.add(text)
        print(f"  [{i}/{len(todo)}] {stem}: {score:.3f}")
        board_path.write_text(json.dumps(board, indent=2), encoding="utf-8")

    print(f"\nwrote {board_path}  ({len(board)} scored entries)")
    print("now rebuild the deck:  python build_deck.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
