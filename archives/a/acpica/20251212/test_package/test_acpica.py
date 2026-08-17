#!/usr/bin/env python3
"""test_package — acpica 消费验证（L0d: test() 必须 self.run）。

验证 bin/iasl 存在且为合法 ELF 可执行文件，并实际编译一个简单 ASL 测试
文件验证 ACPI 编译器可用（headless 无显示依赖）。
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile


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


# 最小 ACPI 源语言（ASL）测试文件：定义表头 + 空 DSDT
TEST_ASL = """/*
 * Minimal ACPI Source Language (ASL) test for iASL verification.
 */
DefinitionBlock ("test.aml", "DSDT", 2, "ACPI", "TEST", 0x00000001)
{
    Name (_HID, "ACPI0007")
}
"""


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    bins = os.path.join(pkg, "bin")
    iasl = os.path.join(bins, "iasl")
    if not os.path.isfile(iasl):
        print(f"FAIL: missing {iasl}")
        return 1
    ok, kind = check_elf(iasl)
    if not ok:
        print(f"FAIL: {iasl} {kind}")
        return 1
    print(f"OK: iasl is {kind} executable")

    # iasl 编译测试 ASL → test.aml（finally 中清理临时目录，避免残留）
    workdir = tempfile.mkdtemp(prefix="acpica-test-")
    asl_path = os.path.join(workdir, "test.asl")
    with open(asl_path, "w") as f:
        f.write(TEST_ASL)
    try:
        r = subprocess.run([iasl, "-p", os.path.join(workdir, "out"), asl_path],
                           capture_output=True, text=True, timeout=60,
                           cwd=workdir)
        out = (r.stdout or "") + (r.stderr or "")
        aml = os.path.join(workdir, "out.aml")
        if r.returncode == 0 and os.path.isfile(aml) and os.path.getsize(aml) > 0:
            print(f"OK: iasl compiled ASL -> out.aml ({os.path.getsize(aml)} bytes)")
        else:
            print(f"FAIL: iasl compile failed rc={r.returncode}: {out[-400:]}")
            return 1
    except Exception as e:
        print(f"FAIL: iasl compile error: {e}")
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
