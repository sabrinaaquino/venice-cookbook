"""Validate every notebook: JSON parses + every code cell compiles."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

NB_DIR = Path(__file__).parent / "notebooks"

errors = 0
checked = 0

for nb_path in sorted(NB_DIR.glob("*.ipynb")):
    try:
        nb = json.loads(nb_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"FAIL {nb_path.name}  invalid JSON: {e}")
        errors += 1
        continue

    cells = nb.get("cells", [])
    code_cells = [c for c in cells if c.get("cell_type") == "code"]

    nb_errors = 0
    for i, cell in enumerate(code_cells):
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        if not src.strip():
            continue

        # Strip ipython magics so ast.parse doesn't choke
        clean_lines = []
        for line in src.splitlines():
            stripped = line.lstrip()
            if stripped.startswith(("%", "!")):
                clean_lines.append("pass  # magic")
            else:
                clean_lines.append(line)
        cleaned = "\n".join(clean_lines)

        try:
            ast.parse(cleaned)
            checked += 1
        except SyntaxError as e:
            print(f"FAIL {nb_path.name}  cell {i}: {e}")
            print(f"    around line {e.lineno}: {cleaned.splitlines()[max(0, e.lineno - 1)] if e.lineno else '?'}")
            nb_errors += 1
            errors += 1

    status = "OK  " if nb_errors == 0 else "FAIL"
    print(f"{status} {nb_path.name}  ({len(cells)} cells, {len(code_cells)} code, {nb_errors} errors)")

print(f"\n{checked} code cells parsed, {errors} errors")
sys.exit(0 if errors == 0 else 1)
