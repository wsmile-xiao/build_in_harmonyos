#!/usr/bin/env python3
"""Conan test_package — librscode 1.3 (real Reed-Solomon encode/decode test).

Compiles test_rscode.c against the packaged libecc and runs it on-device:
  1. initialize_ecc builds galois tables.
  2. encode -> decode round-trip with zero syndrome and byte-exact payload.
  3. Single-byte error injection is detected (nonzero syndrome) and corrected.
  4. Single-erasure correction recovers the payload.
  5. crc_ccitt determinism + galois field identities.

Evidence markers:
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount parsed from the real
  "RESULT: N passed, M failed" line printed by the test binary.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream RSCODE 1.3 ships no
  test suite (audit in MANIFEST.yml). Re-emitted here every run because the
  main recipe build() output may be skipped on conan cache hits.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import copy


class LibrscodeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        if os.path.normpath(self.source_folder) != os.path.normpath(self.build_folder):
            copy(self, "test_rscode.c", self.source_folder, self.build_folder)

    def _resolve_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        conf_cc = compilers.get("c")
        if conf_cc and os.path.isabs(conf_cc):
            if os.path.isfile(conf_cc) and os.access(conf_cc, os.X_OK):
                return conf_cc
            base = os.path.basename(conf_cc)
            found = shutil.which(base) or shutil.which("clang") or shutil.which("cc")
            if found:
                self.output.info(f"conf compiler {conf_cc} not executable, using {found}")
                return found
            return "clang"
        if conf_cc:
            found = shutil.which(conf_cc)
            if found:
                return found
            return conf_cc
        return shutil.which("clang") or "clang"

    def build(self):
        cc = self._resolve_cc()
        dep = self.dependencies["librscode"]
        include_dir = os.path.join(dep.package_folder, "include")
        lib_dir = os.path.join(dep.package_folder, "lib")
        self.run(
            f'"{cc}" -O2 -I"{include_dir}" -L"{lib_dir}" '
            f'"{os.path.join(self.build_folder, "test_rscode.c")}" -o '
            f'"{os.path.join(self.build_folder, "test_rscode")}" -lecc',
            env="conanbuild",
        )

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.build_folder, "test_rscode")
            # Log file captures stdout so the RESULT line can be parsed
            # into machine evidence (numbers come from the binary output).
            logfile = os.path.join(self.build_folder, "test_rscode.log")
            shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
            self.run(f'{shell} -c \'{bin_path} > "{logfile}" 2>&1\'', env="conanrun")
            output = ""
            try:
                with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                    output = f.read()
            except OSError:
                output = ""
            self.output.info("test_rscode log:\n" + "\n".join(output.splitlines()[-20:]))
            m = re.search(r"RESULT: (\d+) passed, (\d+) failed", output)
            if not m:
                raise ConanException("test_rscode produced no RESULT line — harness broken")
            passed = int(m.group(1))
            failed = int(m.group(2))
            discovered = passed + failed
            ok = failed == 0 and discovered > 0
            marker = {
                "executed": True,
                "passed": ok,
                "command": "./test_rscode",
                "discovered": discovered,
                "passedCount": passed,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            if not ok:
                raise ConanException(f"test_rscode failed: {failed}/{discovered} cases failed")

            upstream_marker = {
                "status": "no_tests",
                "framework": "none",
                "command": "upstream provides no check/test target",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "librscode 1.3 (RSCODE) ships no test suite: no test/tests "
                    "directory, no make check/test target, no CMake/CTest, no "
                    "configure/autotools/meson; only example.c demo (nondeterministic "
                    "rand/time, always exit 0). See test_package/MANIFEST.yml audit."
                ),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
