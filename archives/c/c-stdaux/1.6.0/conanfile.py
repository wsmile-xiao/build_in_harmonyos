#!/usr/bin/env python3
"""Conan recipe for c-stdaux 1.6.0 — Meson header-only library.

c-stdaux provides auxiliary macros and functions for the C standard library
(four public headers, no compiled library). Upstream is a meson project; the
recipe builds and runs the two upstream test programs in build() and installs
the headers. The pkg-config filebase is "libcstdaux-1" (what dependent
projects such as c-rbtree query via dependency('libcstdaux-1')), and the
upstream-exported cflags variable is reduced to its functional member
-D_GNU_SOURCE (the remaining entries are compiler-specific warning switches).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class CStdauxConan(ConanFile):
    name = "c-stdaux"
    version = "1.6.0"
    description = "Auxiliary macros and functions for the C standard library"
    license = "Apache-2.0"
    homepage = "https://github.com/c-util/c-stdaux"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream is a meson project (meson_version >= 0.60); CI worker
        # sandboxes have no meson, so pull it from the artifact repo.
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.generate()
        # Meson probes a static archiver while detecting the C toolchain; the
        # native file names no `ar`, and CI worker PATHs carry no bare
        # llvm-ar/ar (§6.2) -> "Unknown linker(s): [['llvm-ar']]". Pin the
        # archiver next to the compiler the profile already pins absolutely
        # (bstring precedent: /data/service/hnp/bin/ar is CI-proven).
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        with open(native_file) as f:
            content = f.read()
        marker = "[binaries]\nc ="
        if marker not in content:
            raise ConanInvalidConfiguration(
                "meson native file layout changed: '[binaries]\\nc =' not found"
            )
        ar_abs = "/data/service/hnp/bin/ar"
        if "ar =" not in content.split("[binaries]", 1)[1].split("\n\n", 1)[0]:
            content = content.replace(
                marker, "[binaries]\nar = '{}'".format(ar_abs) + "\nc =", 1
            )
            with open(native_file, "w") as f:
                f.write(content)
            self.output.info("  [ok] pinned meson archiver to " + ar_abs)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            # The complete upstream suite: test-api + test-basic, registered
            # via meson test() in src/meson.build.
            meson.test()
        else:
            self.output.info(
                "Skipping upstream meson tests: target binaries cannot run here"
            )

    def package(self):
        meson = Meson(self)
        meson.install()
        # Keep the package header-only; consumers get their pkg-config files
        # from Conan's PkgConfigDeps instead of the upstream-generated one.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "c-stdaux")
        self.cpp_info.set_property("cmake_target_name", "c-stdaux::c-stdaux")
        # Upstream exports -D_GNU_SOURCE to dependent projects via its
        # pkg-config cflags variable; mirror that contract here. Downstream
        # c-util meson projects also read dep.get_variable('version_scripts')
        # (e.g. c-utf8 1.1.0 guards its version-script link flag on it), so
        # expose the upstream default ("no" unless feature-detected) to keep
        # such get_variable calls working against the Conan-generated .pc.
        self.cpp_info.defines = ["_GNU_SOURCE"]
        self.cpp_info.set_property("pkg_config_name", "libcstdaux-1")
        self.cpp_info.set_property(
            "pkg_config_custom_content",
            "cflags=-D_GNU_SOURCE\nversion_scripts=no",
        )
