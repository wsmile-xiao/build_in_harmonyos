#!/usr/bin/env python3
"""Conan recipe — mbpfan 2.4.0 (fan-control daemon, plain Makefile).

The upstream tree is a plain `make` project (no configure).  CC comes from
the OHOS profile (`tools.build:compiler_executables`, R33) and is passed on
the make command line; make runs with -j1 (E074: HMDFS jobserver fifo EPERM).

Upstream tests (tests/minunit.c, `make tests`, 7 cases) run from the source
root and read the fixture configs shipped in the tree.  Patch 0001:
  - bypasses check_requirements() in the test entry: it exits unless the
    process is root with coretemp+applesmc loaded - x86-Mac kernel
    interfaces that cannot exist on HarmonyOS PC (aarch64/HongMeng);
  - skips the 3 hardware-bound cases (test_sensor_paths / test_fan_paths /
    test_get_temp), declared test_skipped per-case in the PR;
  - makes test_config_file read the supplied ./mbpfan.conf instead of
    /etc/mbpfan.conf (unavailable to the unprivileged test run).
Result on device: 4/4 executed cases pass; 3 skipped with technical reasons.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MbpfanConan(ConanFile):
    name = "mbpfan"
    version = "2.4.0"
    description = "mbpfan - fan speed control daemon based on the input/coretemp interfaces"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/dgraziotin/mbpfan"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mbpfan is only supported on Linux/OHOS, not " + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cc(self):
        # R33: the compiler executable comes from the profile, not the shell env
        exe = self.conf.get("tools.build:compiler_executables") or {}
        return exe.get("c", "clang")

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # E074: -j1 (HMDFS jobserver fifo EPERM with parallel make)
        self.run(f'make CC="{cc}" -j1', env="conanbuild", cwd=self.source_folder)
        # Upstream suite: `make tests` runs ./bin/mbpfan-tests from the source
        # root (fixture configs ./mbpfan.conf* are read relative to it).  The
        # binary exits 0 regardless of the verdict, so assert the output.
        self.run(f'make tests CC="{cc}" -j1 > mbpfan-tests.log 2>&1 || true',
                 env="conanbuild", cwd=self.source_folder)
        with open(os.path.join(self.source_folder, "mbpfan-tests.log"), "r",
                  encoding="utf-8", errors="replace") as f:
            log = f.read()
        if "ALL TESTS PASSED" not in log or "Tests run: 4" not in log:
            raise ConanException(
                "upstream test suite did not pass (4/4 expected):\n" + log[-2000:])
        self.output.info("upstream suite: 4/4 executed cases passed "
                         "(3 hardware-bound cases skipped, see patches/0001)")

    def package(self):
        cc = self._cc()
        self.run(f'make install DESTDIR="{self.package_folder}" CC="{cc}"',
                 env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["usr/sbin"]
