#!/usr/bin/env python3
"""Conan recipe — jellyfish 2.3.1 for OpenHarmony PC (OHOS/aarch64).

Jellyfish is a fast, memory-efficient k-mer counter for DNA/RNA. It is an
Autotools project that produces the `jellyfish` command-line tool plus the
`libjellyfish-2.0` C++ library.

Adaptation notes (HarmonyOS PC, see patches/ for each change):
  * config.guess is taught about `uname -s = HarmonyOS` (E160).
  * configure's `umask 077` temporary-directory creation is relaxed for
    HMDFS (E011/E114): `mktemp -d` under HMDFS inherits a setgid mode that
    makes the directory unwritable for its own owner.
  * configure only keeps `unix2dos` when it supports the `-n <in> <out>`
    interface the upstream tests use (toybox's unix2dos does not).
  * Test cases that need named pipes are gated at runtime: HarmonyOS denies
    `mkfifo(2)` with EPERM, so the generator-command tests (`-g`/`-G`) and
    the FIFO unit cases are skipped. File-input k-mer counting, which is
    the core functionality, is unaffected.
  * The optional htslib SAM/BAM/CRAM reader is disabled for reproducible
    builds; upstream skips tests/sam.sh accordingly (exit 77).

The full upstream test suite runs in build() via `make check`; a non-zero
exit aborts the Conan build and the PASS/FAIL/SKIP totals are reported from
the automake .trs result files.
"""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JellyfishConan(ConanFile):
    name = "jellyfish"
    version = "2.3.1"
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
        get(self, **self.conan_data["sources"], strip_root=True)

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
        self.cpp_info.includedirs = ["include/jellyfish-2.3.1"]
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
