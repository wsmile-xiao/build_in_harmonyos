#!/usr/bin/env python3
"""test_package/test_rhai.py — rhai 消费者测试（含鸿蒙特有断言）。

用法: python3 test_rhai.py <package_folder>

A 组（消费者功能）: 脚本执行 / 运算结果 / 语法错误处理 / 帮助信息
B 组（鸿蒙特有）:   ELF machine=AArch64 / PT_INTERP=ld-musl-aarch64.so.1 /
                    OHOS code signature / 非空可执行
"""
import os
import struct
import subprocess
import sys
import tempfile

ASSERTIONS = []


def check(name, cond, detail=""):
    ASSERTIONS.append((name, bool(cond), detail))
    print(f"  [{'ok' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def elf_header(path):
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:4] == b"\x7fELF", "not an ELF file"
    is64 = data[4] == 2
    little = data[5] == 1
    endian = "<" if little else ">"
    e_machine = struct.unpack_from(endian + "H", data, 18)[0]
    # 解析 program headers 找 PT_INTERP
    if is64:
        e_phoff = struct.unpack_from(endian + "Q", data, 32)[0]
        e_phentsize = struct.unpack_from(endian + "H", data, 54)[0]
        e_phnum = struct.unpack_from(endian + "H", data, 56)[0]
    else:
        e_phoff = struct.unpack_from(endian + "I", data, 28)[0]
        e_phentsize = struct.unpack_from(endian + "H", data, 42)[0]
        e_phnum = struct.unpack_from(endian + "H", data, 44)[0]
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type = struct.unpack_from(endian + "I", data, off)[0]
        if p_type == 3:  # PT_INTERP
            if is64:
                p_offset = struct.unpack_from(endian + "Q", data, off + 8)[0]
                p_filesz = struct.unpack_from(endian + "Q", data, off + 32)[0]
            else:
                p_offset = struct.unpack_from(endian + "I", data, off + 4)[0]
                p_filesz = struct.unpack_from(endian + "I", data, off + 16)[0]
            interp = data[p_offset:p_offset + p_filesz].split(b"\x00")[0].decode()
    return e_machine, interp, data


def main():
    if len(sys.argv) != 2:
        print("usage: test_rhai.py <package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    run_bin = os.path.join(pkg, "bin", "rhai-run")
    dbg_bin = os.path.join(pkg, "bin", "rhai-dbg")

    print("== A. 消费者功能测试 ==")
    check("A0 rhai-run 存在", os.path.isfile(run_bin), run_bin)
    check("A1 rhai-dbg 存在", os.path.isfile(dbg_bin), dbg_bin)

    with tempfile.TemporaryDirectory() as td:
        script = os.path.join(td, "hello.rhai")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write("let x = 0;\nfor i in 0..10 { x += i; }\n"
                     "print(`sum=${x}`);\nprint(40 + 2);\n")
        try:
            out = subprocess.run([run_bin, script], capture_output=True,
                                 text=True, timeout=60)
            stdout = out.stdout
            rc = out.returncode
        except Exception as exc:  # pragma: no cover
            stdout, rc = "", -1
            print(f"  (exec error: {exc})")
        check("A2 脚本执行退出码为 0", rc == 0, f"rc={rc}")
        check("A3 脚本输出含 sum=45", "sum=45" in stdout, repr(stdout.strip()))
        check("A4 脚本输出含 42", "42" in stdout, repr(stdout.strip()))

        # 上游 rhai-run 对脚本语法/运行时错误仅打印诊断、退出码为 0
        # （src/bin/rhai_run.rs），因此断言诊断输出而非退出码。
        bad = os.path.join(td, "bad.rhai")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("fn foo( {\n")
        out = subprocess.run([run_bin, bad], capture_output=True, text=True,
                             timeout=60)
        check("A5 语法错误脚本报 Syntax error 诊断",
              "Syntax error" in (out.stdout + out.stderr),
              repr((out.stdout + out.stderr).strip()[:80]))

        # 文件缺失时返回非零（os error 2）
        out = subprocess.run([run_bin, os.path.join(td, "missing.rhai")],
                             capture_output=True, text=True, timeout=60)
        check("A6 缺失脚本文件返回非零退出码", out.returncode != 0,
              f"rc={out.returncode}")

    print("== B. 鸿蒙特有测试 ==")
    machine, interp, data = elf_header(run_bin)
    check("B1 ELF machine = AArch64(183)", machine == 183, f"machine={machine}")
    check("B2 PT_INTERP = ld-musl-aarch64.so.1",
          interp is not None and "ld-musl-aarch64.so.1" in interp, f"interp={interp}")
    check("B3 含 OHOS code signature 段",
          b"code_sign" in data or b"codesign" in data or b"Harmony" in data,
          f"size={len(data)}")
    check("B4 产物非空且可执行",
          len(data) > 100000 and os.access(run_bin, os.X_OK),
          f"{len(data)} bytes")

    total = len(ASSERTIONS)
    passed = sum(1 for _n, ok, _d in ASSERTIONS if ok)
    print(f"\n结果: {passed}/{total} 断言通过")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
