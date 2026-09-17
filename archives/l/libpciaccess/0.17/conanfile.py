#!/usr/bin/env python3
"""Conan recipe — libpciaccess 0.17 (Meson).

PCI bus access library for X.Org, adapted for OpenHarmony PC (arm64).

R32: settings.os check uses in ("Linux", "OHOS").
R33: build() uses Conan MesonToolchain, no bare shell env vars.
R34: test_package calls pci_get_strings/pci_system_init APIs.
R38: package installs the library only (upstream 0.17 does not install
     scanpci — its meson target lacks install: true), so this is a pure
     library package and no commands.json is declared.
R51: upstream 0.17 registers zero Meson test() entries; `meson test` is
     still invoked in build() and completes with "No tests defined.".
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibpciaccessConan(ConanFile):
    name = "libpciaccess"
    version = "0.17"
    description = "Generic PCI access library for X.Org"
    license = "MIT", "X11"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libpciaccess"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # common_device_name.c gzopens the (optionally compressed) pci.ids
        # database; zlib support must stay enabled — no feature trimming.
        self.requires("zlib/1.3.1")

    def validate(self):
        # R32: Platform check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpciaccess only supports Linux/OHOS, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

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
        # R51: upstream 0.17 ships no test() registrations; this still runs
        # the official test entry point and completes with zero tests.
        self.run(
            f"meson test -C {self.build_folder} --print-errorlogs",
            env="conanbuild",
        )

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["pciaccess"]
        self.cpp_info.set_property("pkg_config_name", "pciaccess")
