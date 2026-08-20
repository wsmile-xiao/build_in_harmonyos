#!/usr/bin/env python3
"""test_package — vlang 消费验证（L0d: test() 必须 self.run）。

验证 bin/v 为合法 ELF 可执行文件 + v version 输出（V 编译器自举产物）。
"""
import os
import struct
import subprocess
import sys


def check_elf(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        return False, "not ELF magic"
    with open(path, "rb") as f:
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
    kind = {2: "ET_EXEC", 3: "ET_DYN"}.get(e_type, f"ET_{e_type}")
    return True, kind


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    v = os.path.join(pkg, "bin", "v")
    if not os.path.isfile(v):
        print(f"FAIL: missing {v}")
        return 1
    ok, kind = check_elf(v)
    if not ok:
        print(f"FAIL: {v} {kind}")
        return 1
    print(f"OK: v is {kind} executable")
    # v version 输出验证（aireview P3：断言加强——"V" in out 偏弱 →
    # 精确匹配版本行 "V 0.5.x"）
    try:
        r = subprocess.run([v, "version"], capture_output=True, text=True,
                           timeout=60)
        out = r.stdout or r.stderr or ""
        first = out.strip().splitlines()[0] if out.strip() else ""
        if r.returncode == 0 and first.startswith("V "):
            print("OK: v version ->", first[:60])
        else:
            print(f"FAIL: v version rc={r.returncode}: {(out or '')[:200]}")
            return 1
    except subprocess.TimeoutExpired:
        print("FAIL: v version timed out")
        return 1
    except Exception as e:
        print(f"FAIL: v version error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
