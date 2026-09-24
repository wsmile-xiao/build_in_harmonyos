#!/usr/bin/env python3
"""Conan recipe for kelbt — Backtracking LR parser generator.

kelbt reads `.kl` / `.kh` grammar files and generates C++ backtracking
parsers. It is the parser-generator sibling of ragel/colm by Adrian
Thurston, and ships its own AAPL container library in-tree.

Build system: autotools
Dependencies: 无外部依赖（仅 C++ 编译器 + 内置 aapl 头文件）
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class KelbtConan(ConanFile):
    name = "kelbt"
    version = "0.16"
    description = "Backtracking LR parser generator — generates C++ parsers from .kl/.kh grammar files"
    license = "GPL-2.0-or-later"
    homepage = "http://www.colm.net/open-source/kelbt/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # R26: 终端工具静态链接，避免在真机运行时依赖系统动态库。
            tc.extra_ldflags.append("-static")
            # ARM64 上 char 默认为 unsigned，kelbt 生成的 klparse.cpp 中
            # `char Parser_indicies[] = {-1, ...}` 在 C++11+ 触发 narrowing
            # 错误（-1 无法窄化为 unsigned char）。kelbt 假设 char 为 signed，
            # 显式指定 -fsigned-char 保持 -1 的语义。
            tc.extra_cxxflags.append("-fsigned-char")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # 上游发布包自带生成的 klscan.cpp / klparse.{h,cpp}（DIST 中
        # build_parsers=no），因此 configure 不需要 ragel/kelbt bootstrap。
        #
        # OHOS/HMDFS 平台适配（真机 shadow CI 实测）：
        # 1) /tmp 只读（知识库 E002）→ TMPDIR 指向可写目录。
        # 2) configure 直接 exec 报 Permission denied（E046/E047）：文件 owner
        #    uid 与构建进程 uid 不一致，且 HMDFS 屏蔽 other 执行位，chmod 无效。
        #    → 改用 `sh configure` 显式执行（sh 读脚本无需执行位）。
        os.environ["TMPDIR"] = "/data/storage/el2/base/cache"

        # Autotools 的 configure/Makefile 位于 base_build（self.build_folder
        # 是其下的 build-release 子目录，只放 generators），需以 base_build
        # 为工作目录执行。
        base_build = self.folders.base_build
        configure_path = os.path.join(base_build, "configure")
        self.run(f'sh "{configure_path}" --prefix=/', cwd=base_build, env="conanbuild")
        self.run("make -j1", cwd=base_build, env="conanbuild")

    def package(self):
        # kelbt 只安装一个可执行文件（aapl 为 noinst_HEADERS，不安装）。
        # 编译产物在 base_build/src（与 configure/Makefile 同级），而非
        # self.build_folder（其下的 build-release 子目录）。
        base_build = self.folders.base_build
        copy(self, "kelbt", os.path.join(base_build, "src"),
             os.path.join(self.package_folder, "bin"), keep_path=False)
        # 许可证：kelbt 主体 GPL-2.0-or-later，aapl 库为 LGPL-2.1。
        # 两个 COPYING 文件名相同，分放子目录避免互相覆盖。
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING", os.path.join(self.source_folder, "aapl"),
             os.path.join(self.package_folder, "licenses", "aapl"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
