#!/usr/bin/env python3
"""Conan recipe for retry 1.0.6 — repeat a command until a criteria is met.

retry is a single-binary Autotools CLI tool (retry.c, ~22 KB).  It captures
stdin into memory and replays it when a command is repeated, and routes the
stdout of failed attempts to stderr so that stdout is emitted once and once
only in shell pipelines.  Criteria are success/fail, integers or ranges, with
optional --times and --delay/--jitter.

The upstream release tarball ships a fully generated Autotools tree
(configure, Makefile.in, config.h.in, build-aux/, m4/), so the recipe runs the
real upstream configure + make + install.

OHOS adaptations (patches in conandata.yml):
  - build-aux/config.guess: report aarch64-unknown-linux-ohos if uname -s is
    HarmonyOS.  The bundled 2018 config.guess does not know HarmonyOS and
    native builds (build == host, no --host/--build triplet) make configure
    abort with "cannot guess build type; you must specify one".
  - build-aux/config.sub: accept the linux-ohos OS token in both the
    3-component (maybe_os) and 4-component canonicalization paths, so both
    aarch64-linux-ohos (cross builds) and aarch64-unknown-linux-ohos
    (native config.guess output) canonicalize.
  - configure: create the config.status temporary directory with umask 022
    instead of 077.  HMDFS maps directory ownership to a different UID, so an
    0700 directory is not writable by the build process (knowledge E011).
None of the patches inject platform macros; they are plain portability fixes
(R8/PF5).

Upstream tests: the project ships no test suite — there is no tests/ tree, no
TESTS/check_PROGRAMS/check-local in Makefile.am, and no test-related configure
option; `make check` executes zero cases.  build() still runs `make check` so
every build log carries that evidence, and test_package/test_retry.sh provides
the consumer-side regression tests required for the no-upstream-tests case
(R51; evidence in test_package/MANIFEST.yml).

Artifacts: bin/retry + share/man/man1/retry.1 (the software-level
commands.json declares the CLI, R38).  License: Apache-2.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RetryConan(ConanFile):
    name = "retry"
    version = "1.0.6"
    description = (
        "Repeat a command until a criteria is met, usually success "
        "(standard input is captured and replayed between retries)"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/minfrin/retry"
    url = "https://github.com/minfrin/retry"
    topics = ("retry", "cli", "automation", "shell", "utility")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: check the OHOS family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "retry requires a POSIX host (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        # R9: single job — the HMDFS jobserver FIFO breaks parallel make (E074).
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream ships no tests; run the (empty) automake check target so the
        # build log records that `make check` executes zero cases (R51).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
