#!/usr/bin/env python3
"""Conan recipe — cllayerinfo 2.3.3 (Autotools).

cllayerinfo 是 OpenCL ICD Loader 项目（OCL-dev/ocl-icd）与 loader 同源码树构建的
命令行诊断工具：初始化 ICD loader 的 layer 链后用 clGetLayerInfo 逐个打印层的
CL_LAYER_API_VERSION 与 CL_LAYER_NAME（上游 Makefile.am: bin_PROGRAMS = cllayerinfo）。

交付范围（与 archives/o/ocl-icd/2.3.5.x 互补，不重复交付同名产物）：
  * 本包只交付 bin/cllayerinfo。loader 源码被直接编进该二进制
    （Makefile.am: cllayerinfo_SOURCES = cllayerinfo.c $(libOpenCL_la_SOURCES)），
    因此运行时不需要 libOpenCL.so；
  * libOpenCL.so / OpenCL 头文件与 .pc 由 archives/o/ocl-icd 交付，本包安装后清理；
  * 上游自测用的 dummy ICD / dummy layer 是 pkglib_LTLIBRARIES，上游 install-exec-hook
    自行删除（Makefile.am:110-111），不会进包。

构建要点（W0b 历史核验：与 archives/o/ocl-icd/2.3.5.1 的历史结论逐条对齐）：
  * GitHub tag 归档不含 configure（只有 configure.ac/Makefile.am），需 autoreconf 自举；
  * 自带 config.guess 不认 HarmonyOS，须显式 --build/--host=aarch64-unknown-linux-ohos（E007）；
  * HMDFS 默认 umask 077，会让 autoreconf/configure 产物与安装文件带 0600-0700 权限，
    包内文件对其他用户不可读（E011 同类现象）→ 构建/打包期显式收敛到 022；
  * 生成 dispatch 表需要 ruby（icd_generator.rb），worker 与真机由系统提供。

上游测试（R51）：`make check` 驱动 tests/testsuite（autotest）在本配方 build() 内真实执行，
实测计数以 testsuite.log 为准并打印 HMBS_UPSTREAM_TEST_RESULT 标记（framework=autotest）。
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.files import replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ClLayerInfoConan(ConanFile):
    name = "cllayerinfo"
    version = "2.3.3"
    description = ("OpenCL layer inspection utility (cllayerinfo) shipped by the "
                   "ocl-icd ICD Loader")
    license = "BSD-2-Clause"
    homepage = "https://github.com/OCL-dev/ocl-icd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("opencl", "icd", "loader", "layer", "command-line-tool")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零运行时依赖：cllayerinfo 内联了 loader 源码，只链接 libc/pthread。
        # 构建期依赖见 build_requirements()。
        pass

    def build_requirements(self):
        # 上游 tag 归档不含 configure，需要在 worker 上自举 autotools；
        # 真机/worker 无系统 automake、libtool，走 conan 工具包补齐。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4.1")

    def validate(self):
        # R32：平台判断必须用 in (...)，不能 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} 仅适配 Linux/OHOS，当前 {self.settings.os} 未适配")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007：上游自带 config.guess 无法识别 HarmonyOS（uname -s 报 HarmonyOS 时
        # 猜出的三元组不匹配），显式钉住原生三元组，避免 config.sub 归一化失败。
        triple = "aarch64-unknown-linux-ohos"
        tc.configure_args.extend([f"--build={triple}", f"--host={triple}"])
        tc.generate()

    def build(self):
        # E011：HMDFS 默认 umask 077，会让 autoreconf/configure 生成物与安装文件
        # 带 0600/0700 权限，包内文件消费者读不到。显式收敛到 022（子进程继承）。
        os.umask(0o022)

        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.autoreconf()
        self._apply_e011_umask_fix()
        autotools.configure()
        autotools.make(args=["-j2"])

        # R51：build() 末尾必须真正跑上游测试（上游是 autotest 套件，入口 make check）
        autotools.make(target="check")
        self._report_upstream_tests()

    def package(self):
        os.umask(0o022)
        autotools = Autotools(self)
        autotools.install()

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        # 只交付工具本体：libOpenCL.so / OpenCL 头文件 / .pc 由 archives/o/ocl-icd 交付，
        # 同一 SONAME 不应由两个包各自持有（消费者链接时会冲突）。
        for extra in ("include", "lib", "lib64", "libexec", "share"):
            target = os.path.join(self.package_folder, extra)
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)

        tool = os.path.join(self.package_folder, "bin", "cllayerinfo")
        if not os.path.isfile(tool):
            raise ConanException(
                "bin/cllayerinfo 未生成：上游 bin_PROGRAMS 安装目标缺失，配方失效")
        os.chmod(tool, 0o755)  # 兜底，避免 umask 残留导致二进制不可执行

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    # ── 上游测试取证 ────────────────────────────────────────────────
    def _apply_e011_umask_fix(self):
        """E011：HMDFS 的 UID 映射让 mode 0700 的临时目录对当前进程不可写。

        autoconf 生成的 configure/config.status 模板用 `(umask 077 && mktemp -d)`
        创建 config.status 的临时目录；在 HMDFS 上该目录得到 drwx--S---(02700) 且
        属主被映射成其它 UID，随后写 subs1.awk 报 "Permission denied"，
        configure 直接失败在 `config.status: error: could not setup config files machinery`。
        按知识库 E011 的处置，把内嵌模板的 umask 077 收敛为 022。
        （configure 是 autoreconf 在构建期生成的产物，不属于上游源码文件，
        因此这里不做成补丁，而是构建期源码修复。）
        """
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanException("configure 未生成：autoreconf 自举失败（R51 前置条件）")

        with open(configure, encoding="utf-8", errors="surrogateescape") as fh:
            replaced = fh.read().count("umask 077")

        if replaced:
            replace_in_file(self, configure, "umask 077", "umask 022")
        else:
            self.output.warning("E011: configure 中未发现 umask 077（上游 autoconf 模板可能变更）")

        os.chmod(configure, 0o755)
        self.output.info(f"E011: configure 内嵌 umask 077 -> 022（{replaced} 处）")

    def _report_upstream_tests(self):
        """解析 make check 产出的 testsuite.log，打印 HMBS_UPSTREAM_TEST_RESULT 标记。

        上游 tests/Makefile.am 的 check-local 直接执行 tests/testsuite（原生 autotest），
        其计数只出现在汇总横幅里（"All N tests were successful." /
        "K of N tests failed." / "K of N tests were skipped."）；若某发行方式改走
        automake 并行测试驱动，则退化为 "# TOTAL:/# PASS:..." 汇总行。两种都解析，
        并把日志末尾（含横幅）打进构建输出，便于 PR 正文原样引用。
        """
        log_path = self._find_testsuite_log()
        if not log_path:
            self.output.error("make check 未产出 testsuite.log（R51：上游测试必须真实执行）")
            raise ConanException("testsuite.log 缺失：上游测试未真正运行")

        with open(log_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        total, passed, failed, skipped = self._parse_test_counts(text)

        if failed:
            status = "failed"
        elif total == 0:
            status = "no_tests"
        else:
            status = "passed"

        rel_log = os.path.relpath(log_path, self.source_folder)
        self.output.info(f"上游 testsuite 汇总（{rel_log}）:\n"
                         + "\n".join(text.splitlines()[-30:]))

        marker = {
            "status": status,
            "framework": "autotest",
            "command": "make check",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "log": rel_log,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))

        if status != "passed":
            raise ConanException(
                f"上游测试未全部通过：TOTAL={total} PASS={passed} FAIL={failed} "
                f"SKIP={skipped}（{rel_log}）")

    @staticmethod
    def _parse_test_counts(text):
        """返回 (total, passed, failed, skipped)，两种汇总格式都支持。"""
        # 格式一：automake 并行测试驱动
        def _tagged(key):
            m = re.search(rf"^#\s*{key}:\s*(\d+)\s*$", text, re.M)
            return int(m.group(1)) if m else 0

        total = _tagged("TOTAL")
        passed = _tagged("PASS")
        failed = _tagged("FAIL") + _tagged("ERROR")
        skipped = _tagged("SKIP")

        # 格式二：原生 autotest 汇总横幅（上游当前走这条）
        m = re.search(r"^All (\d+) tests? (?:were successful|behaved as expected)\.",
                      text, re.M)
        if m:
            return int(m.group(1)), int(m.group(1)), 0, 0

        m_total = re.search(r"^(\d+) of (\d+) tests? (?:failed|behaved as expected|"
                            r"were skipped)\.", text, re.M)
        if m_total:
            total = int(m_total.group(2))
        m_failed = re.search(r"^(\d+) of \d+ tests? failed\.", text, re.M)
        if m_failed:
            failed = int(m_failed.group(1))
        m_skipped = re.search(r"^(\d+) of \d+ tests? were skipped\.", text, re.M)
        if m_skipped:
            skipped = int(m_skipped.group(1))

        # 兜底：从用例状态表逐行统计（部分日志只保留该表）
        if total == 0:
            rows = re.findall(r"^\s*\d+:\s+\S.*?\s{2,}(\S.*?)\s*$", text, re.M)
            if rows:
                total = len(rows)
                failed = sum(1 for r in rows if "FAILED" in r or r.startswith("failed"))
                skipped = sum(1 for r in rows if "skipped" in r)

        if passed == 0 and total:
            passed = max(total - failed - skipped, 0)
        return total, passed, failed, skipped

    def _find_testsuite_log(self):
        """testsuite.log 由 tests/ 下的 check-local 在当前目录生成，优先精确路径。"""
        candidates = [
            os.path.join(self.build_folder, "tests", "testsuite.log"),
            os.path.join(self.source_folder, "tests", "testsuite.log"),
            os.path.join(self.build_folder, "testsuite.log"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        for root, _dirs, files in os.walk(self.build_folder):
            if "testsuite.log" in files:
                return os.path.join(root, "testsuite.log")
        return None
