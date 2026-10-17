#!/usr/bin/env python3
"""Consumer test for the packaged `teller` 2.0.7 binary on HarmonyOS PC.

A. 通用消费者冒烟测试 —— 运行打包的 teller，验证 --version / --help 与
   端到端功能（export json / scan，使用临时目录内的 .env，无外部服务依赖）。
B. 鸿蒙特有测试（HarmonyOS-specific）—— 断言产物在本平台可用所必需的特性：
   B1. ELF machine = AArch64（OHOS PC 目标）
   B2. PT_INTERP = OHOS musl loader（证明是 OHOS bionic/musl 二进制，
       而非 glibc Linux 二进制）
   B3. 含 OHOS code signature —— HarmonyOS 拒绝 execve 未签名 ELF
       （EACCES errno 13），正是配方 _sign_binaries() 修复的失败点
   B4. 产物为非空普通可执行文件

每条断言单独打印，便于与 PR / reports 中的统计数字对齐。
"""

import os
import struct
import subprocess
import sys
import tempfile

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}",
              file=sys.stderr)
    return ok


def elfinfo(path):
    """Return (e_machine, interp) or (None, None) when unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, None
    if data[:4] != b"\x7fELF":
        return None, None
    e_machine = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = (data[p_offset:p_offset + p_filesz]
                      .rstrip(b"\x00").decode("utf-8", "replace"))
            break
    return e_machine, interp


def run(cmd, cwd=None, timeout=60):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          timeout=timeout)


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    exe = os.path.join(package_folder, "bin", "teller")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    if not check("B4: teller is a non-empty regular executable file",
                 os.path.isfile(exe) and os.path.getsize(exe) > 0,
                 f"{exe} ({os.path.getsize(exe) if os.path.isfile(exe) else 0} bytes)"):
        raise AssertionError(f"Missing teller executable: {exe}")

    e_machine, interp = elfinfo(exe)
    check("B1: ELF machine is AArch64 (EM_AARCH64=183)",
          e_machine == EM_AARCH64, f"e_machine={e_machine}")
    check(f"B2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
          interp is not None and OHOS_MUSL_LOADER in interp, f"interp={interp}")

    with open(exe, "rb") as fh:
        payload = fh.read()
    check("B3: OHOS code signature present (unsigned ELF cannot execve)",
          b"codesign" in payload)

    # ── A. 通用消费者冒烟测试 ──
    print("== 消费者冒烟测试 / consumer smoke test ==")
    version = run([exe, "--version"])
    check("A1: `teller --version` exits 0", version.returncode == 0,
          f"rc={version.returncode} err={version.stderr.strip()[:120]}")
    check("A2: `--version` reports 2.0.7",
          "2.0.7" in version.stdout, version.stdout.strip()[:80])

    help_run = run([exe, "--help"])
    check("A3: `teller --help` exits 0 and lists subcommands",
          help_run.returncode == 0 and "export" in help_run.stdout and
          "scan" in help_run.stdout,
          f"rc={help_run.returncode}")

    # 端到端功能（dotenv provider，无外部服务依赖）
    with tempfile.TemporaryDirectory(prefix="teller-test-") as tmp:
        with open(os.path.join(tmp, ".teller.yml"), "w",
                  encoding="utf-8") as fh:
            fh.write("providers:\n"
                     "  dot1:\n"
                     "    kind: dotenv\n"
                     "    maps:\n"
                     "      - id: one\n"
                     "        path: .env\n")
        with open(os.path.join(tmp, ".env"), "w", encoding="utf-8") as fh:
            fh.write("FOO_BAR=foo\nTELLER_TEST=harmonyos\n")

        export = run([exe, "export", "json"], cwd=tmp)
        check("A4: `teller export json` reads .env end-to-end",
              export.returncode == 0 and
              '{"FOO_BAR":"foo","TELLER_TEST":"harmonyos"}' in export.stdout,
              f"rc={export.returncode} out={export.stdout.strip()[:120]}")

        scan = run([exe, "scan"], cwd=tmp)
        scan_out = scan.stdout + scan.stderr
        check("A5: `teller scan` finds the secrets in .env",
              scan.returncode == 0 and "found 2 result(s)" in scan_out,
              f"rc={scan.returncode} out={scan_out.strip()[:160]}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("teller test_package OK: HarmonyOS traits + end-to-end CLI verified")


if __name__ == "__main__":
    sys.exit(main())
