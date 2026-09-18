#!/usr/bin/env python3
"""Conan recipe for lrcalc 1.2 (Littlewood-Richardson calculator) on OHOS.

Upstream builds liblrcalc plus the command line programs `lrcalc` and
`schubmult`.  Build system: autotools; the tarball ships a 2014 vintage
generated `configure`.

OHOS notes
----------
* The bundled config.guess/config.sub predate HarmonyOS/`ohos`, so
  patches 0001/0002 teach them the `HarmonyOS` uname (native builds run
  config.guess because conan only emits --host/--build triplets for
  cross builds) and the `linux-ohos*` OS token.
* On HMDFS a `umask 077` temp directory is not writable (setgid
  injection, knowledge E011/E129); patch 0003 relaxes the configure
  temp-dir umask to 022.
* The profile injects the harmonybrew bash as SHELL; on HMDFS that bash
  breaks libtool ("syntax error near unexpected token `}'") and even
  config.status (`print: command not found`, E386 family).  configure is
  therefore invoked with `CONFIG_SHELL=/bin/sh SHELL=/bin/sh` so the
  generated Makefiles use /bin/sh (tslib precedent).  make runs with
  -j1 because the HMDFS TMPDIR forbids the -j jobserver FIFO.
* The upstream test suite (`make check` -> `testsuite`, 8 checks) is
  executed from build() and must fully pass (R51).
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


class LrcalcConan(ConanFile):
    name = "lrcalc"
    version = "1.2"
    description = "Littlewood-Richardson calculator: symmetric-function C library with the lrcalc and schubmult command line programs"
    license = "GPL-2.0-or-later"
    homepage = "https://sites.math.rutgers.edu/~asbuch/lrcalc/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_env(self):
        """Explicit compiler environment (R33).

        The OHOS adapted conan exposes the toolchain compilers through
        ``tools.build:compiler_executables``; the CI profile leaves that
        conf empty and only puts clang/clang++ on PATH, so fall back to
        those names (tslib/adplay precedent).
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        if bindir:
            env.define("AR", compilers.get("ar") or os.path.join(bindir, "llvm-ar"))
            env.define(
                "RANLIB", compilers.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
            )
        return env

    def build(self):
        apply_conandata_patches(self)
        shared_args = (
            "--enable-shared --disable-static"
            if self.options.shared
            else "--disable-shared --enable-static"
        )
        with self._compiler_env().vars(self).apply():
            self._run(
                "CONFIG_SHELL=/bin/sh SHELL=/bin/sh ./configure "
                f'--prefix="{self.package_folder}" {shared_args}'
            )
            self._run("make -j1")
            # R51: upstream test suite (Makefile.am: TESTS = testsuite, 8 checks).
            self._run("make -j1 check")
            self._run("make -j1 install")

    def _run(self, command):
        self.run(f'cd "{self.source_folder}" && {command}', env="conanbuild")

    def package(self):
        rm(self, "*.la", self.package_folder, recursive=True)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["lrcalc"]
        # Upstream installs every header into include/lrcalc while the
        # headers include their siblings with angle brackets
        # (`#include <hashtab.h>`), so both include roots are exported.
        self.cpp_info.includedirs = ["include", "include/lrcalc"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "lrcalc")
        self.cpp_info.set_property("cmake_target_name", "lrcalc::lrcalc")
