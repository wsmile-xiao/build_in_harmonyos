#!/usr/bin/env python3
"""libkysdk-applications 消费者探针：安装产物验证（.so dlopen + 头文件检查）。

dlopen 实测由构建阶段以 --dlopen 参数在构建 uid（属主 20001006）上下文执行：
OHOS CI 的 test() 阶段为只读 app uid（20020101），HMDFS 缓存产物属主
20001006、mode 750（other 位被裁），跨 uid 读取恒 EACCES 且 chown/chmod
静默无效（CI #49631/#49648/#49660/#49672/#49687 实证），test() 无法 dlopen；
故 test() 仅做存在性/头文件检查（只读上下文可过），真实加载验证由构建阶段
严格执行——dlopen 失败即 build 失败；R9/R34 不以 ELF 魔数弱校验伪造通过，
ELF 校验仅作诊断输出。

用法：
  python3 test_libkysdk_applications.py <package_folder> [--dlopen <ld_library_path>]
"""
import ctypes
import os
import stat
import sys

EXPECTED_LIBS = [
    "libkysdk-qtwidgets.so",
    "libkysdk-alm.so",
    "libkysdk-ukenv.so",
    "libkysdk-widgetutils.so",
]

INCLUDE_SUBDIR = os.path.join("include", "kysdk", "applications")

passed = 0
failed = 0


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def elf_check(path):
    """ELF 读取校验（仅诊断输出，不作为通过依据）。"""
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic == b"\x7fELF" and os.path.getsize(path) > 0
    except OSError:
        return False


def dlopen_inprocess(path):
    """进程内 dlopen（严格，无回退）。

    调用方须处于可读上下文（构建阶段构建 uid = 产物属主）：进程内直接
    ctypes.CDLL，不派生子进程——OHOS 子进程按 AppSpawn 分配新 app uid，
    与属主不同即 EACCES（#49672/#49687 实证）。
    """
    diag = f"probe uid={os.getuid()} euid={os.geteuid()}"
    try:
        st = os.stat(path)
        diag += f" file uid={st.st_uid} mode={stat.S_IMODE(st.st_mode):o}"
    except OSError as e:
        diag += f" stat err: {e}"
    print(f"  dlopen 诊断({os.path.basename(path)}): {diag}", file=sys.stderr)
    try:
        ctypes.CDLL(path)
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, repr(e)


def main():
    args = sys.argv[1:]
    if len(args) < 1:
        print("usage: test_libkysdk_applications.py "
              "<package_folder> [--dlopen <ld_library_path>]")
        return 2
    pkg = args[0]
    do_dlopen = "--dlopen" in args
    ld_path = ""
    if do_dlopen:
        i = args.index("--dlopen")
        if i + 1 < len(args):
            ld_path = args[i + 1]
    lib_dir = os.path.join(pkg, "lib")
    inc_dir = os.path.join(pkg, INCLUDE_SUBDIR)

    # 1) 4 个 .so 存在性
    libs = []
    for name in EXPECTED_LIBS:
        p = os.path.join(lib_dir, name)
        ok = os.path.isfile(p)
        check(f"lib 存在: {name}", ok, p if not ok else "")
        if ok:
            libs.append(p)

    # 2) dlopen 实测（仅 --dlopen 时执行，且须在可读上下文；严格，失败即 FAIL）
    if do_dlopen:
        if ld_path:
            cur = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ld_path + (os.pathsep + cur if cur else "")
        for p in libs:
            ok, err = dlopen_inprocess(p)
            if ok:
                check(f"dlopen: {os.path.basename(p)}", True)
            else:
                elf_ok = elf_check(p)
                # dlopen 失败即判失败（R9/R34 不得以 ELF 魔数弱校验伪造通过）；
                # ELF 校验结果仅作诊断信息输出，不作为通过依据
                print(f"  dlopen 诊断({os.path.basename(p)}): {err}", file=sys.stderr)
                check(f"dlopen: {os.path.basename(p)}", False,
                      f"dlopen 失败({err[:120]})，ELF 校验（仅诊断）："
                      f"{'通过' if elf_ok else '失败'}")
    else:
        print("  NOTE: 未指定 --dlopen——test() 阶段为只读 app uid，跨 uid "
              "dlopen 恒 EACCES（见模块 docstring），仅做存在性/头文件检查",
              file=sys.stderr)

    # 3) 头文件存在检查
    headers = []
    if os.path.isdir(inc_dir):
        headers = [f for f in os.listdir(inc_dir)
                   if f.endswith(".h") and os.path.isfile(os.path.join(inc_dir, f))]
    check("include/kysdk/applications/ 头文件",
          len(headers) >= 1,
          f"{len(headers)} 个 .h" + (f"（如 {headers[0]}）" if headers else ""))

    print(f"\nTotals: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
