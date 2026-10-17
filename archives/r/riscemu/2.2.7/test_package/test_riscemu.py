#!/usr/bin/env python3
"""test_riscemu.py — consumer test source for riscemu 2.2.7 (L0c).

消费者视角的真实 API 测试（R34）：把 conan 配方刚刚装出来的 riscemu 当作第三方
库使用，而不是只 import 一下。覆盖：

  A. 包身份 —— `riscemu.__file__` 必须落在本次被验证的 site-packages 内（防止
     误从源码树导入），版本/作者取自包内 dist-info 元数据。
  B. 运行时依赖闭包 —— riscemu.riscemu_main 顶层 `import importlib_resources`
     必须成立且能读出包内 `riscemu.libc` 的 crt0.s/stdlib.s/string.s 资源；
     pyelftools（ELF 加载后端）必须能真正解析一个真实 ELF 文件。
  C. 核心 API —— riscemu.core 的 Int32/UInt32/Float32/Float64 语义、decoder 反
     汇编、指令集注册表、CSR、helpers，断言值与上游 pytest 套件同一口径。
  D. 端到端模拟 —— 用打包出来的 `python3 -m riscemu` 与 console script
     `bin/riscemu` 真跑 RISC-V 汇编，校验程序输出、libc 运行时与退出码传递。
  E. 程序化 API —— RiscemuMain + RunConfig 直接跑程序，校验寄存器/退出码/停机位。

成功时输出 HMBS_TEST_PACKAGE_RESULT 标记与真实断言计数。
用法: test_riscemu.py <site-packages-dir>
"""
import json
import math
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROGRAMS = os.path.join(SCRIPT_DIR, "programs")
FILECHECK = os.path.join(SCRIPT_DIR, "filecheck")
ELF_MAGIC = b"\x7fELF"

# `add a0, a0, a1` (opcode/funct3/funct7 = 0110011/000/0000000), little endian
ADD_A0_A0_A1 = bytes([0x33, 0x05, 0xB5, 0x00])

# test/filecheck/fibs.asm exits with this code (checked by the upstream lit suite);
# the process exit status is truncated to 8 bits by the OS.
FIBS_EXIT_CODE = 1265227608
# examples/static-data.asm leaves 0xCCDDEEFF in a0 and exits with it.
STATIC_DATA_A0 = 0xCCDDEEFF
STATIC_DATA_WORDS = ("11223344", "55667788", "9900aabb", "ccddeeff")


def check(cond, name, results):
    results.append((name, bool(cond)))


def find_elf_sample():
    """First real ELF file on this system (used to exercise pyelftools for real)."""
    for path in (sys.executable, "/proc/self/exe", "/bin/sh", "/usr/bin/env"):
        try:
            with open(path, "rb") as fh:
                if fh.read(4) == ELF_MAGIC:
                    return path
        except OSError:
            continue
    return None


def run(cmd, env, timeout=120):
    # stdin is detached on purpose (DEVNULL). Some upstream programs drop into
    # riscemu's interactive debugger, which reads commands from stdin: fibs.asm
    # ends with `ebreak`, and the debugger then waits for input at the prompt.
    # On a CI runner the inherited stdin is an open pipe that never delivers
    # data and never reaches EOF, so an inherited stdin turns that run into a
    # hang until the timeout expires (observed on the PR build worker). The
    # upstream lit suite does not have this problem because lit closes the
    # child's stdin right after spawning it (lit/TestRunner.py), which the
    # process sees as an immediate EOF. Passing /dev/null reproduces exactly
    # that behaviour, so the debugger exits deterministically instead of
    # blocking, on every runner.
    proc = subprocess.run(
        cmd,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=timeout,
        cwd=SCRIPT_DIR,
    )
    return (
        proc.returncode,
        (proc.stdout or b"").decode(errors="replace"),
        (proc.stderr or b"").decode(errors="replace"),
    )


def run_checks(sp, env, results):
    python = sys.executable

    # ── A. package identity ────────────────────────────────────────────────
    check(os.path.isdir(os.path.join(sp, "riscemu")), "site_packages_has_riscemu", results)
    import riscemu

    check(
        os.path.realpath(riscemu.__file__).startswith(sp + os.sep),
        "riscemu_imported_from_verified_package",
        results,
    )
    check(riscemu.__version__ == "2.2.7", "module_version_is_2_2_7", results)
    check(riscemu.__author__.startswith("Anton Lydike"), "module_author", results)
    check("Copyright 2023" in riscemu.__copyright__, "module_copyright", results)
    import importlib.metadata as md

    check(md.version("riscemu") == "2.2.7", "dist_metadata_version", results)
    check(
        os.path.isdir(os.path.join(sp, "riscemu-2.2.7.dist-info")),
        "dist_info_present",
        results,
    )

    # ── B. runtime dependency closure ─────────────────────────────────────
    # (importing the CLI entry module is itself the proof that the top level
    #  `import importlib_resources` of riscemu.riscemu_main resolves)
    from riscemu.riscemu_main import RiscemuMain, RiscemuSource  # noqa: F401

    check(True, "entry_module_importlib_resources_import", results)

    import importlib_resources

    ir_version = tuple(int(p) for p in md.version("importlib_resources").split(".")[:2])
    check(ir_version >= (6, 1), "importlib_resources_meets_declared_floor", results)
    libc = importlib_resources.files("riscemu.libc")
    libc_names = {p.name for p in libc.iterdir()}
    check(
        {"crt0.s", "stdlib.s", "string.s"} <= libc_names,
        "packaged_libc_resources_present",
        results,
    )
    crt0 = (libc / "crt0.s").read_text()
    check(
        len(crt0) > 100 and "_start" in crt0,
        "packaged_libc_crt0_readable",
        results,
    )

    import elftools
    from elftools.elf.elffile import ELFFile

    check(elftools.__version__ == "0.30", "pyelftools_version_is_0_30", results)
    elf_path = find_elf_sample()
    check(elf_path is not None, "elf_sample_available", results)
    if elf_path:
        with open(elf_path, "rb") as fh:
            elf = ELFFile(fh)
            check(elf.elfclass in (32, 64), "pyelftools_elfclass", results)
            check(
                str(elf.header["e_machine"]).startswith("EM_"),
                "pyelftools_header_e_machine",
                results,
            )
            check(
                sum(1 for _ in elf.iter_sections()) > 0,
                "pyelftools_iter_sections",
                results,
            )

    # ── C. core API ────────────────────────────────────────────────────────
    from riscemu.core import CPU, Float32, Float64, Int32, UInt32  # noqa: F401

    check(
        Int32.MIN_VALUE == -(2**31) and Int32.MAX_VALUE == 2**31 - 1,
        "int32_bounds",
        results,
    )
    check(
        int(Int32(Int32.MAX_VALUE) + 1) == Int32.MIN_VALUE,
        "int32_wraparound",
        results,
    )
    check(
        int(Int32(-100).shift_right_logical(1)) == 2147483598,
        "int32_logical_right_shift",
        results,
    )
    check(int(UInt32(-1)) == 0xFFFFFFFF, "uint32_wraparound", results)
    check(
        int(Int32.from_float(float("inf"))) == Int32.MAX_VALUE
        and int(Int32.from_float(float("nan"))) == Int32.MIN_VALUE,
        "int32_from_float_special_values",
        results,
    )
    check(Float32(math.pi).bytes == b"\xdb\x0fI@", "float32_serialisation", results)
    check(
        Float64.bitcast(Float32(math.pi)).bytes[:4] == b"\x00\x00\x00\x00",
        "float64_bitcast_float32",
        results,
    )
    check(
        float(Float32(5) ** 2) == 25.0 and float(Float32(9) ** 0.5) == 3.0,
        "float32_arithmetic",
        results,
    )

    from riscemu.decoder import RISCV_REGS, decode, format_ins

    check(
        RISCV_REGS[:5] == ["zero", "ra", "sp", "gp", "tp"] and len(RISCV_REGS) == 32,
        "riscv_register_table",
        results,
    )
    name, args, insn = decode(ADD_A0_A0_A1)
    check(
        (name, args, insn) == ("add", [10, 10, 11], 0x00B50533),
        "decoder_decodes_add",
        results,
    )
    check(
        format_ins(insn, name) == "add     a0, a0, a1",
        "decoder_formats_add",
        results,
    )

    from riscemu.instructions import InstructionSetDict

    check(
        {"RV32I", "RV32M", "RV32F", "RV32D", "RV32A", "Zicsr"} <= set(InstructionSetDict),
        "instruction_set_registry",
        results,
    )
    check(
        sum(1 for n in vars(InstructionSetDict["RV32I"]) if n.startswith("instruction_"))
        == 47,
        "rv32i_instruction_count",
        results,
    )
    check(
        {"instruction_mul", "instruction_div", "instruction_rem"}
        <= set(vars(InstructionSetDict["RV32M"])),
        "rv32m_instructions",
        results,
    )
    check(
        "instruction_csrrw" in vars(InstructionSetDict["Zicsr"]),
        "zicsr_instructions",
        results,
    )

    from riscemu.core.csr import MStatusRegister

    status = MStatusRegister()
    status.mpie = 1
    check(int(status.state) == 0x80, "mstatus_mpie_bit", results)
    status.mpie = 0
    status.mpp = 3
    check(int(status.state) == 0x1800, "mstatus_mpp_field", results)

    from riscemu.helpers import align_addr, create_chunks, parse_numeric_argument

    check(
        align_addr(3, 2) == 4 and align_addr(8, 8) == 8,
        "helpers_align_addr",
        results,
    )
    check(
        parse_numeric_argument("0x100") == 256 and parse_numeric_argument("-13") == -13,
        "helpers_parse_numeric_argument",
        results,
    )
    check(
        create_chunks(b"\x01\x02\x03\x04", 2) == [b"\x01\x02", b"\x03\x04"],
        "helpers_create_chunks",
        results,
    )

    # ── D. end-to-end emulation through the CLI ────────────────────────────
    rc, out, err = run([python, "-m", "riscemu", os.path.join(PROGRAMS, "hello-world.asm")], env)
    check(rc == 0, "cli_hello_world_exit_code_0", results)
    check("Hello world" in out, "cli_hello_world_stdout", results)

    rc, out, _err = run([python, "-m", "riscemu", os.path.join(PROGRAMS, "static-data.asm")], env)
    check(rc == STATIC_DATA_A0 & 0xFF, "cli_static_data_exit_code", results)
    check(
        all(f"0x{word}" in out for word in STATIC_DATA_WORDS),
        "cli_static_data_loads_all_words",
        results,
    )

    rc, out, _err = run(
        [python, "-m", "riscemu", "-v", os.path.join(FILECHECK, "libc", "test-string.s"), "-o", "libc"],
        env,
    )
    check(rc == 0, "cli_libc_test_string_exit_code_0", results)
    check(
        "Program exited with code 0" in out,
        "cli_libc_test_string_runtime_starts",
        results,
    )

    rc, out, _err = run(
        [python, "-m", "riscemu", "-v", os.path.join(FILECHECK, "fibs.asm"), "-o", "libc"],
        env,
    )
    check(rc == FIBS_EXIT_CODE & 0xFF, "cli_exit_code_propagated", results)
    check(
        f"Program exited with code {FIBS_EXIT_CODE}" in out,
        "cli_exit_code_reported",
        results,
    )

    rc, out, _err = run([python, "-m", "riscemu", "--help"], env)
    check(rc == 0 and "riscemu" in out, "cli_help", results)

    console_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(sp))), "bin", "riscemu"
    )
    check(os.path.isfile(console_script), "console_script_installed", results)
    check(os.access(console_script, os.X_OK), "console_script_executable", results)
    if os.path.isfile(console_script):
        rc, out, _err = run([console_script, os.path.join(PROGRAMS, "hello-world.asm")], env)
        check(
            rc == 0 and "Hello world" in out,
            "console_script_runs_program",
            results,
        )

    # ── E. programmatic API ────────────────────────────────────────────────
    from riscemu.config import RunConfig

    runner = RiscemuMain(
        RunConfig(
            verbosity=0,
            use_libc=False,
            debug_instruction=False,
            debug_on_exception=False,
        )
    )
    runner.register_all_isas()
    runner.register_all_program_loaders()
    runner.input_files.append(os.path.join(PROGRAMS, "static-data.asm"))
    runner.selected_ins_sets = list(runner.available_ins_sets.values())
    runner.run()
    check(
        int(runner.cpu.regs.get("a0")) == STATIC_DATA_A0 - (1 << 32),
        "api_register_value_after_run",
        results,
    )
    check(int(runner.cpu.regs.get("a7")) == 93, "api_exit_syscall_number", results)
    check(
        runner.cpu.exit_code & 0xFFFFFFFF == STATIC_DATA_A0,
        "api_exit_code",
        results,
    )
    check(bool(runner.cpu.halted), "api_cpu_halted", results)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_riscemu.py <site-packages-dir>")
    sp = os.path.realpath(sys.argv[1])
    if not os.path.isdir(os.path.join(sp, "riscemu")):
        raise SystemExit(f"riscemu package missing under {sp}")
    sys.path.insert(0, sp)

    env = dict(os.environ)
    env["PYTHONPATH"] = sp + (
        (os.pathsep + env["PYTHONPATH"]) if env.get("PYTHONPATH") else ""
    )

    results = []
    try:
        run_checks(sp, env, results)
    except Exception as exc:  # noqa: BLE001 - report the failure instead of dying silently
        check(False, f"unexpected_exception:{type(exc).__name__}:{exc}", results)

    passed = sum(1 for _name, ok in results if ok)
    total = len(results)
    ok = passed == total
    marker = {
        "executed": True,
        "passed": ok,
        "command": "python3 test_riscemu.py <site-packages-dir>",
        "discovered": total,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
    for name, result in results:
        print(f"  [{'ok' if result else 'FAIL'}] {name}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
