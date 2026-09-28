#!/usr/bin/env python3
"""Conan recipe for Yavta, the V4L2 test application."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class YavtaConan(ConanFile):
    name = "yavta"
    version = "0.0-git20260603.4257331"
    description = "Yet Another V4L2 Test Application"
    license = "GPL-2.0-or-later"
    homepage = "https://git.ideasonboard.org/yavta.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("Yavta is packaged here for HarmonyOS only")
        if self.settings.arch not in ("x86_64", "armv8"):
            raise ConanInvalidConfiguration("Yavta supports OHOS x86_64 and armv8 builds")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        archiver = self._meson_tool("llvm-ar", "ar")
        if not archiver:
            raise ConanInvalidConfiguration(
                "Unable to locate an OHOS archiver (llvm-ar or ar) for Meson"
            )
        toolchain.ar = archiver
        toolchain.generate()

    def _meson_tool(self, *names):
        """Resolve LLVM tools from the configured compiler or OHOS SDK."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured = compilers.get("ar")
        if configured:
            found = shutil.which(configured)
            if found:
                return found
            if os.path.isfile(configured):
                return configured

        compiler = compilers.get("c") or ""
        search_dirs = []
        compiler_dir = os.path.dirname(compiler)
        if compiler_dir:
            search_dirs.append(compiler_dir)
            search_dirs.append(os.path.dirname(os.path.realpath(compiler)))
        search_dirs.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                    "ohos/native/llvm/bin"
                )
            )
        )

        for directory in dict.fromkeys(search_dirs):
            for name in names:
                found = shutil.which(name, path=directory)
                if found:
                    return found
                candidate = os.path.join(directory, name)
                if os.path.isfile(candidate):
                    return candidate

        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING.GPL", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
