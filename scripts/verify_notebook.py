"""Execute the notebook's code cells in order, as a kernel would, and report failures."""
import json
import os
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parents[1]
nb = json.loads((ROOT / "notebook.ipynb").read_text(encoding="utf-8"))

# make sure the optional live cell stays offline
for var in ("DEEPSEEK_API_KEY", "API_KEY"):
    os.environ.pop(var, None)

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

code_cells = [(i, "".join(c["source"])) for i, c in enumerate(nb["cells"])
              if c["cell_type"] == "code"]
print(f"executing {len(code_cells)} code cells\n")

ns = {"__name__": "__main__"}
failures = []
for n, (idx, src) in enumerate(code_cells, 1):
    first = src.strip().splitlines()[0][:70]
    try:
        exec(compile(src, f"<cell {idx}>", "exec"), ns)
        print(f"  cell {n:>2} (nb#{idx:>2}) OK    {first}")
    except Exception:
        print(f"  cell {n:>2} (nb#{idx:>2}) FAIL  {first}")
        failures.append((idx, traceback.format_exc()))

print()
if failures:
    print("=" * 70)
    for idx, tb in failures:
        print(f"\n--- nb#{idx} ---")
        print(tb[-1500:])
    sys.exit(1)
print("ALL CODE CELLS RAN CLEANLY")
