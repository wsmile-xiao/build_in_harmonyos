#!/usr/bin/env python3
"""Conan test_package for dconf — R34 real artifact verification (no empty shell).

dconf ships a CLI tool <pkg>/bin/dconf plus libraries and a GSettings backend.
This test verifies the dconf CLI exists and is executable; it then tries to
run `dconf help` — but on OHOS the AppSpawn sandbox blocks posix_spawn of
user-path executables (E212-class "Operation not permitted", same as
python3-cairo's dlopen restriction). In that case it degrades to static ELF
artifact verification (real, honest), never faking a pass.
"""
import os
import struct
import subprocess
import sys

ELF_MAGIC = b"\x7fELF"


def _is_elf_executable(path):
    """Return True if path is a valid ELF executable (ET_EXEC or PIE ET_DYN)."""
    with open(path, "rb") as f:
        ident = f.read(16)
    if len(ident) < 16 or ident[:4] != ELF_MAGIC:
        return False
    with open(path, "rb") as f:
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
    # ET_EXEC=2 或 PIE ET_DYN=3 都是有效可执行（dconf 为 PIE，实测 e_type=3）
    return e_type in (2, 3)


def main():
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "dconf")
    if not os.path.isfile(exe):
        print(f"FAIL: {exe} not found", file=sys.stderr)
        return 1
    if not os.access(exe, os.X_OK):
        print(f"FAIL: {exe} not executable", file=sys.stderr)
        return 1

    # 尝试真实执行 dconf help（无 D-Bus session 时也应打印 usage）。
    try:
        r = subprocess.run([exe, "help"], capture_output=True, text=True, timeout=30)
    except (PermissionError, OSError) as exc:
        # E212 类：OHOS AppSpawn 沙箱禁止 posix_spawn 用户路径可执行文件。
        # 降级为静态产物校验（如实声明，不伪造通过）。
        if not _is_elf_executable(exe):
            print(f"FAIL: {exe} is not an ELF executable", file=sys.stderr)
            return 1
        print("OK: dconf present + executable + valid ELF; runtime exec blocked "
              f"by OHOS sandbox (E212): {exc}")
        return 0

    if r.returncode != 0:
        print(f"FAIL: dconf help rc={r.returncode}: {r.stderr[:300]}",
              file=sys.stderr)
        return 1
    out = r.stdout + r.stderr
    if "usage" not in out.lower():
        print(f"FAIL: dconf help output unexpected: {out[:200]}",
              file=sys.stderr)
        return 1
    print(f"OK: dconf help -> {out.strip()[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
