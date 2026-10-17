#!/usr/bin/env python3
"""Conan recipe — zhcon 0.2.6 (Autotools CLI application).

zhcon is a CJK console environment for Linux. This recipe builds the
upstream 0.2.6 sources (distributed upstream as zhcon-0.2.5.tar.gz plus
the 0.2.5-to-0.2.6 diff; the diff is folded into the patches below).
Hard deps: ncurses (wide-char variant, linked as -lncursesw) and gettext
(-lintl). Optional gpm/ggi/unicon backends are auto-disabled on OHOS.
"""
from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ZhconConan(ConanFile):
    name = "zhcon"
    version = "0.2.6"
    description = "Fast CJK console environment for Linux, ported to HarmonyOS"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/zhcon/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ncurses/6.5")
        self.requires("gettext/0.22.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from ncurses/gettext into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.extra_cflags.append("-funsigned-char")
        tc.extra_cxxflags.append("-funsigned-char")
        # 静态链接 libc++：运行时不依赖 libc++_shared.so（该库仅在 OHOS SDK
        # llvm/lib/aarch64-linux-ohos/ 子目录，CI 运行环境无默认搜索路径）。
        tc.extra_ldflags.append("-static-libstdc++")
        tc.generate()
        # OHOS: /system/bin/sh (mksh) cannot execute ELF conftest binaries;
        # force bash as CONFIG_SHELL so configure's AC_RUN_IFELSE probes run.
        # (same fix as abook/aaphoto; profile buildenv CONFIG_SHELL may not
        # propagate into the conan-build subprocess on CI workers)
        # OHOS loader has no default search path for conan-cached shared libs;
        # configure conftest links the dependency closure (AutotoolsDeps
        # exports LIBS) and must run immediately -> prepend host deps' bin
        # dirs to PATH and lib dirs to LD_LIBRARY_PATH (dirb/aaphoto pattern,
        # DRAFT-conan-dep-shared-libs; "cannot run C compiled programs").
        env = Environment()
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        env.define("SHELL", "/data/service/hnp/bin/bash")
        for dep in self.dependencies.host.values():
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])
        autotools.make(args=["check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # CLI application: no libraries to link, binary is zhcon.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]