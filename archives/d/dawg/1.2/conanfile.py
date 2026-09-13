#!/usr/bin/env python3
"""Conan recipe for Dawg 1.2 — DNA Assembly With Gaps (sequence evolution simulator).

Dawg 是 Reed A. Cartwright 的 DNA 序列演化模拟器（GPL-2+，C++98 风格代码 + CMake）。
它接受 Newick 系统发育树，按 GTR/JC/K2P 等替换模型与 NB/PL/US 三种 indel 模型模拟
序列演化，输出 FASTA/Nexus/Phylip/Clustal 比对结果，是校对比对与建树算法时
获取"已知真实比对"的工具。上游源码 http://scit.us/projects/dawg，
当前官方仓库 https://github.com/reedacartwright/dawg（tag v1.2，2009-04-26）。

OHOS 适配要点：
* 上游 1.2 的 CMake 下限是 2.6（CMakeLists.txt 首行），CMake 4.x 已移除 <3.5 的
  兼容策略，直接报 "Compatibility with CMake < 3.5 has been removed"；配方在
  cmake.configure() 传 CMAKE_POLICY_VERSION_MINIMUM=3.5（与 Debian 打包同口径）。
* 词法/语法分析器由 flex/bison 现场生成（src/CMakeLists.txt 缺任一即 SEND_ERROR），
  必须以 tool_requires 提供，不能依赖设备或 CI worker 的系统 PATH。
* CMake 不识别 OHOS 平台名，按仓库惯例显式声明 CMAKE_SYSTEM_NAME=Linux。
* 需要两个补丁（缺任一项都无法得到可用制品）：
  0002 把 2009 年代码移植到 C++17——std::auto_ptr 与 std::unary_function 均在 C++17
  被移除，而本 profile 强制 compiler.cppstd=17，不应用则编译失败；
  0001 刷新上游过期的测试基准 tests/test0.fasta（理由见下段）。

上游测试基准说明（必须如实申报，PR 正文同步）：v1.2 tarball 里的 tests/test0.sh 是
autotools 时代遗留入口（引用 top_srcdir、tests/CMakeLists.txt 为 0 字节，CMake 化时
未一并迁移），其基准 tests/test0.fasta 仍是 v1.0.0 的 RNG 语义下生成的：v1.1 起
rand_real()/rand_bool() 由 ILP32 位拼接改为 (double)u/2^32 且比较由 <= 改为 <，
模拟输出随之改变，基准却从未重生成。上游缺陷追踪编号为 #56，依据是 Debian 官方源码包
debian/rules 的注释与 Debian 邮件列表归档（原始字节随本 PR 入库于
archives/d/dawg/1.2/reports/evidence/，可离线复核）。取证边界：本设备访问
https://github.com/reedacartwright/dawg/issues/56 返回 HTTP 404（响应体 9 字节
"Not Found"，已原样留档），因此本任务未直接读到该 issue 页面，编号采信依据是上述
两条离线来源，而非该链接。Debian 自 1.2-2 起在 debian/rules 里以 `|| true` 忽略该测试。
本配方补丁 0001 用 v1.2 源码在 OHOS 上的真实确定性输出刷新基准；该输出与 Debian 在
amd64/glibc/GCC 上用未修改源码得到的输出逐行一致（见版本级 notes.md），
证明这不是 OHOS 侧行为差异。
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class DawgConan(ConanFile):
    name = "dawg"
    version = "1.2"
    description = "DNA Assembly With Gaps: a DNA sequence evolution simulator with indel formation"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/reedacartwright/dawg"
    url = "https://github.com/reedacartwright/dawg"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # src/CMakeLists.txt 缺 bison 或 flex 直接 SEND_ERROR（第 10-12 行），
        # 二者是构建期工具：CI worker 无系统级 flex/bison，按仓库惯例 tool_requires。
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4")
        # bison 生成 parser 时要展开自己的 m4 宏库，m4 需作为工具依赖提供
        # （见 build() 的 BISON_PKGDATADIR / M4 处置，与 archives/b/ball 同型）。
        self.tool_requires("m4/1.4.19")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dawg {self.version} is prepared for Linux and OHOS only, "
                f"got os={self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # tool_requires(bison/flex) 的 bin 目录经 VirtualBuildEnv 注入 PATH，
        # 上游用 FIND_PROGRAM(bison/flex) 按 PATH 查找。
        VirtualBuildEnv(self).generate()

        toolchain = CMakeToolchain(self)
        # CMake 没有 OHOS 平台模块，OHOS 即 Linux 内核，按仓库惯例显式声明。
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64"
                if str(self.settings.arch) in ("armv8", "armv8.3", "aarch64")
                else str(self.settings.arch)
            )
        # R26：终端工具不做动态库交付。
        toolchain.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        with self._bison_runtime_env().vars(self).apply():
            # 上游 CMakeLists.txt 首行 CMAKE_MINIMUM_REQUIRED(VERSION 2.6 FATAL_ERROR)，
            # CMake 4.x 已删除 <3.5 兼容策略。该策略检查发生在 CMakeLists 顶部，早于
            # 依赖 toolchain 文件生效的变量注入，故必须走命令行缓存变量。
            cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
            cmake.build()

            if not self.conf.get("tools.build:skip_test", default=False):
                self._run_upstream_tests()

    def _bison_runtime_env(self):
        """bison 的 pkgdatadir 被编译成 /share/bison（构建时 --prefix= 所致），直接运行会报
        `bison: /share/bison/m4sugar/m4sugar.m4: cannot open`。必须把 BISON_PKGDATADIR
        指向包内真实位置，并把 M4 指向 m4 工具包（与 archives/b/ball 同一处置，
        也是 bison 自身 test_package 的做法）。
        """
        bison_pkg = self.dependencies.build["bison/3.8.2"].package_folder
        m4_pkg = self.dependencies.build["m4/1.4.19"].package_folder
        pkgdata = os.path.join(bison_pkg, "share", "bison")
        if not os.path.isdir(pkgdata):
            raise ConanException(f"bison package has no share/bison dir: {pkgdata}")
        env = Environment()
        env.define_path("BISON_PKGDATADIR", pkgdata)
        env.define_path("M4", os.path.join(m4_pkg, "bin", "m4"))
        self.output.info(f"BISON_PKGDATADIR={pkgdata}")
        return env

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "copying.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    # ── 上游测试（v1.2 未注册 ctest，tests/CMakeLists.txt 为 0 字节，手工驱动）──

    def _run_upstream_tests(self):
        dawg_bin = os.path.join(self.build_folder, "src", "dawg")
        if not os.path.isfile(dawg_bin):
            raise ConanException(f"built binary not found: {dawg_bin}")

        config = os.path.join(self.source_folder, "tests", "test0.dawg")

        # 1) 真实产出回读：ConanFile.run() 的 Python 返回值是 None，必须重定向到文件
        #    再读；同时防空套件假绿（输出为 0 条记录一律判失败）。
        actual = os.path.join(self.build_folder, "test0.actual.fasta")
        self.run(
            f'"{dawg_bin}" "{config}" > "{actual}" 2>&1',
            cwd=self.source_folder,
            env="conanbuild",
        )
        with open(actual, encoding="utf-8", errors="replace") as handle:
            output = handle.read()
        records = [line for line in output.splitlines() if line.startswith(">")]
        if len(records) != 5:
            raise ConanException(
                "upstream test0.dawg did not produce the 5 labelled sequences "
                f"(got {len(records)})"
            )
        # 比对型证据：所有序列等长（真比对，而非空/截断输出）
        lengths = {
            len("".join(block.split("\n")[1:]))
            for block in output.strip().split("\n\n")
            if block.strip()
        }
        if len(lengths) != 1 or 0 in lengths:
            raise ConanException(
                f"generated alignment is not rectangular: lengths={sorted(lengths)}"
            )
        self.output.info(
            "UPSTREAM RUN: test0.dawg records=%d alignment_length=%d raw_bytes=%d"
            % (len(records), lengths.pop(), len(output.encode("utf-8")))
        )

        # 2) 上游自带 tests/test0.sh（golden 比对，含补丁 0001 刷新后的基准）。
        #    DIFF/DAWG/top_srcdir 是上游脚本接口，按 POSIX 行内赋值传入。
        cmd = (
            f'DAWG="{dawg_bin}" DIFF=diff top_srcdir="{self.source_folder}" '
            f"sh tests/test0.sh"
        )
        self.run(cmd, cwd=self.source_folder, env="conanbuild")
        self.output.info(
            "UPSTREAM TEST: tests/test0.sh PASS 1/1 "
            "(golden tests/test0.fasta, refreshed by patches/0001)"
        )
