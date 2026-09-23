#!/usr/bin/env python3
"""Conan test_package for libdom 0.4.2.

CMakeDeps 在 2.29.1 上对 `cpp_info.requires` 传递的依赖会丢 includedirs
（transitive 依赖生成的 config 中 INCLUDE_DIRS 为空），因此这里把全部
链接依赖声明为 direct requirement 并显式 find_package，确保 test.c /
DOMTS 测试能拿到 libwapcaplet/libparserutils/libhubbub/libxml2 的头文件。

除消费者 API 冒烟 (test_libdom) 外，本 test_package 还集成上游 W3C DOMTS
可运行子集：test/transform.pl 在打包侧（本机 perl + XML::Parser::PerlSAX/
XML::XPath）将 level1/core 的 .xml 用例离线转换为 .c 片段（vendored 于
upstream/test/domts/，未修改），与上游 test/testutils/*.{c,h} 一起编译，
每个片段一个可执行文件，在 CI（OHOS aarch64）上逐个实跑。运行期 CWD 置于
upstream/，使片段内 chdir("test/testcases/tests/level1/core/files") 能定位
到 vendored fixtures（staff.xml 等）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibdomTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libparserutils/0.2.5")
        self.requires("libwapcaplet/0.4.3.1")
        self.requires("libhubbub/0.3.8")
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _domts_fragment_names(self):
        """Discover vendored DOMTS .c fragments -> executable suffix names."""
        domts_dir = os.path.join(self.source_folder, "upstream", "test", "domts")
        names = []
        if os.path.isdir(domts_dir):
            for c in sorted(glob.glob(os.path.join(domts_dir, "*.c"))):
                names.append(os.path.splitext(os.path.basename(c))[0])
        return names

    def test(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Resolve the CMake runtime output dir to an ABSOLUTE path. Under
        # cmake_layout the bindir may be relative (e.g. "."); self.run() with a
        # cwd= argument resolves relative executable paths against that cwd,
        # which would make "./domts_*" point into upstream/ and fail with
        # "inaccessible or not found" (Error 127). Anchor to self.build_folder.
        bindir = self.cpp.build.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.normpath(os.path.join(self.build_folder, bindir))

        # 1) Consumer API smoke test (core DOM + XML binding + hubbub binding)
        self.run(os.path.join(bindir, "test_libdom"), env="conanrun")

        # 2) Real upstream W3C DOMTS subset (level1/core): run each vendored
        #    fragment from upstream/ so its chdir(.../files) resolves to the
        #    vendored fixtures.
        frags = self._domts_fragment_names()
        if frags:
            run_cwd = os.path.join(self.source_folder, "upstream")
            for name in frags:
                exe = os.path.join(bindir, "domts_" + name)
                self.run(exe, cwd=run_cwd, env="conanrun")
