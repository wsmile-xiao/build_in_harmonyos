#!/usr/bin/env python3
"""cycler consumer test (R34): import cycler + cycler() real API."""
import os
import sys


def main() -> int:
    site = os.path.join(sys.argv[1], "lib", "python3.12", "site-packages")
    sys.path.insert(0, site)
    try:
        import cycler
        from cycler import cycler
    except Exception as e:
        print(f"FAIL: import cycler: {e}", file=sys.stderr)
        return 1
    # 真实 API：cycler() 组合样式循环（组合要求**等长**——3+2 会报
    # "Can only add equal length cycles"——用等长序列实测）
    try:
        cc = (cycler(color=list("rgb")) + cycler(linestyle=["-", "--", "-."]))
        items = list(cc)
        if len(items) != 3:
            print(f"FAIL: cycler compose len={len(items)}", file=sys.stderr)
            return 1
        if items[0] != {"color": "r", "linestyle": "-"}:
            print(f"FAIL: cycler first item: {items[0]}", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"FAIL: cycler() API: {e}", file=sys.stderr)
        return 1
    print("OK: cycler imported + cycler() compose API works "
          "(pure Python library)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
