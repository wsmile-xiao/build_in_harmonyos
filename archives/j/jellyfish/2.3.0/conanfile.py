#!/usr/bin/env python3
"""Conan recipe - jellyfish 2.3.0 for OpenHarmony PC (OHOS/aarch64).

Jellyfish is a fast, memory-efficient k-mer counter for DNA/RNA. It is an
Autotools project that produces the `jellyfish` command-line tool plus the
`libjellyfish-2.0` C++ library.

Adaptation notes (HarmonyOS PC, see patches/ for each change):
  * config.guess is taught about `uname -s = HarmonyOS` (E160).
  * configure's `umask 077` temporary-directory creation is relaxed for
    HMDFS (E011/E114): a 0700 scratch directory created there is not writable
    by its own owner, so config.status cannot write subs1.awk into it.
  * configure only keeps `unix2dos` when it supports the `-n <in> <out>`
    interface the upstream tests use (toybox's unix2dos does not).
  * Test cases that need named pipes are gated at run time: HarmonyOS denies
    `mkfifo(2)` with EPERM, so the generator-command tests (`-g`/`-G`) and the
    FIFO unit cases are skipped. File-input k-mer counting, which is the core
    functionality, is unaffected.
  * The unit tests hard-code /tmp, which is a read-only mount here (E002);
    they fall back to TMPDIR and then the build directory.
  * The optional htslib SAM/BAM/CRAM reader is disabled for reproducible
    builds; upstream skips tests/sam.sh accordingly (exit 77).

The full upstream test suite runs in build() via `make check`; a non-zero
exit aborts the Conan build and the PASS/FAIL/SKIP totals are reported from
the automake .trs result files.
"""
import os
import time

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JellyfishConan(ConanFile):
    name = "jellyfish"
    version = "2.3.0"
    description = "Fast, memory-efficient k-mer counter (C++ library + CLI)"
    license = "BSD-3-Clause OR GPL-3.0-or-later"
    homepage = "https://github.com/gmarcais/Jellyfish"
    url = "https://github.com/gmarcais/Jellyfish"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # github.com intermittently stalls past Conan's 30s connect timeout from
        # here, and the official dist tarball is the only usable source: the tag
        # archive ships no generated configure/Makefile.in/config.guess, and
        # neither this device nor the CI workers have autoconf to regenerate
        # them. So outlast the stall by retrying the same verified URL rather
        # than pointing at a mirror. A checksum mismatch is never retried.
        sources = self.conan_data["sources"]
        for attempt in range(1, 6):
            try:
                get(self, **sources, strip_root=True)
                return
            except Exception as exc:
                text = str(exc).lower()
                if attempt == 5 or "checksum" in text or "sha256" in text:
                    raise
                self.output.warn("Source download failed (attempt %d/5): %s" % (attempt, exc))
                time.sleep(20)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-htslib")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream test suite: 11 shell test scripts (tests/*.sh), the SWIG
        # binding scripts (skipped when bindings are disabled) and the bundled
        # gtest unit suite. A failing test makes `make check` exit non-zero and
        # aborts the Conan build.
        autotools.make(target="check", args=["-j1"])
        self._report_test_summary()
        self._report_unit_test_totals()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE-*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["jellyfish-2.0"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include/jellyfish-2.3.0"]
        self.cpp_info.set_property("pkg_config_name", "jellyfish-2.0")

    def _report_test_summary(self):
        results = {"PASS": 0, "FAIL": 0, "SKIP": 0, "ERROR": 0, "XFAIL": 0, "XPASS": 0}
        trs_paths = set()
        for base in (self.build_folder, self.source_folder):
            if not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for name in files:
                    if name.endswith(".trs"):
                        trs_paths.add(os.path.realpath(os.path.join(root, name)))
        for path in sorted(trs_paths):
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith(":test-result:"):
                        result = line.split(":", 2)[2].strip()
                        if result in results:
                            results[result] += 1
        total = sum(results.values())
        self.output.info(
            "UPSTREAM 'make check' RESULTS: TOTAL={} PASS={} FAIL={} SKIP={} ERROR={}".format(
                total, results["PASS"], results["FAIL"], results["SKIP"], results["ERROR"]))

    def _report_unit_test_totals(self):
        # automake keeps each test script's stdout in its own .log, so the gtest
        # totals never reach the conan log on their own. Echo them here: they are
        # the declared case count for the upstream test table.
        for root, _dirs, files in os.walk(self.build_folder):
            for name in sorted(files):
                if not name.endswith(".log"):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        hits = [ln.strip() for ln in fh if ln.startswith(
                            ("[==========]", "[  PASSED  ]", "[  FAILED  ]", "[  SKIPPED ]"))
                            or "Named pipes unavailable" in ln]
                except OSError:
                    continue
                if hits:
                    self.output.info("UPSTREAM UNIT TESTS {}: {}".format(
                        name, " | ".join(hits[:8])))
