#!/usr/bin/env python3
"""kicad-library-utils 消费者测试（OHOS 侧真实运行上游官方测试）。

从被测包目录（test_package/conanfile.py 传入的 package_folder）按上游 Makefile
原样执行官方测试命令（unittest 体系 + 符号生成器冒烟，纯标准库）：

  * 上游 make test-klc-symbols
  * 上游 make test-klc-footprints（两条命令）
  * 上游 make test-symgen（from_csv_generator.py，纯标准库，无第三方依赖）

任一命令非零退出即失败。test-symgen 会在包内 symbol-generators/ 旁生成
BQ24004-example.kicad_sym（上游测试自身的设计行为），校验生成物存在且非空后
移除该单文件，保持包目录卫生。同时校验包内 klc-check 树完整（证明测试实质
依赖被测包，而非空壳运行）。

用法: test_klc_check.py <package_folder>
"""
import glob
import os
import subprocess
import sys

UTILS_SUBDIR = os.path.join("share", "kicad-library-utils")
CHECK_DIR = os.path.join(UTILS_SUBDIR, "klc-check")
SYMGEN_DIR = os.path.join(UTILS_SUBDIR, "symbol-generators")
CMD_TIMEOUT = 600  # 每条上游命令的兜底超时（秒）；真机实测全部在数秒内完成


def run_target(name, cmd):
    """运行一条上游测试命令；非零退出或超时判 FAIL 并回显输出尾部。"""
    print("[RUN] %s" % name)
    print("      cmd: %s" % " ".join(cmd))
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=CMD_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("[FAIL] %s (timeout after %ds)" % (name, CMD_TIMEOUT))
        return False
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    n_pass = sum(1 for ln in lines if " passed" in ln or "No errors" in ln)
    if proc.returncode != 0:
        for ln in lines[-30:]:
            print("      | %s" % ln)
        print("[FAIL] %s (exit %d)" % (name, proc.returncode))
        return False
    tail = lines[-1] if lines else "(no output)"
    print("      tail: %s" % tail)
    print("[PASS] %s (exit 0, %d upstream assertion line(s))" % (name, n_pass))
    return True


def run_symgen(py, pkg_root):
    """上游 make test-symgen：from_csv_generator.py 从示例 CSV 生成符号。

    上游命令无 --output，生成物落在输入 CSV 旁（BQ24004-example.kicad_sym）。
    断言：退出码 0 + 生成物存在且非空；随后移除该单文件保持包目录卫生
    （移除失败仅提示，不影响判定）。
    """
    gen = os.path.join(pkg_root, SYMGEN_DIR, "from_csv_generator.py")
    csv_in = os.path.join(pkg_root, SYMGEN_DIR, "BQ24004-example.csv")
    sym_out = os.path.join(pkg_root, SYMGEN_DIR, "BQ24004-example.kicad_sym")
    name = "make test-symgen"
    print("[RUN] %s" % name)
    print("      cmd: %s -B %s %s" % (py, gen, csv_in))
    try:
        proc = subprocess.run([py, "-B", gen, csv_in], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              timeout=CMD_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("[FAIL] %s (timeout after %ds)" % (name, CMD_TIMEOUT))
        return False
    except OSError as exc:
        print("[FAIL] %s (%s)" % (name, exc))
        return False
    if proc.returncode != 0:
        for ln in proc.stdout.splitlines()[-30:]:
            print("      | %s" % ln)
        print("[FAIL] %s (exit %d)" % (name, proc.returncode))
        return False
    tail = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    print("      tail: %s" % (tail[-1] if tail else "(no output)"))
    if not (os.path.isfile(sym_out) and os.path.getsize(sym_out) > 0):
        print("[FAIL] %s (generated %s missing or empty)" % (name, sym_out))
        return False
    size = os.path.getsize(sym_out)
    try:
        os.remove(sym_out)  # 单文件、生成物路径明确；恢复包目录原状
        removed = "removed after check"
    except OSError as exc:
        removed = "note: cleanup failed (%s)" % exc
    print("[PASS] %s (exit 0, 1 case: generated BQ24004-example.kicad_sym "
          "%d bytes, %s)" % (name, size, removed))
    return True


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else ""
    check_dir = os.path.join(pkg_root, CHECK_DIR) if pkg_root else ""

    print("[1] package layout (consumer depends on the tested package)")
    layout_ok = True
    sym_tests = sorted(glob.glob(os.path.join(check_dir, "test_symbol", "*.kicad_symdir")))
    fp_tests = sorted(glob.glob(os.path.join(check_dir, "test_footprint.pretty", "*__*.kicad_mod")))
    checks = [
        ("klc-check/check_symbol.py installed",
         os.path.isfile(os.path.join(check_dir, "check_symbol.py"))),
        ("klc-check/test_symbol/ has upstream test data (%d .kicad_symdir)" % len(sym_tests),
         len(sym_tests) > 0),
        ("klc-check/test_footprint.pretty/ has upstream test data (%d __*.kicad_mod)" % len(fp_tests),
         len(fp_tests) > 0),
    ]
    for label, ok in checks:
        print("  [%s] %s" % ("OK" if ok else "FAIL", label))
        layout_ok = layout_ok and ok
    if not layout_ok:
        print("\nRESULT: FAILED (package layout incomplete: %r)" % pkg_root)
        return 1

    so8 = os.path.join(check_dir, "test_footprint.pretty",
                       "SO-8_3.9x4.9mm_P1.27mm.kicad_mod")
    py = sys.executable or "python3"

    print("\n[2] upstream Makefile tests (test-klc-symbols / test-klc-footprints)")
    targets = [
        ("make test-klc-symbols",
         [py, "-B", os.path.join(check_dir, "check_symbol.py"), "--unittest"] + sym_tests),
        ("make test-klc-footprints (unittest)",
         [py, "-B", os.path.join(check_dir, "check_footprint.py"), "--unittest"] + fp_tests),
        ("make test-klc-footprints (SO-8 single -vv)",
         [py, "-B", os.path.join(check_dir, "check_footprint.py"), "-vv", so8]),
    ]
    all_ok = True
    for name, cmd in targets:
        all_ok = run_target(name, cmd) and all_ok

    print("\n[3] upstream Makefile test-symgen (pure stdlib symbol generator)")
    all_ok = run_symgen(py, pkg_root) and all_ok

    print("\nRESULT: %s" % ("PASSED" if all_ok else "FAILED"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
