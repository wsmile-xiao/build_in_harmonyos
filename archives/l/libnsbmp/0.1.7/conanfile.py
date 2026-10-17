#!/usr/bin/env python3
"""Conan recipe for libnsbmp 0.1.7 (NetSurf BMP/ICO decoding library).

libnsbmp uses the NetSurf project's own build system (NSSHARED /
netsurf-buildsystem), which is neither a standard autotools/cmake/meson
project nor packaged for OHOS. A standalone Makefile patch replaces the
NSSHARED include so the upstream compile, install and official test
runner (test/runtest.sh over the full BMP+ICO corpus) work unmodified on
HarmonyOS/OpenHarmony.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibnsbmpConan(ConanFile):
    name = "libnsbmp"
    version = "0.1.7"
    description = "Decoding library for BMP and ICO image file formats"
    license = "MIT"
    homepage = "https://www.netsurf-browser.org/projects/libnsbmp/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    # Upstream defaults to a static library (COMPONENT_TYPE ?= lib-static).
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libnsbmp is supported only on Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── Tool resolution ──────────────────────────────────────────────
    # Raw makefile build: no CMakeToolchain/AutotoolsToolchain applies, so
    # the profile-configured compiler (tools.build:compiler_executables) is
    # resolved here and passed as make command-line variables. L0h forbids
    # bare ${CC}/${CFLAGS} shell references inside self.run(); these are
    # Python-resolved values, not shell variable expansions.

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        return compilers.get("c", "clang")

    def _tool(self, name):
        """Resolve an LLVM tool (llvm-ar/llvm-ranlib) co-located with CC."""
        cc = self._cc()
        if "/" in cc:
            return os.path.join(os.path.dirname(cc), name)
        return name

    def _cflags(self):
        flags = []
        if self.options.get_safe("fPIC", True):
            flags.append("-fPIC")
        if str(self.settings.build_type) == "Debug":
            flags.extend(["-g", "-O0"])
        else:
            flags.append("-O2")
        return " ".join(flags)

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        ar = self._tool("llvm-ar")
        ranlib = self._tool("llvm-ranlib")
        cflags = self._cflags()
        make_vars = f'CC="{cc}" AR="{ar}" RANLIB="{ranlib}" CFLAGS="{cflags}"'

        # Build the static library + pkg-config file.
        # No -j: libnsbmp is a single translation unit, and make's jobserver
        # uses mkfifo which HMDFS rejects (EACCES) on HarmonyOS.
        self.run(f"make {make_vars}", cwd=self.source_folder)

        # Upstream official test runner: test/runtest.sh decodes the full
        # BMP corpus (bmpsuite + bmp + afl-bmp + ns-afl-bmp = 1070 files)
        # and ICO corpus (icons + afl-ico + ns-afl-ico = 611 files) through
        # test_decode_bmp / test_decode_ico, reporting pass/error counts.
        # runtest.sh resolves test data relative to the source root, so it
        # must run from the source directory.
        self.run(f"make {make_vars} check", cwd=self.source_folder)

    def package(self):
        build_out = os.path.join(self.source_folder, "build")

        # Static library
        copy(self, "libnsbmp.a", src=build_out,
             dst=os.path.join(self.package_folder, "lib"))

        # Public header
        copy(self, "libnsbmp.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

        # pkg-config file (relocatable: prefix resolves at consumer time)
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_in = os.path.join(self.source_folder, "libnsbmp.pc.in")
        with open(pc_in, "r", encoding="utf-8") as f:
            pc_content = f.read()
        pc_content = pc_content.replace("PREFIX", "${pcfiledir}/../..")
        pc_content = pc_content.replace("LIBDIR", "lib")
        pc_content = pc_content.replace("INCLUDEDIR", "include")
        pc_content = pc_content.replace("VERSION", self.version)
        with open(os.path.join(pkgconfig_dir, "libnsbmp.pc"), "w", encoding="utf-8") as f:
            f.write(pc_content)

        # License
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["nsbmp"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libnsbmp")
        self.cpp_info.set_property("cmake_target_name", "libnsbmp::libnsbmp")
        self.cpp_info.set_property("pkg_config_name", "libnsbmp")
