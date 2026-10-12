#!/usr/bin/env python3
"""Conan recipe — skint 0.6.8 (portable C11 R7RS-small Scheme interpreter).

上游构建系统：手写 Makefile（`make` 直接编译 5 个 .c 并 `-lm` 链接），
没有 CMake/autotools。仓库里那个 `configure` 只是把 `--prefix` 写进
`prefix.mk` 的 8 行 bash 脚本，配方不调用它 —— 顺带避开 E165
（OHOS 无 /bin/bash，shebang 指向不存在的路径）。

HarmonyOS 适配结论：零源码补丁。
  * `s.h` 的平台分派链在 clang/OHOS 上命中 `__GNUC__ && __linux` 分支
    （OHOS clang 同时定义 `__GNUC__`、`__linux`、`__OHOS__`），不会落到
    `#error "s.h: add your platform here"`；aarch64-linux-ohos 交叉编译零告警。
  * 构建参数是唯一适配面：CFLAGS 由配方整体钉死，禁用 makefile 里基于
    **构建机 uname** 的 `-D NAN_BOXING` 自动嗅探，也不把 `-DLIBDIR=/usr/local/...`
    编进产物 —— 交叉编译时那两处都会按构建机（而非目标机）取值。
  * 运行期只依赖 musl libc：`libm` 已并入 `libc.so`，产物 `DT_NEEDED` 只有
    `libc.so`（glibc 产物会多出 `libm.so.6`）。
  * 上游默认库搜索路径是 `.:lib:<LIBDIR>`；打包后通过 `runenv_info` 注入
    `SKINT_LIBDIRS=<package>/share/skint/lib`，把 SRFI 外置库树接上，
    保持包可重定位（不把构建期绝对路径烧进 ELF）。

上游测试：`build()` 里同一次构建内真实执行上游两套官方测试（can_run 时）
  * `test/test.scm`   —— R7RS-small 一致性套件，原生报告 1194 个 test case。
    注意 `test-end` 只打印汇总、**不设置退出码**，所以这里解析打印出来的
    `N out of M passed` 并按 `passed == run` 且 `run >= 1194` 判定，
    防静默跳过式假绿。
  * `test/srfi/*.scm` —— 111 个 SRFI 外置库用例，官方入口 `test/srfi/all.scm`
    汇总 "SRFIs TESTED" 与 "CUMULATIVE FAILURES"，退出码 = 失败数。
"""
import datetime
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get, save)
from conan.tools.layout import basic_layout

R7RS_SUITE = "test/test.scm"
SRFI_SUITE = "test/srfi/all.scm"
# 上游基线（未改动源码实测）：R7RS 一致性套件 1194 个 test case；
# SRFI 外置库套件 111 个模块。口径见 test_package/MANIFEST.yml。
R7RS_CASES_BASELINE = 1194
SRFI_MODULES_BASELINE = 111
SUMMARY_RE = re.compile(r"(\d+) out of (\d+) passed")


class SkintConan(ConanFile):
    name = "skint"
    version = "0.6.8"
    description = (
        "Portable, dependency-free interpreter for R7RS-small Scheme: precise "
        "GC, proper tail recursion, call/cc, dynamic-wind, hygienic macros, a "
        "library system and 100+ SRFI ports shipped as an external .sld tree"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/false-schemers/skint"
    url = "https://github.com/false-schemers/skint"
    topics = ("scheme", "r7rs", "interpreter", "srfi", "scripting")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # 本版本无补丁；保留以便后续适配需要时走同一导出路径。
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: OHOS 必须与 Linux 并列匹配，不能写成 == "Linux"。
        if self.settings.os not in ("Linux", "OHOS", "Macos", "FreeBSD"):
            raise ConanException(
                "skint 面向 POSIX 宿主（Linux/OHOS/macOS），s.h 没有 %s 分支"
                % self.settings.os)

    def _compiler(self):
        """R33: 编译器路径只从 Conan conf 取，绝不用裸 shell ${CC}。"""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        if compilers and compilers.get("c"):
            return compilers["c"]
        return "clang"

    def build(self):
        # 本版本 conandata 的 patches 为空，这里是空操作；保留调用是为了让
        # 后续需要补丁时走同一（并已被 conan-verify G1 校验的）路径。
        apply_conandata_patches(self)

        cc = self._compiler()
        src = self.source_folder
        # R9: -j1。命令行变量优先于 makefile 内赋值，CFLAGS 因此被整体钉死：
        # 不放行 makefile 的宿主 uname 架构嗅探（-D NAN_BOXING），也不编入
        # -DLIBDIR=/usr/local/...（交叉编译时会按构建机前缀取值）。
        self.run(
            'make -C "{src}" -j1 CC="{cc}" CFLAGS="-O2 -DNDEBUG" "./skint"'
            .format(src=src, cc=cc))

        exe = os.path.join(src, "skint")
        if not os.path.isfile(exe):
            raise ConanException("build(): make 没有产出 %s" % exe)
        # HMDFS/chmod guard (E046): 显式补可执行位。
        os.chmod(exe, 0o755)
        self._run_upstream_suites(exe)

    # ── 上游官方测试（层 1） ───────────────────────────────────────────
    def _run_upstream_suites(self, exe):
        evidence = os.path.join(self.build_folder, "upstream")
        os.makedirs(evidence, exist_ok=True)

        if not can_run(self):
            self.output.info(
                "cross-building: an aarch64-linux-ohos ELF cannot execute on "
                "this host, so the upstream R7RS + SRFI suites are deferred to "
                "the HarmonyOS CI worker (they are also re-driven by "
                "test_package on a real device)")
            return

        r7rs = self._run_suite(exe, R7RS_SUITE, os.path.join(evidence, "r7rs.log"))
        summary = _parse_summary(r7rs["text"])
        r7rs_passed, r7rs_run = summary if summary else (0, 0)
        # 上游 test-end 只打印汇总、不设置退出码，所以真正的判据是
        # 「汇总行存在 + passed == run + 用例数不少于上游基线」；rc 只作辅助校验。
        if (summary is None or r7rs_passed != r7rs_run
                or r7rs_run < R7RS_CASES_BASELINE or r7rs["rc"] != 0):
            raise ConanException(
                "上游 R7RS 一致性套件未全通过：%d/%d passed（上游基线 %d 个用例；"
                "退出码 %s；日志 %s）"
                % (r7rs_passed, r7rs_run, R7RS_CASES_BASELINE,
                   r7rs["rc"], r7rs["log"]))

        srfi = self._run_suite(exe, SRFI_SUITE, os.path.join(evidence, "srfi.log"))
        modules = _search_int(srfi["text"], r"SRFIs TESTED: (\d+)")
        failures = _search_int(srfi["text"], r"CUMULATIVE FAILURES: (\d+)")
        cases = sum(int(x) for x, _ in SUMMARY_RE.findall(srfi["text"]))
        if srfi["rc"] != 0 or failures != 0 or modules < SRFI_MODULES_BASELINE:
            raise ConanException(
                "上游 SRFI 套件未全通过：模块 %s、失败 %s、退出码 %s（上游基线 "
                "%d 个模块；日志 %s）"
                % (modules, failures, srfi["rc"], SRFI_MODULES_BASELINE,
                   srfi["log"]))

        result = {
            "framework": "skint-built-in-harness",
            "status": "passed",
            "count_method": "independent_check_items",
            "discovered": R7RS_CASES_BASELINE + modules,
            "executed": r7rs_run + modules,
            "passed": r7rs_passed + (modules - failures),
            "failed": (r7rs_run - r7rs_passed) + failures,
            "r7rs": {"suite": R7RS_SUITE, "cases_run": r7rs_run,
                     "cases_passed": r7rs_passed, "exit_code": r7rs["rc"]},
            "srfi": {"suite": SRFI_SUITE, "modules": modules,
                     "module_failures": failures, "case_summaries": cases,
                     "exit_code": srfi["rc"]},
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        with open(os.path.join(evidence, "upstream_test_result.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)

    def _run_suite(self, exe, suite, log):
        # skint 按 cwd 解析 `.:lib:<LIBDIR>` 的外置库树，所以必须在上游源码目录内执行。
        # self.run() 不回传退出码，因此把真实 rc 以标记行追加进日志再解析
        # （test/srfi/all.scm 的退出码就是失败数，必须拿到）。
        self.run(
            'cd "{src}" && "{exe}" {suite} > "{log}" 2>&1; '
            'echo "SKINT_SUITE_EXIT=$?" >> "{log}"'
            .format(src=self.source_folder, exe=exe, suite=suite, log=log),
            ignore_errors=True)
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        m = re.search(r"SKINT_SUITE_EXIT=(\d+)", text)
        return {"log": log, "text": text, "rc": int(m.group(1)) if m else -1}

    # ── 打包 ──────────────────────────────────────────────────────────
    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "skint", src=self.source_folder, dst=bindir, keep_path=False)
        exe = os.path.join(bindir, "skint")
        if not os.path.isfile(exe):
            raise ConanException("package(): 缺少构建产物 %s" % exe)
        os.chmod(exe, 0o755)

        # SRFI 外置库树（上游可选 libinstall 的内容）：share/skint/lib/**。
        copy(self, "*", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "share", "skint", "lib"))

        # man page：上游由 make 用 sed + date 生成；这里改用 Python 做同样的
        # @VERSION@/@DATE@/@LIBDIR@ 替换，避免依赖 worker 上 date/sed 的行为。
        save(self, os.path.join(self.package_folder, "share", "man", "man1",
                                "skint.1"), self._man_page())

    def _man_page(self):
        with open(os.path.join(self.source_folder, "doc", "skint.1.in"),
                  encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        text = text.replace("@VERSION@", self.version)
        text = text.replace("@DATE@", datetime.date.today().isoformat())
        text = text.replace("@LIBDIR@", "share/skint/lib")
        return text

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # application 包：CLI 要在 VirtualRunEnv 里通过 PATH 找到。
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        # 外置 SRFI 库树：skint 只认 SKINT_LIBDIRS，设了它就不再走编译期默认值。
        self.runenv_info.prepend_path(
            "SKINT_LIBDIRS",
            os.path.join(self.package_folder, "share", "skint", "lib"))


def _parse_summary(text):
    """最后一条 `N out of M passed` 汇总行 → (passed, run)；没有汇总行返回 None。"""
    m = SUMMARY_RE.findall(text)
    if not m:
        return None
    return int(m[-1][0]), int(m[-1][1])


def _search_int(text, pattern):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else -1
