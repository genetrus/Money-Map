from __future__ import annotations

import subprocess
import sys


def main() -> None:
    result = subprocess.run([sys.executable, "-m", "money_map", "export", "all"], check=False)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
