#!/usr/bin/env python3
"""termbg 0.6.2 消费者测试（R34：实质调用被测包二进制，非空壳）。

用法: PACKAGE_FOLDER=<conan package folder> python3 test_termbg.py

共 12 条断言，分两组：

A. 消费者功能（8 条）——真实运行 bin/termbg：
   A1 `--version` 输出含 0.6.2 且退出码 0
   A2 默认运行退出码 0
   A3 打印 "Check terminal background color"（检测头部）
   A4 打印 "Term :"（终端类型探测路径被执行）
   A5 COLORFGBG=15;0 → "Color: R=0, G=0, B=0"
   A6 COLORFGBG=15;0 → "Theme: Dark"
   A7 COLORFGBG=0;15 → "Theme: Light"（与 A6 相反分支，证明真读环境变量）
   A8 非法参数 → 退出码非 0

B. 鸿蒙特有（4 条）——断言产物在本平台可执行所必需的特性：
   B1 ELF class = 64-bit (ELFCLASS64)
   B2 ELF e_machine = 183 (EM_AARCH64)
   B3 PT_INTERP 程序解释器为 `/lib/ld-musl-aarch64.so.1`（OHOS musl，
      而非 glibc 的 /lib/ld-linux-aarch64.so.1）
   B4 含 `.note.ohos.ident` 段（HarmonyOS 标记；未签名/非 OHOS 产物缺此标记）
"""
import os
import struct
import subprocess
import sys

PACKAGE_FOLDER = os.environ.get("PACKAGE_FOLDER", "")
BINARY = os.path.join(PACKAGE_FOLDER, "bin", "termbg")

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"        [ok] {name}")
    else:
        print(f"        [fail] {name} {detail}")
        FAILURES.append(name)


def run_binary(args=None, env_extra=None, timeout=60):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    cmd = [BINARY] + (args or [])
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env,
                          timeout=timeout)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def section_a():
    print("[step] A. 消费者功能（真实运行 bin/termbg）")

    rc, out = run_binary(["--version"])
    check("A1 --version 含 0.6.2 且退出码 0",
          rc == 0 and "0.6.2" in out, f"(rc={rc}, out={out!r})")

    rc, out = run_binary()
    check("A2 默认运行退出码 0", rc == 0, f"(rc={rc})")
    check("A3 打印检测头部 'Check terminal background color'",
          "Check terminal background color" in out, f"(out={out!r})")
    check("A4 终端类型探测路径执行（Term :）", "Term :" in out,
          f"(out={out!r})")

    rc, out = run_binary(env_extra={"COLORFGBG": "15;0"})
    check("A5 COLORFGBG=15;0 → Color: R=0, G=0, B=0",
          "Color: R=0, G=0, B=0" in out, f"(out={out!r})")
    check("A6 COLORFGBG=15;0 → Theme: Dark", "Theme: Dark" in out,
          f"(out={out!r})")

    rc, out = run_binary(env_extra={"COLORFGBG": "0;15"})
    check("A7 COLORFGBG=0;15 → Theme: Light", "Theme: Light" in out,
          f"(out={out!r})")

    rc, out = run_binary(["--not-a-real-flag"])
    check("A8 非法参数退出码非 0", rc != 0, f"(rc={rc})")


def section_b():
    print("[step] B. 鸿蒙特有断言（产物平台特性）")
    with open(BINARY, "rb") as handle:
        blob = handle.read()

    check("B1 ELF class = 64-bit", blob[:4] == b"\x7fELF" and blob[4] == 2,
          f"(magic={blob[:4]!r}, class={blob[4]})")
    machine = struct.unpack_from("<H", blob, 18)[0] if len(blob) > 20 else -1
    check("B2 ELF e_machine = 183 (EM_AARCH64)", machine == 183,
          f"(e_machine={machine})")
    check("B3 PT_INTERP = /lib/ld-musl-aarch64.so.1 (OHOS musl)",
          b"/lib/ld-musl-aarch64.so.1" in blob)
    check("B4 含 .note.ohos.ident 段（HarmonyOS 标记）",
          b".note.ohos.ident" in blob)


def main():
    if not os.path.isfile(BINARY):
        print(f"termbg binary not found: {BINARY}")
        return 2
    section_a()
    section_b()
    total = 8 + 4
    if FAILURES:
        print(f"[fail] termbg test_package: {len(FAILURES)}/{total} 断言失败: "
              + ", ".join(FAILURES))
        return 1
    print(f"[ok] termbg test_package: all {total} assertions passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
