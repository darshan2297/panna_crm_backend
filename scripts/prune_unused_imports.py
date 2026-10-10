"""Prune imports left unused after the permission-guard rewrite.

`require_roles`/`UserRole`/`get_current_active_user` stopped being referenced
once routes moved to `require_permission`, but the import lines still name them.

Only removes a name when it appears nowhere else in the file body, and only
from the known import statements this rewrite touched.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
ROUTERS = BACKEND / "app" / "api" / "v1"

# Only these three are candidates for removal, and only when unreferenced.
CANDIDATES = ("UserRole", "require_roles", "get_current_active_user")

AUTH_IMPORT_RE = re.compile(r"^from app\.dependencies\.auth import (.+)$", re.MULTILINE)
USER_IMPORT_RE = re.compile(r"^from app\.models\.user import (.+)$", re.MULTILINE)


def used_outside_imports(src: str, name: str) -> bool:
    for line in src.splitlines():
        s = line.strip()
        if s.startswith(("from ", "import ")):
            continue
        if re.search(rf"\b{re.escape(name)}\b", line):
            return True
    return False


def tidy(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    ast.parse(src)  # guard against rewriting something broken
    removed: list[str] = []

    for regex, candidates in ((AUTH_IMPORT_RE, CANDIDATES), (USER_IMPORT_RE, ("UserRole",))):
        m = regex.search(src)
        if not m:
            continue
        names = [n.strip() for n in m.group(1).split(",")]
        keep = [n for n in names if not (n in candidates and not used_outside_imports(src, n))]
        dropped = [n for n in names if n not in keep]
        if dropped:
            removed.extend(dropped)
            if keep:
                src = src[: m.start()] + f"from {'app.dependencies.auth' if regex is AUTH_IMPORT_RE else 'app.models.user'} import {', '.join(keep)}" + src[m.end() :]
            else:
                line_start = src.rfind("\n", 0, m.start()) + 1
                line_end = src.find("\n", m.end()) + 1
                src = src[:line_start] + src[line_end:]

    path.write_text(src, encoding="utf-8")
    return removed


def main() -> int:
    for p in sorted(ROUTERS.rglob("router.py")):
        removed = tidy(p)
        if removed:
            print(f"  {str(p.relative_to(BACKEND)):44s} - {', '.join(sorted(set(removed)))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
