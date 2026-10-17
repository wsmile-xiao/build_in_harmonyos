#!/usr/bin/env python3
"""Conan recipe for tsocks 1.8beta5 on Linux and HarmonyOS."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class TsocksConan(ConanFile):
    name = "tsocks"
    version = "1.8beta5"
    description = "Transparent SOCKS proxying through LD_PRELOAD interception"
    license = "GPL-2.0-or-later"
    homepage = "http://tsocks.sf.net"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Tarball entries carry a leading ./ so conan cannot detect the single
        # root folder; strip_root leaves ./tsocks-1.8 in place. Flatten it so
        # configure, patches and make all work against the source root.
        nested = os.path.join(self.source_folder, "tsocks-1.8")
        if os.path.isdir(nested):
            for entry in os.listdir(nested):
                shutil.move(os.path.join(nested, entry),
                            os.path.join(self.source_folder, entry))
            os.rmdir(nested)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler_env_prefix(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        cxx = executables.get("cpp", "clang++")
        return f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "

    def build(self):
        apply_conandata_patches(self)
        prefix = shlex.quote(self.package_folder)
        # The 2001 config.guess cannot classify aarch64-linux-ohos (newest
        # upstream still does not know uname -s HarmonyOS), so pin the host
        # triple explicitly. configure/make run in-tree: the Makefile has no
        # VPATH support and the package dir doubles as the build dir.
        self.run(
            f"{self._compiler_env_prefix()}sh ./configure "
            f"--host=aarch64-linux-ohos --prefix={prefix} "
            f"--libdir={prefix}/lib --bindir={prefix}/bin --includedir={prefix}/include",
            cwd=self.source_folder,
            env="conanbuild",
        )
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        self.run(
            "make install",
            cwd=self.source_folder,
            env="conanbuild",
        )
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []  # tsocks installs no headers; empty dir keeps CMakeDeps honest
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["tsocks"]
