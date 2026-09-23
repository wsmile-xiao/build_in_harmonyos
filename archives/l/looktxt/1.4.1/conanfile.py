#!/usr/bin/env python3
"""Conan recipe for looktxt 1.4.1 — free-format text to scientific data converter.

looktxt scans an arbitrary text file for numerical fields and exports every data
set it finds (scalar / vector / matrix) as Matlab, IDL, Scilab, Octave, XML, YAML,
HTML, Raw (or NeXus/HDF5 when the optional NeXus API is available).  Data sets
get names derived from the file content, which is what removes the need for a
hand-written loader per instrument log format.

Adaptation notes (HarmonyOS PC, aarch64):
    * W0: no third-party dependencies — the upstream README states "pure C code,
      with no dependency"; only the optional NeXus/HDF5 export needs libNeXus,
      and `nexus` is not published in the ohpcd registry, so that code path is
      deliberately disabled (see build()).
    * Upstream is a single-target, one-translation-unit POSIX Makefile: six phony
      rules (all/install/clean/distclean/uninstall/test), no configure, no
      recursive make, and the binary itself comes from an implicit %: %.c rule
      (so CFLAGS/EXTRA_CFLAGS are not read by the compile line).  The compiler comes from the
      Conan conf (R33: never a bare ${CC}); jobs are pinned to -j1 because this
      is one translation unit anyway and it keeps the upstream test log
      deterministic, and `NEXUS_NAPI=` is passed on the make command line so the
      Makefile's `$(shell [ -f /usr/include/napi.h ] ...)` host probe can never
      leak the build host into the produced binary (a command-line variable also
      wins over the makefile assignment inside its `ifeq` guard).
    * build() runs the upstream regression target (`make test`: --version plus
      `--verbose --test` over the five bundled examples) and fails hard unless
      the log carries upstream's own "Test OK" marker with exit status 0 (R9: no
      skipping, no faked pass).  The suite runs under `timeout -k 5 600`, so a
      regression that reintroduces the hang fails with a clean diagnostic instead
      of pinning a core until the CI kills the job.  That suite is exactly what
      the single portability patch fixes: without it the scanner spins forever on
      examples/Al.lau.
    * package() copies artifacts directly — upstream `make install` needs
      install(1), which OHOS/toybox does not provide.

Artifacts: bin/looktxt + licenses/LICENSE + share/doc/looktxt/README.md
(the software-level commands.json declares the CLI tool, R38).
License: GPL-2.0-or-later.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LooktxtConan(ConanFile):
    name = "looktxt"
    version = "1.4.1"
    description = (
        "Convert any free format text file with numerical areas into scientific "
        "data formats (Matlab, IDL, Scilab, Octave, XML, YAML, HTML, Raw)"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt"
    url = "https://gitlab.com/soleil-data-treatment/soleil-software-projects/looktxt"
    topics = ("cli", "data-conversion", "matlab", "xml", "html", "numerical-data")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: accept the whole POSIX family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "looktxt requires a POSIX host (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)
        # Plain upstream Makefile project: build in the source folder, because
        # `make test` reads ./looktxt and examples/ relative to the project root.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") if compilers else None
        if not cc:
            # R33: a bare "clang" from PATH would silently produce a host binary.
            raise ConanException(
                "looktxt: tools.build:compiler_executables.c must point at the OHOS "
                "SDK clang; refusing to fall back to a PATH-resolved compiler"
            )
        # R33 (compiler from conf) + -j1 (single TU, deterministic test log)
        # + hermetic NeXus probe (see header).
        self.run('make -j1 CC="{0}" NEXUS_NAPI='.format(cc))

        # Upstream regression suite.  `make test` is the project's own target:
        #   ./looktxt --version
        #   ./looktxt --verbose --test examples/*      (5 bundled data files)
        #   @echo Test OK
        # It must run in the project root (that is where examples/ lives), which
        # is also self.build_folder thanks to layout() above.  A non-zero exit or
        # a missing "Test OK" aborts the build: the hung scanner is precisely the
        # defect this recipe patches, so a silent skip would hide a regression.
        # The suite is wrapped in `timeout` so that a regression which restores the
        # hang fails with a clean diagnostic instead of pinning a core until the CI
        # kills the job (124 = timed out, 137 = killed after -k).
        self.run(
            'timeout -k 5 600 make -j1 CC="{0}" NEXUS_NAPI= test '
            '> upstream-tests.log 2>&1; '
            'rc=$?; echo "looktxt-upstream-suite-exit=$rc" >> upstream-tests.log; '
            'cat upstream-tests.log'.format(cc),
            ignore_errors=True,
        )
        log_path = os.path.join(self.build_folder, "upstream-tests.log")
        if not os.path.exists(log_path):
            raise ConanException(
                "looktxt upstream suite: log missing — the test target did not execute"
            )
        with open(log_path, "r", errors="replace") as handle:
            log_text = handle.read()
        if "looktxt-upstream-suite-exit=124" in log_text or \
                "looktxt-upstream-suite-exit=137" in log_text:
            raise ConanException(
                "looktxt upstream suite: hung and was killed after the 600 s timeout — "
                "the EOF patch (char -> int in file_scan()) is not being applied"
            )
        if "looktxt-upstream-suite-exit=0" not in log_text:
            raise ConanException(
                "looktxt upstream suite: `make test` exited non-zero — "
                "see upstream-tests.log"
            )
        if "Test OK" not in log_text:
            raise ConanException(
                "looktxt upstream suite: no upstream 'Test OK' marker — the suite "
                "did not run to completion (a hung scanner means the EOF patch is "
                "not applied)"
            )
        tested = len(set(re.findall(r"examples/([A-Za-z0-9_.\-]+)", log_text)))
        self.output.info(
            "looktxt upstream suite: PASS (make test, {0} example files)".format(tested)
        )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        copy(self, "looktxt", src=self.build_folder, dst=bindir, keep_path=False)
        os.chmod(os.path.join(bindir, "looktxt"), 0o755)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "looktxt"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
