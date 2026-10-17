#!/usr/bin/env python3
"""Conan recipe for libpfm 4.13.0 on HarmonyOS PC.

libpfm4 is the Linux performance monitoring (perfmon) support library,
pure C with no third-party dependencies. It uses a custom make-based
build (Makefile + config.mk), no autotools and no cmake.

Source: official git repo https://github.com/wcohen/libpfm4 (tag v4.13.0,
commit 3d77461cb966259c51f3b3e322564187f4bef7fb; verified sha256
b06071d7e528402a6504273ea700354ebfcf4b62ffe239cb6471fcdb04ae3f3d).

OHOS adaptation notes:
- uname -s reports "HarmonyOS"; libpfm gates Linux-only sources (perf_event
  glue, validate_perf.c) behind SYS=Linux, so the recipe builds with
  SYS=Linux (HarmonyOS kernel is Linux-based, perf_event syscall present).
- upstream config.mk defaults to -Werror; clang 15 flags an unused-but-set
  variable in lib/pfmlib_common.c and the OHOS sysroot emits a
  "#warning redirecting incorrect #include <sys/poll.h>" for perf_examples;
  we relax only those two warning classes and keep -Werror for everything
  else.
- the python/ binding dir is skipped via CONFIG_PFMLIB_NOPYTHON=y (it is a
  pure-python optional binding, off by default upstream; not part of the C
  library).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibpfmConan(ConanFile):
    name = "libpfm"
    version = "4.13.0"
    description = "Linux/HarmonyOS performance monitoring (perfmon) library"
    license = "MIT"
    homepage = "https://github.com/wcohen/libpfm4"
    url = "https://github.com/wcohen/libpfm4"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libpfm only supports Linux/OHOS targets")

    def _arch(self):
        mapping = {
            "armv8": "aarch64",
            "armv7": "arm",
            "armv7hf": "arm",
            "x86_64": "x86_64",
            "x86": "i386",
        }
        return mapping.get(str(self.settings.arch), str(self.settings.arch))

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # compiler from Conan conf (R33: never rely on undefined shell vars)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar") or "llvm-ar"
        nm = compilers.get("nm") or "llvm-nm"
        ranlib = compilers.get("ranlib") or "llvm-ranlib"

        dbg = ("-g -Wall -Werror -Wextra -Wno-unused-parameter "
               "-Wno-error=unused-but-set-variable -Wno-error=#warnings "
               "-D__WORDSIZE=64")
        shared = "y" if self.options.shared else "n"

        self.run(
            f'make -j1 SYS=Linux ARCH={self._arch()} CC="{cc}" AR="{ar}" NM="{nm}" '
            f'RANLIB="{ranlib}" CONFIG_PFMLIB_SHARED={shared} CONFIG_PFMLIB_NOPYTHON=y '
            f'"DBG={dbg}"',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "perfmon"),
             dst=os.path.join(self.package_folder, "include", "perfmon"))
        copy(self, "libpfm.a", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libpfm.so*", src=os.path.join(self.source_folder, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["pfm"]
        if self.options.shared:
            self.cpp_info.system_libs = ["m"]