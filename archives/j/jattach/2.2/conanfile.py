#!/usr/bin/env python3
"""Conan recipe for jattach 2.2 (plain Makefile).

jattach is a tiny JVM Dynamic Attach utility: a single native binary that
sends diagnostic commands (threaddump, dumpheap, jcmd, setflag, ...) to a
running HotSpot or OpenJ9 JVM through the Dynamic Attach mechanism, without
needing a JDK.  Pure C, POSIX only, no third-party dependencies (W0).

Adaptation notes (HarmonyOS PC, aarch64):
    * Upstream has no configure script: build with the project Makefile
      (`make` -> build/jattach).  No source patches are required; the OHOS
      clang 15 toolchain defines __linux__/__NR_setns and provides
      <sys/sem.h>, so the Linux branch of src/posix/psutil.c and the OpenJ9
      code path compile unmodified.
    * The compiler is taken from the Conan conf
      (tools.build:compiler_executables:c), never from a bare shell
      variable (R33).
    * Artifacts: bin/jattach.  Declared in archives/j/jattach/commands.json
      per R38.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JattachConan(ConanFile):
    name = "jattach"
    version = "2.2"
    description = "JVM Dynamic Attach utility (jmap/jstack/jcmd/jinfo in one tiny binary)"
    license = "Apache-2.0"
    homepage = "https://github.com/jattach/jattach"
    url = "https://github.com/jattach/jattach"
    topics = ("jvm", "attach", "hotspot", "openj9", "diagnostics")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS must be accepted next to Linux
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "jattach only supports POSIX/Linux-family targets, not {0}".format(self.settings.os)
            )

    def source(self):
        # The codeload URL ends with the bare tag ("v2.2"), which Conan's
        # get() would otherwise use as the file name (no extension -> wrong
        # decoder).  An explicit *.tar.gz name selects the tar.gz decoder
        # (same pattern as archives/a/abcmidi).
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            filename="jattach-2.2.tar.gz",
        )

    def build(self):
        # No patches are required for 2.2 (see notes.md); the call keeps the
        # recipe ready for future portability fixes.
        apply_conandata_patches(self)
        # R33: compiler path comes from the Conan profile, not the shell env.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        with chdir(self, self.source_folder):
            # R9: keep the build serial.
            self.run("make -j1 CC={0}".format(cc))

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "jattach",
            src=os.path.join(self.source_folder, "build"),
            dst=os.path.join(self.package_folder, "bin"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
