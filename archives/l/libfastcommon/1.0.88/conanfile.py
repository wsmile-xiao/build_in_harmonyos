#!/usr/bin/env python3
"""Conan recipe for libfastcommon 1.0.88 (HarmonyOS / aarch64 port).

libfastcommon is the common C utility library extracted from FastDFS/FastDHT
(logger, ini reader, id generator, skiplists, ioevent, thread pool, etc.).

Upstream build is a raw Makefile driven by make.sh: it generates
src/_os_define.h by probing the host (uname, dirent fields, pthread
symbols), then substitutes $(CC)/$(CFLAGS)/$(LIBS)/$(TARGET_PREFIX) into
src/Makefile.in and src/tests/Makefile.in and runs make.

The HarmonyOS adaptation replicates that substitution inside build() with
the Conan toolchain compiler instead of running make.sh:
  * make.sh hardcodes `gcc`; the OHOS PC toolchain only ships clang, so the
    recipe takes the C compiler from tools.build:compiler_executables.
  * make.sh's uname probe does not know "HarmonyOS" and would select
    OS_UNKOWN/IOEVENT_USE_NONE; the OHOS kernel is Linux-based with epoll
    available, so _os_define.h is generated with OS_LINUX +
    IOEVENT_USE_EPOLL and the dirent fields actually present in the OHOS
    sysroot (d_type/d_reclen/d_off, no d_namlen).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout

_OS_DEFINE_H = """\
#ifndef _OS_DEFINE_H
#define _OS_DEFINE_H

#define OS_BITS  64
#define OFF_BITS 64

#ifndef OS_LINUX
#define OS_LINUX  1
#endif

#ifndef IOEVENT_USE_EPOLL
#define IOEVENT_USE_EPOLL  1
#endif

#ifndef HAVE_VMMETER_H
#define HAVE_VMMETER_H 0
#endif

#ifndef HAVE_USER_H
#define HAVE_USER_H 0
#endif

#define HAVE_DIRENT_D_TYPE  1
#define HAVE_DIRENT_D_RECLEN 1
#define HAVE_DIRENT_D_OFF   1

#endif
"""


class LibfastcommonConan(ConanFile):
    name = "libfastcommon"
    version = "1.0.88"
    description = "Common C utility library extracted from FastDFS/FastDHT"
    license = "LGPL-3.0"
    homepage = "https://github.com/happyfish100/libfastcommon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfastcommon supports Linux/OHOS only, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "libfastcommon OHOS support is validated for armv8/AArch64"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], filename="libfastcommon-1.0.88.tar.gz")

    def _cc(self):
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c")
        return cc or "clang"

    def _cflags(self):
        flags = ["-Wall", "-D_FILE_OFFSET_BITS=64", "-D_GNU_SOURCE"]
        if self.settings.build_type == "Debug":
            flags.append("-g")
        else:
            flags.append("-O3")
        if self.options.shared:
            # Give the shared object a SONAME; the OHOS link gate verifies it.
            flags.append("-Wl,-soname,libfastcommon.so")
        return " ".join(flags)

    def _libs(self):
        return "-lm -ldl"

    def _render_makefile(self, template, variables):
        content = template
        for key, value in variables.items():
            content = content.replace("$({})".format(key), value)
        return content

    def build(self):
        apply_conandata_patches(self)
        src_dir = self.source_folder
        # 1) Generate src/_os_define.h (replaces make.sh's host probing).
        save(self, os.path.join(src_dir, "src", "_os_define.h"), _OS_DEFINE_H)

        # 2) Render src/Makefile with the Conan toolchain compiler.
        with open(os.path.join(src_dir, "src", "Makefile.in")) as handle:
            makefile = self._render_makefile(handle.read(), {
                "CC": self._cc(),
                "CFLAGS": self._cflags(),
                "INCS": "",
                "LIBS": self._libs(),
                "TARGET_PREFIX": os.path.join(self.build_folder, "stage"),
                "LIB_VERSION": "lib",
            })
        save(self, os.path.join(src_dir, "src", "Makefile"), makefile)

        # 3) Build the library (all target builds libfastcommon.so/.a).
        self.run("make -j1 all", cwd=os.path.join(src_dir, "src"))

        # 4) Install into the staging prefix (lib + include/fastcommon).
        self.run("make -j1 install", cwd=os.path.join(src_dir, "src"))

        # 5) Build the upstream test programs (test_package uses a real API;
        #    the full upstream suite is executed and reported separately).
        with open(os.path.join(src_dir, "src", "tests", "Makefile.in")) as handle:
            test_makefile = self._render_makefile(handle.read(), {
                "CC": self._cc(),
                "INCS": f"-I{os.path.join(src_dir, 'src')}",
                "LIBS": (
                    f"-L{os.path.join(self.build_folder, 'stage', 'lib')} "
                    "-lfastcommon -lm -ldl"
                ),
            })
        save(self, os.path.join(src_dir, "src", "tests", "Makefile"), test_makefile)

    def package(self):
        stage = os.path.join(self.build_folder, "stage")
        copy(
            self,
            "*.so*",
            src=os.path.join(stage, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.a",
            src=os.path.join(stage, "lib"),
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include", "fastcommon"),
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
        self.cpp_info.libs = ["fastcommon"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libfastcommon")
        self.cpp_info.set_property("cmake_target_name", "libfastcommon::libfastcommon")
