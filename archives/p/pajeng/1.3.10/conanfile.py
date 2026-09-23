#!/usr/bin/env python3
"""Conan recipe for PajeNG (pajeng) 1.3.10 — CMake project.

PajeNG 是 Paje 追踪文件格式的可视化/分析库（libpaje + pj_dump/pj_equals 工
具）。上游用 CMake 构建：FLEX/BISON 是必需的构建期工具（scanner.l/parser.y），
fmt 是必需的第三方库（PAJE_USE_FMT=OFF 会退化到 boost::karma，精度行为不同，
上游默认 ON），pj_equals 使用 OpenMP（-fopenmp，OHOS SDK llvm 自带 libomp）。

R51 上游测试：上游通过 CTest 注册 12 个 tesh 套件（src/tools/CMakeLists.txt
的 ADD_TESH/ADD_TEST，tests/*.tesh 共 50 条 tesh 命令，用 perl 版 tesh 驱动
脚本逐条执行并比对期望输出）。build() 内真实执行 ctest（tesh 的 --cd 指向
CMAKE_BINARY_DIR，命令按 ../traces 相对路径取数据 → 需把上游 traces 拷到
构建目录的上一级），解析 ctest 汇总计数，失败抛错。

运行时库路径：musl 忽略 DT_RUNPATH，测试执行 ./pj_dump 时需显式
LD_LIBRARY_PATH 指向构建目录（libpaje.so）+ 依赖库目录 + SDK libomp 目录。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PajengConan(ConanFile):
    name = "pajeng"
    version = "1.3.10"
    description = "Visualization and analysis tools for the Paje trace file format"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/schnorr/pajeng"
    url = "https://github.com/schnorr/pajeng"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # 上游安装路径只覆盖共享库（STATIC_LINKING=ON 时不 INSTALL 任何库），
    # 因此默认 shared=True 与上游可安装形态一致
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # FIND_PACKAGE(FMT 5.0.0 REQUIRED)：CONFIG 模式吃 conan CMakeDeps
        self.requires("fmt/11.1.3")
        # PajeTraceEvent.cc/PajeEntity.cc 无条件包含 boost/spirit/qi.hpp
        self.requires("boost/1.85.0")
        # pj_dump.cc/pj_equals.cc 无条件包含 argp.h（musl 无 argp）
        self.requires("argp-standalone/1.4.1")

    def build_requirements(self):
        # FIND_PACKAGE(FLEX/BISON REQUIRED)：构建期工具
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # FLEX_LIBRARIES 预置为 flex 工具包的 libfl.a 绝对路径：
        # scanner.l 无 %option noyywrap，链接需要 libfl；CMake 的 find_library
        # 搜不到 tool_requires 的 libdir，显式传缓存变量绕开
        flex = self.dependencies.build["flex"]
        for libdir in flex.cpp_info.libdirs:
            cand = os.path.join(libdir, "libfl.a")
            if os.path.isfile(cand):
                tc.variables["FL_LIBRARY"] = cand
                break
        # conan bison 包的数据目录不在默认前缀，运行期需显式指向
        self._bison_pkgdata = None
        bison = self.dependencies.build["bison"]
        if bison.package_folder:
            cand = os.path.join(bison.package_folder, "share", "bison")
            if os.path.isdir(cand):
                self._bison_pkgdata = cand
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            "PAJE_LIBRARY": "ON",
            "PAJE_TOOLS": "ON",
            # PAJE_DOC 需要 asciidoc/latex 文档工具链，非库/工具产物
            "PAJE_DOC": "OFF",
            "PAJE_USE_FMT": "ON",
            # 上游 STATIC_LINKING 决定构建静态还是共享 libpaje 及安装路径
            "STATIC_LINKING": "ON" if not self.options.shared else "OFF",
        })
        # bison 按编译期前缀找数据目录，conan 包需显式指到包内 share/bison
        # （否则报 /share/bison/m4sugar/m4sugar.m4 cannot open）
        if getattr(self, "_bison_pkgdata", None):
            os.environ["BISON_PKGDATADIR"] = self._bison_pkgdata
        cmake.build()
        # OHOS 交叉平台 CMake 不产出带版本号的库文件名（只有 libpaje.so），
        # 而 SONAME 是 libpaje.so.2——工具按 SONAME 找文件会失败，补链接
        _libdir = os.path.join(self.build_folder, "src", "libpaje")
        _real = os.path.join(_libdir, "libpaje.so")
        _want = os.path.join(_libdir, "libpaje.so.2")
        if os.path.isfile(_real) and not os.path.exists(_want):
            os.symlink("libpaje.so", _want)
        self._run_upstream_tests()

    def _sdk_omp_libdirs(self):
        # pj_equals 链接 -fopenmp，运行期需要 SDK llvm 的 libomp.so 目录
        pats = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/usr/local/ohos-sdk/*/ohos/native/llvm/lib/aarch64-linux-ohos",
        ]
        dirs = []
        for pat in pats:
            dirs.extend(glob.glob(pat))
        return [d for d in dirs if os.path.isdir(d)]

    def _run_upstream_tests(self):
        """R51：build() 内真实执行上游 CTest 套件（12 个 tesh 文件，50 条
        tesh 命令）。ctest 汇总计数取自日志，非硬编码；失败抛错。"""
        bdir = self.build_folder
        # tesh 的 ADD_TEST 用 --cd CMAKE_BINARY_DIR，命令内按 ./pj_dump 与
        # ../traces 相对路径访问 → 工具在 cwd、traces 在 cwd 的上一级
        _src_traces = os.path.join(self.source_folder, "traces")
        _dst_traces = os.path.join(os.path.dirname(bdir), "traces")
        os.makedirs(_dst_traces, exist_ok=True)
        _n = 0
        for _f in glob.glob(os.path.join(_src_traces, "*")):
            if os.path.isfile(_f):
                shutil.copy2(_f, _dst_traces)
                _n += 1
        self.output.info("traces copied: %d files -> %s" % (_n, _dst_traces))
        # musl 忽略 DT_RUNPATH：显式拼 LD_LIBRARY_PATH（构建目录的 libpaje.so
        # + 依赖 libfmt.so + SDK libomp.so）。Conan self.run(env=) 注入不可靠
        # （astroterm/acf-db 已实证），改进程级 os.environ。
        libdirs = [bdir, os.path.join(bdir, "src", "libpaje")]
        for _, dep in self.dependencies.items():
            libdirs.extend(dep.cpp_info.libdirs)
        libdirs.extend(self._sdk_omp_libdirs())
        prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            libdirs + ([prev] if prev else []))
        perl_home = "/data/service/hnp/bin"
        if os.path.isdir(perl_home):
            pp = os.environ.get("PATH", "")
            os.environ["PATH"] = perl_home + ":" + pp

        log_path = os.path.join(bdir, "ctest.log")
        # conanbuild env 会覆盖进程级 LD_LIBRARY_PATH，改用 shell 前缀式
        # 注入，保证传到 ctest -> perl tesh -> pj_dump 全链
        ldstr = ":".join(libdirs)
        test_cmd = (
            f'LD_LIBRARY_PATH="{ldstr}:$LD_LIBRARY_PATH" '
            f'ctest -V --output-on-failure > "{log_path}" 2>&1'
        )
        self.run(test_cmd, ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("=== upstream ctest (tail) ===")
        for line in (out.splitlines() or [])[-25:]:
            self.output.info(line)

        suites = len(set(re.findall(r"Test #\d+: (\S+)", out)))
        m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)",
                      out)
        total = int(m.group(3)) if m else 0
        failed = int(m.group(2)) if m else 0
        passed = total - failed
        gate_ok = total > 0 and failed == 0
        ut_status = "passed" if gate_ok else "failed"
        ut_result = {
            "status": ut_status,
            "framework": "ctest+tesh",
            "command": test_cmd,
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "suites": suites,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + repr(ut_result)
        )
        if ut_status != "passed":
            raise RuntimeError(
                "upstream ctest failed: total=%d failed=%d" % (total, failed)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # 包内同样补 SONAME 兼容链接（消费者运行期按 libpaje.so.2 查找）
        _plib = os.path.join(self.package_folder, "lib")
        _preal = os.path.join(_plib, "libpaje.so")
        _pwant = os.path.join(_plib, "libpaje.so.2")
        if os.path.isfile(_preal) and not os.path.exists(_pwant):
            os.symlink("libpaje.so", _pwant)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["paje"]
        self.cpp_info.set_property("pkg_config_name", "libpaje")
        # R38: 同时产出 pj_dump/pj_equals CLI 工具（软件级 commands.json 已声明）
        self.cpp_info.bindirs = ["bin"]
