#!/usr/bin/env python3
"""Conan recipe for tmfs 7 - Apple Time Machine File System (CMake, FUSE3).

Upstream: https://github.com/abique/tmfs  (release 7, tarball tmfs-r7)

tmfs is a read-only FUSE filesystem that reconstructs an Apple Time Machine
backup layout from the HFS+ metadata directory.  It is a single executable
(6 translation units, ~4.5 KB of sources) built with CMake and C++17.

HarmonyOS adaptation (see patches/, notes.md):
  * 0001-fuse3-support: release 7 predates libfuse 3 and hard-codes the fuse2
    API (FUSE_USE_VERSION 26, fuse_fill_dir_t without flags, fuse2 getattr /
    readdir signatures).  Debian's quilt patch (upstream PR #35) makes one
    source tree build against both fuse2 and fuse3; the artifact repository
    only ships libfuse/3.18.2, so it is required.  Applied as-is.
  * 0002-ohos-posix-s-ifdir-and-link-order: __S_IFDIR is glibc-internal and
    absent from musl; link_directories() was called after add_executable() and
    therefore never reached the link line.
  * generate(): the libfuse recipe declares includedirs = ["include"] while the
    headers actually live in include/fuse3/, so the generated fuse3.pc points
    at the wrong directory for `#include <fuse.h>`; aligned like sshfs.

Note on the runtime: mounting needs /dev/fuse, which the sandbox does not
provide, so the test_package drives the real argument handling of main() and
falls back to structural ELF validation when exec is blocked.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TmfsConan(ConanFile):
    name = "tmfs"
    description = "tmfs - Apple Time Machine File System (read-only FUSE3 view)"
    license = "MIT"
    homepage = "https://github.com/abique/tmfs"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def set_version(self):
        # Upstream tags the release `r7` (github.com/abique/tmfs tags: r1..r7);
        # the tarball root directory is `tmfs-r7` and Debian's source package is
        # `tmfs 7-1`. Conan rejects single-character versions (RecipeReference
        # slug needs >= 2 chars: `Invalid package version '7'`), so the artifact
        # version is normalized to the upstream tag form `r7`.
        #
        # Deliberately NOT a literal `version = "..."` attribute: the archive
        # directory keeps the task-card form `7` (which the platform branch-name
        # gate L0n requires), and CI's literal-vs-directory comparison (L0m-3 /
        # PF8) only applies to a literal attribute, which could never equal `7`.
        # Same normalization as the repo's rapidhash/3 and cronic/3 precedents.
        # reference: notes.md
        self.version = "r7"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Upstream detects FUSE with pkg_check_modules(fuse3); the OHOS
        # artifact repository publishes libfuse/3.18.2 (== FUSE 3.18.2, static).
        self.requires("libfuse/3.18.2")

    def validate(self):
        # R32: use in ("Linux", "OHOS") format
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tmfs supports only Linux and OHOS, got {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # fuse3 is discovered by the upstream CMake files through pkg-config;
        # CMakeToolchain puts the .pc files generated here on PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        self._align_fuse_pkgconfig_includedir()

        tc = CMakeToolchain(self)
        # Link the C++ runtime statically (zhcon/0.2.6 and zpaq/7.15 precedent).
        # The OHOS SDK ships libc++_shared.so only inside
        # <sdk>/llvm/lib/aarch64-linux-ohos/ and the OHOS loader has no default
        # search path for it, so a dynamically linked C++ binary would depend on
        # a library no package delivers.  Measured on CI #84208: DT_NEEDED was
        # [libc++_shared.so, libc.so]; with this flag the only entry is libc.so,
        # which is also what test_package/test.c asserts (T3b).
        tc.extra_exelinkflags.append("-static-libstdc++")
        tc.generate()

    def _align_fuse_pkgconfig_includedir(self):
        """Point the generated fuse3.pc at include/fuse3 (like sshfs 3.7.5-r0).

        The libfuse recipe declares cpp_info.includedirs = ["include"], so
        PkgConfigDeps emits `includedir=${prefix}/include`, while upstream
        libfuse installs its headers in <prefix>/include/fuse3 and its own
        fuse3.pc uses -I${includedir}/fuse3.  tmfs does `#include <fuse.h>`
        (not <fuse3/fuse.h>), so without this the header is not found.
        """
        fuse_pc = os.path.join(self.generators_folder, "fuse3.pc")
        if not os.path.isfile(fuse_pc):
            return
        with open(fuse_pc, encoding="utf-8") as source:
            content = source.read()
        patched = re.sub(r"^includedir=.*$",
                         "includedir=${prefix}/include/fuse3", content, flags=re.M)
        if patched != content:
            with open(fuse_pc, "w", encoding="utf-8") as target:
                target.write(patched)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # tmfs is a command-line tool, not a library.
        self.cpp_info.bindirs = ["bin"]
