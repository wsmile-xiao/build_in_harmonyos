#!/usr/bin/env python3
"""Conan recipe for runlim 1.10 — sample and limit time/memory of a program.

runlim runs a command and all its child processes, samples their CPU time,
wall-clock time and resident memory through the /proc filesystem, and stops
the run when a limit is exhausted.  It is the de-facto resource limiter of
the SAT/CP benchmarking community.

Upstream (Armin Biere, JKU) ships a single-file C program (runlim.c, ~930
lines) with a minimal POSIX build: `./configure.sh` substitutes CC/CFLAGS
into makefile.in (generating `makefile`) and `make` performs one compiler
invocation.  There is no install target, so package() copies the binary.

OHOS adaptations (patch in conandata.yml):
  - 0001-runlim.c.patch: RLIMIT_AS is set from the space limit expressed in
    MB, but the kernel expects bytes, so execvp always failed with ENOMEM
    whenever `-t`/`--time-limit` (or `-t` together with `-s`) triggered the
    setrlimit block.  The fix scales the value to bytes
    ((rlim_t) space_limit << 20).  Plain unit fix, no platform macro
    (R8/PF5).  Verified on the device: before the fix `runlim -t 1 sh -c ...`
    reported "execvp failed" (rc=1); after the fix it reports "out of time"
    (rc=2).

Upstream tests: none — the tarball has no tests/ tree, makefile.in defines
only the `runlim` and `clean` targets and configure.sh has no test switch
(inventory evidence in test_package/MANIFEST.yml, R51).  test_package/
test_runlim.sh provides the consumer-side regression suite (31 assertions
against the installed binary); the -t case doubles as the regression test
for the RLIMIT_AS fix.

Artifacts: bin/runlim (software-level commands.json declares the CLI, R38).
License: BSD-4-Clause (see LICENSE in the tarball).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class RunlimConan(ConanFile):
    name = "runlim"
    version = "1.10"
    description = (
        "Tool for sampling and limiting time and memory usage of a program "
        "and its child processes"
    )
    license = "BSD-4-Clause"
    homepage = "https://fmv.jku.at/runlim/"
    url = "https://fmv.jku.at/runlim/"
    topics = ("runlim", "resource-limits", "benchmarking", "procfs", "cli")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: check the OHOS family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "runlim requires a POSIX host with procfs (Linux or OHOS), "
                "not {0}".format(self.settings.os)
            )

    def layout(self):
        basic_layout(self)
        # Plain upstream Makefile project: configure.sh and make write into
        # the source folder (same pattern as the xa 2.4.1 recipe).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang") if compilers else "clang"
        # R5: configure.sh is a POSIX sh script — run it with the shell the
        # profile provides (CI worker: /data/service/hnp/bin/bash).
        shell = os.environ.get("CONFIG_SHELL", "sh")
        # R33: the compiler comes from the Conan conf, never a bare shell
        # variable.  makefile.in inlines @CC@/@CFLAGS@ literally into the
        # compile rule, so the values must reach configure.sh through its
        # environment (it honours $CC/$CFLAGS when set).
        env = Environment()
        env.define("CC", cc)
        env.define("CFLAGS", "-O2 -DNDEBUG")
        with env.vars(self).apply():
            self.run("{0} ./configure.sh".format(shell))
        # R9: single job.
        self.run("make -j1")

    def package(self):
        copy(
            self,
            "runlim",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
