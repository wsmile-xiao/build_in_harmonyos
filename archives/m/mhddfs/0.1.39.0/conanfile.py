#!/usr/bin/env python3
"""Conan recipe for mhddfs 0.1.39.0 (upstream plain GNU Makefile build).

mhddfs is a libfuse 2.x consumer: it merges several source directories into a
single virtual mount point and picks the target directory for new files by
free space (mlimit). uthash is a header-only build dependency.

Platform adaptation (see patches/ and notes.md):
  - patch 0001 switches the hardcoded `gcc` in the upstream compile/link rules
    to $(CC) so the Conan-provided OHOS clang is honoured;
  - patch 0002 adds src/pthread_stubs.c: consumer-side shims for the OHOS C
    library's missing pthread_cancel/pthread_setcancelstate, which the static
    libfuse.a references unconditionally;
  - patch 0003 syncs the stale upstream VERSION macro ("0.1.39") with the
    release/package version 0.1.39.0, mirroring what the Debian build does;
  - the build uses upstream's own WITHOUT_XATTR switch because the OHOS sysroot
    ships <sys/xattr.h> instead of the legacy <attr/xattr.h> the xattr code
    includes (upstream documents xattr support as optional).

Runtime note: a real FUSE mount requires an ordinary process to be able to use
the kernel FUSE device. On HarmonyOS PC this is currently not the case
(/dev/fuse is not accessible, no fusermount helper), so the binary is packaged
and covered by consumer tests, while mounted-operation tests are reported as
environment-blocked in reports/test-report.md.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MhddfsConan(ConanFile):
    name = "mhddfs"
    version = "0.1.39.0"
    description = (
        "FUSE filesystem that merges several mount points into a single "
        "virtual directory tree"
    )
    license = "GPL-3.0-or-later"
    homepage = "http://mhddfs.uvw.ru/"
    url = "https://tracker.debian.org/pkg/mhddfs"
    topics = ("fuse", "filesystem", "union", "storage")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # FUSE 2.x protocol library (static build only, R26) + header-only uthash
        self.requires("libfuse/2.9.9")
        self.requires("uthash/2.4.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mhddfs requires a POSIX host with FUSE support (Linux/OHOS)"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)
        # Upstream is a plain Makefile project: build in the source folder.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        fuse = self.dependencies["libfuse"]
        uthash = self.dependencies["uthash"]

        cflags = ["-Wall", "-O2"]
        for dep in (fuse, uthash):
            for inc_dir in dep.cpp_info.includedirs:
                cflags.append("-I" + os.path.join(dep.package_folder, inc_dir))
        cflags += ["-DFUSE_USE_VERSION=26", "-MMD", "-DWITHOUT_XATTR"]
        cflags += ["-D" + define for define in fuse.cpp_info.defines]

        ldflags = []
        for lib_dir in fuse.cpp_info.libdirs:
            ldflags.append("-L" + os.path.join(fuse.package_folder, lib_dir))
        ldflags += ["-l" + lib for lib in fuse.cpp_info.libs]
        ldflags += ["-l" + lib for lib in fuse.cpp_info.system_libs]

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        self.output.info("mhddfs build: CC=%s" % cc)
        self.run(
            'make -j1 mhddfs CC="{}" CFLAGS="{}" LDFLAGS="{}"'.format(
                cc, " ".join(cflags), " ".join(ldflags)
            )
        )

    def package(self):
        copy(
            self,
            "mhddfs",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "mhddfs.1",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "LICENSE",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "COPYING",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
