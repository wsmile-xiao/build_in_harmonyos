#!/usr/bin/env python3
"""Conan test_package for libitl-gobject 0.3 — Conan L1 official test.

Builds test.c with CMake (CMakeDeps + CMakeToolchain) and actually runs the
resulting binary through `self.run()` (L0d). The test links the packaged shared
library and exercises the real API: the itl_G2H / itl_H2G Umm al-Qura round
trip, itl_h_date / itl_g_date, the itl_HijriGreg dispatcher, the ItlPrayer
GObject lifecycle, setLocation/setMethod, getPrayerTimes (6 ordered entries),
getNextDayFajr and getNorthQibla — see test.c for the assertions.

Two deliberate OHOS accommodations:

* No compiler wrapper is installed. The ohos-aarch64 profile's [buildenv]
  already prepends the OHOS SDK llvm/lib to LD_LIBRARY_PATH (that is where lld
  finds libxml2.so.16, E120), so the plain clang from
  tools.build:compiler_executables is enough for CMake's try-compile probes.
  The wrapper variant would have to be written and chmod'ed in build() and then
  exec'ed by make in the same second; on HMDFS that exec intermittently fails
  with EACCES ("make[1]: .../clang-wrappers/clang: Permission denied", 127).
* The shell that launches the test binary is probed by execution rather than
  taken from CONFIG_SHELL, which is not guaranteed to point at a runnable bash
  in every worker/desktop layout.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout

_SHELL_CANDIDATES = (
    "/data/service/hnp/bin/bash",
    "/bin/bash",
)


class LibitlGobjectTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        if str(self.settings.os) != "OHOS":
            cmake.configure()
            cmake.build()
            return
        # OHOS: a compiler whose stdout/stderr is a pipe can die with exit
        # status 1 while printing nothing at all — cmake reports
        # "CMakeFiles/....dir/test.c.obj] Error 1" with no diagnostic in
        # between. Binding both streams to a file (the same treatment the
        # recipe's _make() applies to `make`) makes the build deterministic;
        # the captured log is echoed back afterwards so nothing is hidden.
        log_path = os.path.join(self.build_folder, "cmake-ohos.log")
        with open(log_path, "w", encoding="utf-8") as log:
            cmake.configure(stdout=log, stderr=log)
            cmake.build(stdout=log, stderr=log)
        with open(log_path, encoding="utf-8") as log:
            self.output.info(log.read())

    def _working_shell(self):
        """First candidate shell that actually starts, or None.

        Probing by running avoids os.access(X_OK), which is meaningless on
        HMDFS (chmod is coerced, so the bit test never reflects reality).
        """
        candidates = list(_SHELL_CANDIDATES)
        for key in ("CONFIG_SHELL", "SHELL"):
            value = os.environ.get(key)
            if value:
                candidates.append(value)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if not os.path.isfile(candidate):
                continue
            try:
                probe = subprocess.run([candidate, "-c", "exit 0"],
                                       capture_output=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                continue
            if probe.returncode == 0:
                return candidate
        return None

    def test(self):
        # On OHOS the conan-provided shell may be /system/bin/sh (mksh), which
        # refuses to exec foreign ELF binaries; the test binary is run through a
        # real bash when one is available (repo-wide convention).
        shell = self._working_shell()
        if shell:
            self.run(f'"{shell}" -c "./test_libitl_gobject"', env="conanrun")
        else:
            self.run("./test_libitl_gobject", env="conanrun")
