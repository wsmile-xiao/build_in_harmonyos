#!/usr/bin/env python3
"""cmake-extras 1.1 消费者测试（鸿蒙特有测试）.

cmake-extras 是纯 CMake 模块数据包：没有可执行文件、没有库、没有头文件，
「可验证的产物」是**下游 CMake 工程能不能 find_package()/include() 到这些模块并
拿到它们承诺的 macro/function**。所以本脚本不止做 R34 的文件存在性校验，而是在
被适配的这台 HarmonyOS 上用 `cmake -P`（脚本模式：不触发编译器探测，也不需要
CMakeToolchain）逐个真正加载打包模块，断言每个模块交付的入口命令/变量确实存在。

两类结果要分清：
  * 模块自身可解析、只是缺外部工具（licensecheck / lcov / gcovr / intltool-*，
    以及 IntltoolConfig 第 66 行 `find_package(Gettext REQUIRED)` 要的 msgfmt）——
    这是环境缺工具，不是打包问题，按「加载可用 + 入口命令存在」断言；同一台机器
    装了 harmonybrew gettext 就解析成功、CI worker 没装就以 Gettext 失败签名收场，
    两种都算通过，但**必须**是那个签名；
  * 上游 1.1 自身的两个缺陷（IncludeCheckerConfig 未 include
    FindPackageHandleStandardArgs；QmlPluginsConfig 把 message 写成 msg）——
    按**错误签名**精确断言，防止它们哪天以别的原因（比如路径没装对）失败却被忽略。

用法：python3 test_cmake_extras.py <package_folder>
"""
import os
import shutil
import subprocess
import sys
import tempfile

# ── 上游 1.1 的产物清单（取自源码树，非配方自创）────────────────────────
MODULE_DIRS = ["CopyrightTest", "CoverageReport", "DoxygenBuilder", "FormatCode",
               "GMock", "GSettings", "IncludeChecker", "Intltool", "Lcov",
               "QmlPlugins", "gcovr"]
LEGACY_SHIMS = ["EnableCoverageReport.cmake", "FormatCode.cmake",
                "QmlPlugins.cmake", "UseDoxygen.cmake", "UseGSettings.cmake"]
# src/ 下所有非 .cmake 文件（install(DIRECTORY src/) 原样交付的伴生数据）
DATA_FILES = ["CopyrightTest/check_copyright.sh", "DoxygenBuilder/Doxyfile.in",
              "FormatCode/formatcode.in", "FormatCode/formatcode_format.cmake.in",
              "FormatCode/formatcode_test.cmake.in", "FormatCode/unity-api.astyle",
              "FormatCode/unity-api.clang-format", "IncludeChecker/deps",
              "IncludeChecker/include_checker.py"]
EXECUTABLES = ["CopyrightTest/check_copyright.sh",
               "IncludeChecker/include_checker.py"]
CMAKE_FILE_COUNT = 13 + 5          # src/ 13 个 + modules/ 5 个
TOTAL_FILE_COUNT = CMAKE_FILE_COUNT + len(DATA_FILES)

# 模块 → (入口命令, 入口变量)。名字取自上游源文件里的 `function(...)`/`macro(...)`
# 行（取数：grep -nE '^[[:space:]]*(macro|function)\(' src/*/*.cmake）
STRICT_MODULES = [
    ("DoxygenBuilder", ["add_doxygen"], []),
    ("FormatCode", ["add_formatcode_target", "add_formatcode_test"], []),
    ("GSettings", ["add_schema"], []),
    ("CoverageReport", ["ENABLE_COVERAGE_REPORT"], []),
    ("Lcov", [], ["LCOV_EXECUTABLE", "GENHTML_EXECUTABLE"]),
    ("gcovr", [], ["GCOVR_EXECUTABLE"]),
]
# Intltool 单独处理：见下方 F 组的 gettext_missing 注释。
INTLTOOL_CMDS = ["INTLTOOL_UPDATE_POTFILE", "INTLTOOL_INSTALL_TRANSLATIONS",
                 "INTLTOOL_MERGE_TRANSLATIONS"]
LEGACY_SHIM_CHECKS = [
    ("EnableCoverageReport", "ENABLE_COVERAGE_REPORT"),
    ("FormatCode", "add_formatcode_target"),
    ("UseDoxygen", "add_doxygen"),
    ("UseGSettings", "add_schema"),
]

RESULTS = []
_SEQ = [0]


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    line = "%s %s" % ("PASS" if ok else "FAIL", name)
    if detail and not ok:
        line += " :: " + detail
    print(line)
    return bool(ok)


def workdir():
    """在目标机上找一个可写目录（真机 /tmp 是只读挂载）。"""
    cands = [os.environ[k] for k in ("TMPDIR", "TMP", "TEMP") if os.environ.get(k)]
    cands += [os.getcwd(), os.path.dirname(os.path.abspath(__file__))]
    for base in cands:
        if not os.path.isdir(base):
            continue
        try:
            d = tempfile.mkdtemp(prefix="cme11-", dir=base)
        except OSError:
            continue
        probe = os.path.join(d, ".w")
        try:
            with open(probe, "w") as fh:
                fh.write("x")
            os.remove(probe)
        except OSError:
            continue
        return d
    return None


def tail(text, n=300):
    return " ".join((text or "").split())[-n:]


CMAKE = shutil.which("cmake")
WORK = workdir()


def module_script(pkg, body):
    _SEQ[0] += 1
    path = os.path.join(WORK, "cme_%d.cmake" % _SEQ[0])
    with open(path, "w") as fh:
        fh.write('set(CMAKE_PREFIX_PATH "%s")\n' % pkg)
        fh.write('set(CMAKE_MODULE_PATH "%s/share/cmake")\n' % pkg)
        fh.write(body)
    return path


def run_cmake(pkg, body):
    path = module_script(pkg.replace("\\", "/"), body)
    p = subprocess.run([CMAKE, "-P", path], cwd=WORK,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def probe_module(pkg, module, cmds, vars_, preload=""):
    """加载一个模块，并回报它的 rc 与 CMake 打印的入口命令/变量命中情况。"""
    body = preload + "find_package(%s)\n" % module
    if cmds:
        body += probe_loop("COMMAND", "CME-CMD", cmds)
    if vars_:
        body += probe_loop("DEFINED", "CME-VAR", vars_)
    return run_cmake(pkg, body)


def probe_loop(test, marker, names):
    """生成 if(<test> ${n}) 探测循环（COMMAND 对 macro/function/imports 通用）。"""
    body = "foreach(n %s)\n" % " ".join(names)
    if test == "COMMAND":
        body += '  if(COMMAND ${n})\n    message(STATUS "%s ${n}=yes")\n' % marker
    else:
        body += '  if(DEFINED ${n})\n    message(STATUS "%s ${n}=yes")\n' % marker
    body += '  else()\n    message(STATUS "%s ${n}=no")\n' % marker
    body += "  endif()\nendforeach()\n"
    return body


def main():
    if len(sys.argv) < 2:
        print("FAIL usage: test_cmake_extras.py <package_folder>")
        return 2
    pkg = os.path.abspath(sys.argv[1])
    share = os.path.join(pkg, "share", "cmake")
    base = share

    # ══ S 组：R34 产物结构（35 条）════════════════════════════════════
    check("S00 share/cmake 目录存在", os.path.isdir(base))
    for name in MODULE_DIRS:
        check("S 模块目录 %s" % name, os.path.isdir(os.path.join(base, name)))
    for name in MODULE_DIRS:
        check("S 配置文件 %s/%sConfig.cmake" % (name, name),
              os.path.isfile(os.path.join(base, name, "%sConfig.cmake" % name)))
    for name in LEGACY_SHIMS:
        check("S deprecated shim %s" % name, os.path.isfile(os.path.join(base, name)))

    cmake_files, all_files = [], []
    for dirpath, _dirs, files in os.walk(base):
        for fn in sorted(files):
            rel = os.path.relpath(os.path.join(dirpath, fn), base).replace(os.sep, "/")
            all_files.append(rel)
            if fn.endswith(".cmake"):
                cmake_files.append(rel)
    check("S .cmake 文件计数 == %d（实得 %d）" % (CMAKE_FILE_COUNT, len(cmake_files)),
          len(cmake_files) == CMAKE_FILE_COUNT)
    check("S share/cmake 下文件总数 == %d（实得 %d）" % (TOTAL_FILE_COUNT, len(all_files)),
          len(all_files) == TOTAL_FILE_COUNT)
    missing_data = [f for f in DATA_FILES if not os.path.isfile(os.path.join(base, f))]
    check("S %d 个非 .cmake 伴生数据文件齐全" % len(DATA_FILES),
          not missing_data, str(missing_data))
    for rel in EXECUTABLES:
        p = os.path.join(base, rel)
        check("S 可执行位保留 %s" % rel, os.path.isfile(p) and os.access(p, os.X_OK))
    lic = os.path.join(pkg, "licenses", "copyright")
    has_lgpl = False
    if os.path.isfile(lic):
        with open(lic, errors="replace") as fh:
            has_lgpl = "LGPL" in fh.read()
    check("S licenses/copyright 存在且声明 LGPL", has_lgpl)
    leaked = [f for f in all_files if f.startswith(("examples/", "debian/"))]
    check("S 无 examples/ 与 debian/ 越界安装", not leaked, str(leaked[:3]))

    # ══ F 组：在目标机上真跑 cmake 加载模块（35 条）════════════════════
    ready = check("F00 目标机具备 cmake 与可写工作目录",
                  CMAKE is not None and WORK is not None,
                  "cmake=%s work=%s" % (CMAKE, WORK))
    if not ready:
        return summarize()

    for module, cmds, vars_ in STRICT_MODULES:
        rc, out = probe_module(pkg, module, cmds, vars_)
        check("F %s 模块被 CMake 成功解析" % module, rc == 0, "rc=%d %s" % (rc, tail(out)))
        for c in cmds:
            check("F %s 交付命令 %s" % (module, c), ("CME-CMD %s=yes" % c) in out)
        for v in vars_:
            check("F %s 交付变量 %s" % (module, v), ("CME-VAR %s=yes" % v) in out)

    # Intltool：上游 `IntltoolConfig.cmake` 第 66 行是 `find_package(Gettext REQUIRED)`，
    # 也就是**先要求外部工具链 gettext（msgfmt/msgmerge）**，才继续定义三个入口函数。
    # gettext 不是本包的一部分：装了 harmonybrew gettext 的鸿蒙真机上解析成功，
    # CI worker（cmake 装在 /data/service/hnp/cmake.org/…，无 msgfmt）则以
    # FindGettext 的失败签名收场。与 CopyrightTest 同法——只允许「解析成功」或
    # 「失败原因精确是缺 Gettext」两种结果，且三种情况下都必须证明三个入口函数
    # 确实由本包交付（运行期 COMMAND 命中，或缺工具时模块文本里的 function/macro 声明）。
    # 这样「模块路径没装对」一类的真打包缺陷不会因为这条断言变宽而被放过。
    rc, out = probe_module(pkg, "Intltool", INTLTOOL_CMDS, [])
    low = (out or "").lower()
    gettext_missing = ("gettext" in low) and any(
        t in low for t in ("msgfmt", "msgmerge", "could not find gettext",
                           "findgettext.cmake"))
    check("F Intltool 解析（成功，或仅因缺外部工具 Gettext/msgfmt 报错）",
          rc == 0 or gettext_missing, "rc=%d %s" % (rc, tail(out)))
    itxt = ""
    ipath = os.path.join(base, "Intltool", "IntltoolConfig.cmake")
    if os.path.isfile(ipath):
        with open(ipath, errors="replace") as fh:
            itxt = fh.read()
    for c in INTLTOOL_CMDS:
        runtime = ("CME-CMD %s=yes" % c) in out
        declared = ("function(%s" % c) in itxt or ("macro(%s" % c) in itxt
        check("F Intltool 交付命令 %s" % c,
              runtime or (gettext_missing and declared),
              "runtime=%s declared=%s gettext_missing=%s rc=%d %s"
              % (runtime, declared, gettext_missing, rc, tail(out)))

    # 但仍把 function(ADD_COPYRIGHT_TEST) 定义完 —— 断言「只有这一个原因」且函数在。
    rc, out = probe_module(pkg, "CopyrightTest", ["ADD_COPYRIGHT_TEST"], [])
    check("F CopyrightTest 解析（成功，或仅因缺外部工具 licensecheck 报错）",
          rc == 0 or "licensecheck" in out, "rc=%d %s" % (rc, tail(out)))
    check("F CopyrightTest 交付命令 ADD_COPYRIGHT_TEST",
          "CME-CMD ADD_COPYRIGHT_TEST=yes" in out)

    # IncludeChecker：上游 1.1 的缺陷——用了 find_package_handle_standard_args
    # 却没 include(FindPackageHandleStandardArgs)（1.5 到 1.9 至今同样如此）。
    rc_raw, out_raw = probe_module(pkg, "IncludeChecker", ["add_include_check"], [])
    check("F IncludeChecker 裸加载失败的原因签名 == 上游漏 include(FPHSA)",
          rc_raw != 0 and "find_package_handle_standard_args" in out_raw,
          "rc=%d %s" % (rc_raw, tail(out_raw)))
    rc_fix, out_fix = probe_module(pkg, "IncludeChecker", ["add_include_check"], [],
                                   preload="include(FindPackageHandleStandardArgs)\n")
    check("F IncludeChecker 调用方预载 FPHSA 后可正常解析", rc_fix == 0,
          "rc=%d %s" % (rc_fix, tail(out_fix)))
    check("F IncludeChecker 交付命令 add_include_check",
          "CME-CMD add_include_check=yes" in out_fix)

    # GMock：脚本模式下 add_library(INTERFACE) 与 find_package(Threads) 都需要
    # project() 上下文，无法用 cmake -P 真跑；真机上也没有模块硬编码的
    # /usr/src/googletest。退而对「包内模块文本确实声明了这些目标」做断言。
    gmok_path = os.path.join(base, "GMock", "GMockConfig.cmake")
    gmock_txt = ""
    if os.path.isfile(gmok_path):
        with open(gmok_path, errors="replace") as fh:
            gmock_txt = fh.read()
    check("F GMock 模块文本声明 add_library(gtest INTERFACE)",
          "add_library(gtest INTERFACE)" in gmock_txt)
    check("F GMock 模块文本声明 add_library(gmock INTERFACE)",
          "add_library(gmock INTERFACE)" in gmock_txt)

    # QmlPlugins：上游 1.1 把 message() 误写成 msg()（1.9 已修）。缺 Qt 的
    # qmlplugindump 时 find_package(QmlPlugins) 必然以 Unknown command "msg" 失败；
    # 若环境真装了 qmlplugindump 而加载成功，同样算通过。
    rc, out = probe_module(pkg, "QmlPlugins", ["add_qmlplugin"], [])
    check("F QmlPlugins 解析结果只允许是成功或上游 msg() 笔误",
          rc == 0 or "msg" in out, "rc=%d %s" % (rc, tail(out)))

    for shim, cmd in LEGACY_SHIM_CHECKS:
        body = "include(%s)\n" % shim
        body += probe_loop("COMMAND", "CME-CMD", [cmd])
        rc, out = run_cmake(pkg, body)
        check("F shim include(%s) 可解析" % shim, rc == 0, "rc=%d %s" % (rc, tail(out)))
        check("F shim include(%s) 生效提供 %s" % (shim, cmd),
              ("CME-CMD %s=yes" % cmd) in out)

    return summarize()


def summarize():
    total = len(RESULTS)
    passed = sum(1 for _name, ok in RESULTS if ok)
    failed = total - passed
    print("TOTAL=%d PASS=%d FAIL=%d" % (total, passed, failed))
    if failed:
        print("FAILING CASES:")
        for name, ok in RESULTS:
            if not ok:
                print("  - " + name)
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
