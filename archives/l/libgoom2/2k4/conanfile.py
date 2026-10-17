#!/usr/bin/env python3
"""Conan recipe for libgoom2 2k4 (the goom audio visualisation library) on HarmonyOS.

The 2004 goom2k4 tree ships three consumers of the shared library: the library
itself (src/libgoom2), an XMMS visualisation plugin (xmms-goom) and an SDL/GTK
stand-alone application (sdl-goom). Only the library is packaged here; both
front-ends need XMMS/SDL/GTK development packages and stay disabled by the
upstream configure when those are absent.
"""

import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class Libgoom2Conan(ConanFile):
    name = "libgoom2"
    version = "2k4"
    description = "Goom audio visualisation effects library (2k4 release)"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/goom/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        # OHOS 编译器（clang/clang++）位于 /data/service/hnp/bin/，不在默认
        # PATH 中；OHOS 适配版 conan 的 AutotoolsToolchain 不把
        # compiler_executables 映射为 CC/CXX，configure 探测
        # aarch64-unknown-linux-ohos-gcc/gcc/cc 全部落空，报
        # "no acceptable C compiler found in $PATH"（参照 adplay/1.9、
        # jack/1.9.22、tslib/1.22 先例，显式注入 CC/CXX/AR/RANLIB）。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "")
        ranlib = compilers.get("ranlib") or (
            os.path.join(bindir, "llvm-ranlib") if bindir else ""
        )
        if ar:
            env.define("AR", ar)
        if ranlib:
            env.define("RANLIB", ranlib)
        return env

    def build(self):
        apply_conandata_patches(self)
        # patches/0001+0002 teach the bundled 2004 config.guess/config.sub the
        # aarch64-unknown-linux-ohos triplet, so configure identifies the
        # native platform itself; no --build/--host forgery is needed (E007).
        # Configure runs with a plain /bin/sh: HMDFS intermittently breaks
        # getcwd in the hnp bash that the profile exports as CONFIG_SHELL.
        jobs = self.conf.get("tools.build:jobs", default=2)
        with self._compiler_env().vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
                f'./configure --prefix="{self.package_folder}"',
                env="conanbuild",
            )
            self.run(f'cd "{self.source_folder}" && make -j{jobs}', env="conanbuild")
            # Upstream ships no automated test suite (inventory in
            # test_package/MANIFEST.yml): automake's check target is a
            # structural no-op, kept in the log as the upstream test entrypoint.
            self.run(f'cd "{self.source_folder}" && make -j1 check', env="conanbuild")
            self.run(f'cd "{self.source_folder}" && make install', env="conanbuild")

    def package(self):
        rm(self, "*.la", self.package_folder, recursive=True)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["goom2"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libgoom2")
