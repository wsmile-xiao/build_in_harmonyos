#!/usr/bin/env python3
"""Conan recipe for mergerfs 2.40.2 - a FUSE based union filesystem.

mergerfs presents multiple directories (branches) as a single mount point and
lets the user pick the placement/read policy.  The official source tarball is
self-contained: it vendors a modified libfuse 2.x fork plus wyhash,
ghc::filesystem, fmt, optional-lite, concurrentqueue and scope_guard, so there
are no external dependencies.  The upstream Makefile builds everything with the
host compiler.

HarmonyOS / OHOS notes:

* OHOS bionic does not implement POSIX thread cancellation.  The vendored
  libfuse references ``pthread_cancel`` / ``pthread_setcancelstate``; these call
  sites are guarded behind the ``HAVE_PTHREAD_CANCEL`` feature macro (see
  ``patches/0001``), so OHOS builds omit them.
* OHOS folds ``librt`` into libc, so the upstream ``-lrt`` flag has no provider.
  The recipe overrides ``LDFLAGS`` with ``-pthread`` only.
* ``build/tests`` (acutest) is the upstream unit suite and is executed during
  the build.  The upstream ``tests/TEST_*`` integration scripts mount a real
  mergerfs filesystem and are blocked on OHOS because ``/dev/fuse`` is not
  accessible from the sandbox.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# tests/tests.cpp registers 15 acutest cases (126 TEST_CHECK assertions).
UPSTREAM_UNIT_CASES = 15


class MergerfsConan(ConanFile):
    name = "mergerfs"
    version = "2.40.2"
    description = "FUSE based union filesystem (merge/JBOD multiple paths)"
    license = "ISC"
    homepage = "https://github.com/trapexit/mergerfs"
    url = "https://github.com/trapexit/mergerfs"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mergerfs OHOS adaptation is validated on Linux/OHOS; got %s"
                % self.settings.os)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The git tag tarball (unlike the release tarball) does not ship the
        # VERSION file.  buildtools/update-version falls back to `cat VERSION`
        # and would then stamp the binary as "unknown"; recreate it.
        save(self, os.path.join(self.source_folder, "VERSION"), self.version)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)

        cc = self._compiler("c", "clang")
        cxx = self._compiler("cpp", "clang++")
        ar = self._compiler("ar", "llvm-ar")

        # Build the binary, its preload library and the upstream unit tests.
        # LDFLAGS is overridden on the command line (which suppresses the
        # upstream `-lrt` appended by the Makefile) because OHOS has no librt.
        self.run(
            'make tests preload -j1'
            ' CC="{cc}" CXX="{cxx}" AR="{ar}" LDFLAGS="-pthread"'.format(
                cc=cc, cxx=cxx, ar=ar),
            cwd=self.source_folder)

        mergerfs = os.path.join(self.source_folder, "build", "mergerfs")
        if not os.path.isfile(mergerfs):
            raise ConanInvalidConfiguration(
                "build did not produce build/mergerfs")

        # Execute the upstream acutest unit suite (fails the build on any case).
        self.run("./build/tests", cwd=self.source_folder)

    def package(self):
        copy(self, "build/mergerfs", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        for util in ("mergerfs-fusermount", "mount.mergerfs"):
            copy(self, "build/" + util, self.source_folder,
                 os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "build/preload.so", self.source_folder,
             os.path.join(self.package_folder, "lib", "mergerfs"),
             keep_path=False)
        copy(self, "man/mergerfs.1", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
