#!/usr/bin/env python3
"""Re-apply the local fallback patch to webapp/index.html.

The cloud-built webapp/index.html branches on window.location.hostname and
routes any non-prod/non-test host to a hardcoded iframixtest URL. That breaks
when serving locally. This script rewrites that fallback else-branch to derive
values from window.location.

Idempotent: if the marker comment already exists, exits 0 without changes.

Usage:
  python3 scripts/apply-local-index-html-patch.py
  python3 scripts/apply-local-index-html-patch.py path/to/index.html
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    target = Path(args[0] if args else "webapp/index.html")

    if not target.is_file():
        print(f"error: {target} not found", file=sys.stderr)
        return 1

    src = target.read_text(encoding="utf-8")
    if "local-iframix-patch" in src:
        print(f"already patched: {target}")
        return 0

    shutil.copyfile(target, target.with_suffix(target.suffix + ".orig"))

    pattern = re.compile(
        r"\}\s*else\s*\{\s*"
        r"window\.isHttps\s*=\s*[^;]+;\s*"
        r"window\.debug\s*=\s*[^;]+;\s*"
        r"window\.baseUrl\s*=\s*[^;]+;\s*"
        r"window\.mqttAddr\s*=\s*[^;]+;\s*"
        r"window\.appAddr\s*=\s*[^;]+;\s*"
        r"window\.mqttMaxCount\s*=\s*[^;]+;\s*"
        r"\}"
    )

    replacement = (
        "} else {\n"
        "            // local-iframix-patch: derive config from "
        "window.location so the\n"
        "            // same bundle works on any host/port and under "
        "HTTPS/HTTP. See\n"
        "            // scripts/apply-local-index-html-patch.py.\n"
        "            window.isHttps = window.location.protocol === 'https:';\n"
        "            window.baseUrl = window.location.protocol + '//' + "
        "window.location.host;\n"
        "            window.mqttAddr = window.location.host;\n"
        "            window.debug = true;\n"
        "            window.appAddr = 'https://www.pgyer.com/iframixPro';\n"
        "            window.mqttMaxCount = 33;\n"
        "        }"
    )

    new_src, count = pattern.subn(replacement, src, count=1)
    if count != 1:
        print(
            "error: fallback else-branch not found - bundle format changed?",
            file=sys.stderr,
        )
        return 2

    target.write_text(new_src, encoding="utf-8")
    print(f"patched: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
