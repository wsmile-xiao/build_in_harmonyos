#!/usr/bin/env python3
"""planetblupi 产物结构断言(L1 消费者视角)。"""
import os
import sys

FAILURES = []

def check(cond, label, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(label)

def main():
    module = os.environ["PLANETBLUPI_BIN"]
    res = os.environ["PLANETBLUPI_RES_DIR"]

    with open(module, "rb") as fh:
        blob = fh.read()
    print(f"artifact: {module} ({len(blob)} bytes)")

    # ELF 头长度防御(ELF64 头 64 字节),截断产物走可读失败而非 IndexError
    if len(blob) < 64:
        check(False, "ELF 头长度", f"{len(blob)} 字节 < 64(截断或空产物)")
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1

    check(blob[:4] == b"\x7fELF", "ELF 魔数")
    check(blob[4] == 2, "ELFCLASS64", f"ei_class={blob[4]}")
    e_type = int.from_bytes(blob[16:18], "little")
    check(e_type == 3, "ET_DYN(PIE 可执行)", f"e_type={e_type}")
    e_machine = int.from_bytes(blob[18:20], "little")
    check(e_machine == 0xB7, "e_machine=AArch64", f"e_machine={e_machine}")
    check(b"planetblupi" in blob or b"blupi" in blob, "产物含 blupi 字符串标记")

    # 资源目录消费验证：上游 resources/ 实际结构为 data/ fonts/ icon/ image/
    # movie/ music/ po/ sound/（关卡数据 demo*.blp 在 data/ 下，无 level/ 目录）
    for sub in ("data", "image", "music", "sound"):
        check(os.path.isdir(os.path.join(res, sub)), f"resources/{sub}/ 存在")
    check(any(f.startswith("demo") and f.endswith(".blp")
              for f in os.listdir(os.path.join(res, "data"))),
          "resources/data/ 含关卡数据(demo*.blp)")

    if FAILURES:
        print(f"\nFAILED: {len(FAILURES)} 项 — {FAILURES}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
