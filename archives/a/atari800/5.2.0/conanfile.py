#!/usr/bin/env python3
"""Conan recipe — atari800 5.2.0 (Autotools, libatari800 library target).

Atari 8-bit computer and 5200 console emulator. This recipe builds the
--target=libatari800 library form (libatari800.a + libatari800/libatari800.h),
which exposes a stable public C API for embedding the emulator. The library
target needs no SDL/X11/readline dependencies, only libm, so it maps cleanly
to OHOS. Upstream ships a test program (libatari800_test) that drives 200
emulation frames through the public API; it is compiled inside test_package
(every conan create run) since the main recipe's build() may be skipped by
the build cache.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Atari800Conan(ConanFile):
    name = "atari800"
    version = "5.2.0"
    description = "Atari 8-bit computer and 5200 console emulator (libatari800 library)"
    license = "GPL-2.0"
    homepage = "https://atari800.github.io/"
    url = "https://github.com/atari800/atari800"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # Conan 2 requires a `shared` option when package_type == "library".
    # The libatari800 autotools target only produces a static archive
    # (libatari800.a), so shared builds are rejected in validate().
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # The autotools --target=libatari800 only builds a static archive.
        if self.options.shared:
            raise ConanInvalidConfiguration("atari800 libatari800 target only supports static builds")

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libatari800 target: static library + public C API, no video/sound
        # libraries needed (sound becomes the thin libatari800 API internally).
        tc.configure_args.append("--target=libatari800")
        # HarmonyOS: 2018 版 config.guess 不识别该平台，且 HMDFS 下其临时目录
        # (umask 077 + setgid) 属主不可写导致 "unable to guess system type"；
        # 强制 build triplet 后 configure 跳过 config.guess（同 adms/bash 配方）。
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: conan 创建构建树后父目录对 getcwd() 不可达，configure 内 `pwd`
        # 失败报 "working directory cannot be determined"（真机日志逐字命中）。
        # 预置 PWD 让 shell 的 pwd 内建走逻辑路径（同 adms/analog 配方先例），
        # 补丁 0003 兜底回退 $PWD。
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        # Manual packaging: `make install` would also install the tools/ cart
        # helper binary and DOC files. A pure library package ships only the
        # static archive, the public header and the license.
        # libatari800.a is a build artifact (lives in the build tree); the
        # public header libatari800.h is a *source* file — the autotools
        # out-of-source build (build-release subdir) never copies it into the
        # build tree, so it must be taken from the source tree.
        lib_src = os.path.join(self.build_folder, "src")
        if not os.path.isfile(os.path.join(lib_src, "libatari800.a")):
            lib_src = os.path.join(self.source_folder, "src")
        copy(self, "libatari800.a", lib_src,
             os.path.join(self.package_folder, "lib"))
        header_src = os.path.join(self.source_folder, "src", "libatari800")
        if not os.path.isfile(os.path.join(header_src, "libatari800.h")):
            header_src = os.path.join(self.build_folder, "src", "libatari800")
        copy(self, "libatari800.h", header_src,
             os.path.join(self.package_folder, "include", "libatari800"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Fail loudly instead of shipping an incomplete package: conan copy()
        # silently matches nothing, and a missing include/ makes CMake reject
        # the imported target ("includes non-existent path").
        for rel in ("lib/libatari800.a", "include/libatari800/libatari800.h",
                    "licenses/COPYING"):
            if not os.path.isfile(os.path.join(self.package_folder, rel)):
                raise RuntimeError(f"package artifact missing: {rel}")

    def package_info(self):
        self.cpp_info.libs = ["atari800"]
        # configure adds -lm for the libatari800 target (AC_CHECK_LIB(m,cos)).
        self.cpp_info.system_libs = ["m"]
        # 头文件装在 include/libatari800/ 下（对应上游 include_HEADERS 布局），
        # 但上游测试程序 libatari800_test.c 按上游惯例写 `#include "libatari800.h"`
        # （上游 Makefile 以 -Ilibatari800 编译该测试），仅 -I<prefix>/include
        # 解析不到。同时暴露 include/libatari800，使两种包含风格
        # （<libatari800/libatari800.h> 与 "libatari800.h"）都能被消费者解析。
        self.cpp_info.includedirs = ["include", "include/libatari800"]
        self.cpp_info.shared = self.options.shared
