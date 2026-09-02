# -*- coding: utf-8 -*-
"""全量回归 runner：python -X utf8 tests/run_all.py

顺序执行 tests/ 下所有 test_v12*.py 套件并汇总。
- 每套件独立子进程（互不污染 env，与单跑行为一致）
- 任一套件失败即退出码非零（CI/本地全回归一命令完成）
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    suites = sorted(HERE.glob("test_v12*.py"))
    if not suites:
        print("no suites found")
        return 1
    failed = []
    for s in suites:
        print(f"\n===== {s.name} =====", flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(s)],
                           cwd=str(HERE.parent), timeout=900)
        if r.returncode != 0:
            failed.append(s.name)
    print("\n" + "=" * 46)
    if failed:
        print(f"FAILED ({len(failed)}/{len(suites)}): {', '.join(failed)}")
        return 1
    print(f"ALL GREEN: {len(suites)} suites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
