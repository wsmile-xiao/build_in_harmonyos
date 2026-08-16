#!/usr/bin/env python3
"""alien-arena 消费验证脚本（L0d: test() 经 self.run 执行）。

游戏 client 需 X11（OHOS 无），归档以 dedicated server（alienarena-ded）
构建；OHOS headless 无法实跑游戏，验证：
1) bin/ 下存在 alienarena-ded 可执行文件
2) 为合法 ELF 可执行文件（magic 0x7f 'E' 'L' 'F'）
"""
import os
import struct
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
    bins = os.path.join(pkg, "bin")
    for name in ("alienarena-ded", "alienarena_ded", "alien"):
        cand = os.path.join(bins, name)
        if os.path.isfile(cand):
            ok, kind = check_elf(cand)
            if not ok:
                print(f"FAIL: {cand} {kind}")
                return 1
            print(f"OK: {cand} is {kind} executable")
            return 0
    print("FAIL: no alienarena binary found in bin/")
    return 1


if __name__ == "__main__":
    sys.exit(main())
