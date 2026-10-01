#!/usr/bin/env python3
"""Conan recipe -- kma 1.4.21 (K-mer Mapping and Alignment).

KMA maps/aligns raw reads directly against redundant DNA/protein databases
using two k-mer mapping steps and one alignment step.
Upstream: https://bitbucket.org/genomicepidemiology/kma (git repo).  Upstream
publishes no release artifact and no upstream-published checksum -- what this
recipe takes is the archive Bitbucket generates on demand for tag 1.4.21, so the
sha256 in the data file is our own build-host measurement rather than an
upstream statement, and it is a per-tag snapshot, not a signed release.  The
content is plain upstream (no distro repackaging directory, no dfsg-style
stripping, no patches) and was re-verified on the build host to be byte-for-byte
identical to the pristine archive pinned here before: diff -rq zero, 148 regular
files per side, per-file sha256 manifests identical (see notes.md, source
section).

Build facts (all measured on HarmonyOS PC, clang 15 -- see notes.md):
  * zlib is a hard dependency: Makefile links ``-lz`` (Makefile:12,15) and
    filebuff.c includes zlib.h (filebuff.c:22) and calls inflateInit2
    (filebuff.c:102).
  * No configure script, no install target: ``make`` builds four programs
    ``kma kma_index kma_shm kma_update`` from 64 .c files; package() therefore
    copies the binaries itself.
  * Upstream default flags are ``CFLAGS ?= -Wall -O3`` plus ``CFLAGS +=
    -std=c99``.  A make *command line* CFLAGS assignment suppresses that ``+=``
    (GNU make semantics), so -Wall -O3 -std=c99 are re-stated explicitly here
    together with the zlib include dir -- otherwise the build would silently
    lose the C99 standard request.
  * R33: compiler/archiver come from Conan conf, never from bare shell vars.
  * R9: ``make -j1``.

Platform capability / delivery scope (no upstream source was modified):
  The default template-DB load path hashMapKMA_load() (hashmapkma.c:275) calls
  ftok()+shmget() unconditionally (hashmapkma.c:319/349/385/416) and this
  platform's seccomp-BPF filter kills those syscalls with SIGSYS(31), so the
  in-source "else load from file" fallback is unreachable.  The delivered usage
  is upstream's own ``-mmap`` switch (help text kma.c:144; kma.c:525-527 set
  ``shm |= 32`` and route teardown through hashMapKMA_munmap; kmers.c:86-87 and
  sparse.c:381-382 then call hashMapKMAmmap() from kmmap.c:33, a pure
  file-backed mmap which the platform allows).  ``kma db`` (db.c:59) and
  ``kma shm``/``-shm`` have no non-SysV path and are documented as unavailable
  on this platform in notes.md and in the software README.
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class KmaConan(ConanFile):
    name = "kma"
    version = "1.4.21"
    description = ("KMA - k-mer mapping and alignment of raw reads against "
                   "redundant DNA/protein databases")
    license = "Apache-2.0"
    homepage = "https://bitbucket.org/genomicepidemiology/kma"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Makefile:12,15 link -lz; filebuff.c:22,102 use inflateInit2.
        self.requires("zlib/1.3.1.1")

    def validate(self):
        # R32: OHOS must be accepted next to Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os=%s is not supported" % self.settings.os)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value).replace("\\", "/"))

    def _c_compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c", "clang")

    def _archiver(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "")
        cc_dir = os.path.dirname(cc)
        candidate = (os.path.join(cc_dir, "llvm-ar")
                     if cc_dir else "llvm-ar")
        return candidate if os.path.exists(candidate) else "ar"

    def _dependency_flags(self):
        """zlib include/lib dirs straight from the dependency cpp_info."""
        include_flags = []
        libdir_flags = []
        cpp_info = self.dependencies["zlib"].cpp_info
        include_flags.extend("-I%s" % p for p in cpp_info.includedirs)
        libdir_flags.extend("-L%s" % p for p in cpp_info.libdirs)
        return include_flags, libdir_flags

    def _conf_list(self, name):
        return [str(v) for v in self.conf.get(name, default=[],
                                              check_type=list)]

    def _make_arguments(self):
        include_flags, libdir_flags = self._dependency_flags()
        # Upstream: CFLAGS ?= -Wall -O3 ; CFLAGS += -std=c99
        cflags = (["-Wall", "-O3", "-std=c99"]
                  + include_flags
                  + self._conf_list("tools.build:cflags"))
        ldflags = (libdir_flags
                   + self._conf_list("tools.build:exelinkflags"))
        assignments = {
            "CC": self._c_compiler(),
            "AR": self._archiver(),
            "CFLAGS": " ".join(cflags),
            "LDFLAGS": " ".join(ldflags),
        }
        return " ".join("%s=%s" % (k, self._quote(v))
                        for k, v in assignments.items())

    def build(self):
        apply_conandata_patches(self)
        # Upstream has no check/test target (Makefile targets: all, kma,
        # kma_index, kma_shm, kma_update, libkma.a, clean + 56 .o rules);
        # behaviour is asserted by test_package instead.
        self.run("make -j1 all %s" % self._make_arguments(),
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        # Upstream Makefile PROGS (Makefile:4) -- all four are installed.
        for prog in ("kma", "kma_index", "kma_shm", "kma_update"):
            copy(self, prog, self.source_folder, bindir, keep_path=False)
            exe = os.path.join(bindir, prog)
            if os.path.isfile(exe) and os.name != "nt":
                # HMDFS: fresh copies are 0660 without this.
                os.chmod(exe, 0o755)
        # Upstream ships no LICENSE file; the Apache-2.0 header lives in the
        # 128 source files themselves -- keep a pointer for consumers.
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "share", "kma"),
             keep_path=False)
        copy(self, "KMAspecification.pdf", self.source_folder,
             os.path.join(self.package_folder, "share", "kma"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.buildenv_info.prepend_path("PATH",
                                        os.path.join(self.package_folder,
                                                     "bin"))
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
