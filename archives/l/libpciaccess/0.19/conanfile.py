#!/usr/bin/env python3
"""Conan recipe — libpciaccess 0.19 (Meson)."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibpciaccessConan(ConanFile):
    name = "libpciaccess"
    version = "0.19"
    description = "Generic PCI access library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libpciaccess"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["zlib"] = "enabled"
        toolchain.project_options["linux-rom-fallback"] = False
        toolchain.project_options["install-scanpci"] = False
        toolchain.generate()
        self._inject_meson_archive_tools()

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        with open(native_file, encoding="utf-8") as native:
            content = native.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        tools = f"[binaries]\nar = '{ar}'\n"
        if os.path.isfile(ranlib):
            tools += f"ranlib = '{ranlib}'\n"
        with open(native_file, "w", encoding="utf-8") as native:
            native.write(content.replace("[binaries]\n", tools, 1))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self.run(
            f"meson test -C {self.build_folder} --print-errorlogs",
            env="conanbuild",
        )

    def package(self):
        Meson(self).install()

    def package_info(self):
        self.cpp_info.libs = ["pciaccess"]
