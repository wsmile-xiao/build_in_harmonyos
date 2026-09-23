#!/usr/bin/env python3
"""Conan recipe for the t1ha fast positive hash library (raw Makefile).

t1ha 2.1.4 is a portable non-cryptographic 64/128-bit hash library.  The
upstream Makefile builds objects once with CFLAGS_LIB (-fPIC, hidden
visibility) and links libt1ha.a / libt1ha.so from them; there is no
configure step and no install target, so the recipe drives explicit make
targets and copies t1ha.h plus the requested library flavour.

OHOS notes:
- aarch64 compiles the "portable" arch branch: the Makefile's x86 AES-NI
  objects are gated behind TARGET_ARCH_ia32 and compiled out, and t1ha.h
  enables GNU IFUNC dispatch only on ELF x86_64, so no musl conflict.
- Upstream tests/main.c ships an invalid `#elseif` preprocessor directive
  (fixed by patches/0001, tests-only); everything else compiles as-is.
- The upstream test binary is built and executed inside build() on native
  runs; its 12 "Testing ... Ok" entries are the upstream suite evidence.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class T1haConan(ConanFile):
    name = "t1ha"
    version = "2.1.4"
    description = (
        "Fast Positive Hash: portable non-cryptographic 64/128-bit hash "
        "functions (t1ha0/t1ha1/t1ha2, streaming and one-shot APIs)"
    )
    license = "Zlib"
    homepage = "https://github.com/PositiveTechnologies/t1ha"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "t1ha requires a POSIX-like target (Linux or OHOS), "
                f"not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_executables(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        return cc, cxx

    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._compiler_executables()
        # Serial build: the upstream objects compile in seconds and the
        # device jobserver adds only noise at higher parallelism.
        make_prefix = f'make CC="{cc}" CXX="{cxx}"'
        library_target = (
            "libt1ha.so" if bool(self.options.shared) else "libt1ha.a"
        )
        self.run(f"{make_prefix} {library_target}", cwd=self.source_folder)
        if can_run(self):
            # Native run: build and execute the upstream test binary; the
            # harness prints one "Testing <name>... Ok" line per entry and
            # exits non-zero if any probe fails.
            self.run(f"{make_prefix} test", cwd=self.source_folder)
            self.run("./test --test-only", cwd=self.source_folder)
        else:
            self.output.info(
                "Cross build: t1ha upstream test binary was not executed "
                "here; run it on the HarmonyOS PC target."
            )

    def package(self):
        copy(
            self,
            "t1ha.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        lib_pattern = "libt1ha.so*" if bool(self.options.shared) else "libt1ha.a"
        copy(
            self,
            lib_pattern,
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["t1ha"]
        self.cpp_info.set_property("cmake_file_name", "t1ha")
        self.cpp_info.set_property("cmake_target_name", "t1ha::t1ha")
        self.cpp_info.set_property("pkg_config_name", "t1ha")
