#!/usr/bin/env python3
"""Conan recipe — ttmath 0.9.3-src (header-only big-number C++ template library).

TTMath is a header-only C++ template library for big unsigned/signed integers
and big floating point numbers, plus a mathematical expression parser.  It is
written entirely as C++ templates, so there is nothing to compile for the
library itself — consumers just `#include <ttmath/ttmath.h>`.

Upstream official tests
------------------------
The 0.9.3 release tarball (SourceForge `ttmath-0.9.3-src.tar.gz`) ships only
headers + samples; the official test suite lives in the `tests/` directory of
the same 0.9.3 git tag on gitea.ttmath.org.  Those 4 files (main.cpp,
uinttest.cpp, uinttest.h, tests.uint32) are vendored into `upstream_tests/`
here and run unmodified in build() against the freshly unpacked headers.

The harness is data-driven: it reads tests.uint32 and executes
ADD / ADDINT / ADDTWOINTS records across UInt<1..9>.  Each executed check
prints one line "[row] Method<size>: ok" (pass) or an error line (fail).
The harness itself always returns 0 regardless of failures, so this recipe
parses the emitted check lines to count real executed/passed/failed and
emits the HMBS_UPSTREAM_TEST_RESULT machine-evidence marker.

OHOS portability
----------------
On OHOS aarch64 (clang) ttmath auto-detects no x86 macros, so it selects the
portable implementation via TTMATH_PLATFORM32 + TTMATH_NOASM
(ttmathuint_noasm.h).  No source patch is required.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

UPSTREAM_COMMAND = "tests  (upstream ttmath 0.9.3 data-driven ADD/ADDINT/ADDTWOINTS suite)"

# Error phrases that may appear without the "[row]" prefix (e.g. read errors).
_ERR_RE = re.compile(
    r"carry from reading uint|I can't open|syntax error|not supported",
    re.IGNORECASE,
)


class TtmathConan(ConanFile):
    name = "ttmath"
    version = "0.9.3-src"
    description = "Header-only C++ template library for big unsigned/signed integers and big floating point numbers"
    license = "BSD-3-Clause"
    homepage = "https://www.ttmath.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/t/ttmath/0.9.3-src"
    topics = ("bignum", "big-int", "big-float", "math", "header-only", "cpp")
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)
        # Vendor the official 0.9.3 upstream tests into the export sources so
        # build() can compile + run them against the unpacked headers.
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "upstream_tests"),
            dst=os.path.join(self.export_sources_folder, "upstream_tests"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"ttmath not validated for {self.settings.os}"
            )

    def package_id(self):
        # Header-only: no arch/compiler-specific artifacts.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _cxx_compiler(self):
        """Resolve the C++ compiler from the Conan toolchain conf (R33)."""
        conf = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = conf.get("cpp") or conf.get("cxx")
        if cxx:
            return cxx
        c = conf.get("c")
        if c:
            return c if c.endswith("++") else c + "++"
        return shutil.which("clang++") or "clang++"

    def _emit_upstream_marker(self, *, status, executed, passed, failed, skipped, reason):
        result = {
            "status": status,
            "framework": "ttmath-upstream-data",
            "command": UPSTREAM_COMMAND,
            "discovered": executed,          # every check that ran is a discovered case
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": reason,
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}", flush=True)

    def _run_upstream_tests(self):
        """Compile and run the vendored official upstream test suite.

        Returns (passed, failed, output) and raises on a genuine failure so
        `conan create` fails when upstream tests do not pass.
        """
        src_tests = os.path.join(self.export_sources_folder, "upstream_tests")
        build_tests = os.path.join(self.build_folder, "upstream_tests")
        if not os.path.isdir(build_tests):
            shutil.copytree(src_tests, build_tests)

        compiler = self._cxx_compiler()
        binary = os.path.join(build_tests, "ttmath_tests")
        compile_cmd = [
            compiler,
            "-Wall",
            "-O2",
            "-I", self.source_folder,
            os.path.join(build_tests, "main.cpp"),
            os.path.join(build_tests, "uinttest.cpp"),
            "-o", binary,
        ]
        self.output.info("Compiling upstream ttmath tests: %s" % " ".join(compile_cmd))
        compile_proc = subprocess.run(
            compile_cmd, cwd=build_tests, capture_output=True, text=True
        )
        # Surface the compiler output so it shows in the preflight log.
        for stream in (compile_proc.stdout, compile_proc.stderr):
            if stream:
                print(stream, flush=True)
        if compile_proc.returncode != 0:
            raise ConanException(
                "upstream ttmath test build failed (returncode=%s): %s"
                % (compile_proc.returncode, (compile_proc.stderr or "")[-4000:])
            )

        test_cmd = [binary]
        self.output.info("Running upstream ttmath tests: %s" % str(test_cmd))
        # cwd must contain tests.uint32 (harness reads it from cwd).
        run_proc = subprocess.run(
            test_cmd, cwd=build_tests, capture_output=True, text=True
        )
        output = (run_proc.stdout or "") + (run_proc.stderr or "")
        if output.strip():
            print(output, flush=True)

        executed = 0
        passed = 0
        bare_errors = 0
        for line in output.splitlines():
            if not line.strip():
                continue
            if _ERR_RE.search(line):
                # Error phrase that may lack the "[row]" prefix (read/open
                # errors, unsupported method). Still an executed-and-failed
                # check if it carries a row prefix; otherwise a bare error.
                if line.lstrip().startswith("["):
                    executed += 1
                else:
                    bare_errors += 1
                continue
            if line.lstrip().startswith("["):
                # One executed check: "[row] Method<size>: ok" or an
                # "Incorrect ..." / "syntax error" failure line.
                executed += 1
                if line.rstrip().endswith(": ok"):
                    passed += 1

        if executed == 0 and bare_errors == 0:
            # Nothing ran (e.g. input file not found / silent skip): a false
            # pass would be dangerous, so treat as failed.
            self._emit_upstream_marker(
                status="failed",
                executed=0,
                passed=0,
                failed=0,
                skipped=0,
                reason=(
                    "Harness produced no executed checks and no error output. "
                    "Possibly the tests.uint32 fixture was not found (the "
                    "harness prints 'I can't open' to stderr) or the suite "
                    "silently skipped. Refusing to report a pass. Output:\n"
                    + output[-3000:]
                ),
            )
            raise ConanException("upstream ttmath tests produced no executed checks")

        failed = (executed - passed) + bare_errors
        executed_total = executed + bare_errors
        skipped = 0

        if failed == 0 and executed > 0 and passed == executed:
            status = "passed"
        else:
            status = "failed"

        self._emit_upstream_marker(
            status=status,
            executed=executed_total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            reason=(
                "conanfile.py build() compiled and ran the vendored official "
                "ttmath 0.9.3 tests (ADD/ADDINT/ADDTWOINTS across UInt<1..9>) "
                "on the real device; counts parsed from harness output lines."
            ),
        )

        if status == "failed" or executed == 0:
            raise ConanException(
                "upstream ttmath tests failed: passed=%s failed=%s executed=%s"
                % (passed, failed, executed_total)
            )
        return passed, failed, output

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def package(self):
        # Consumer-facing include layout: <ttmath/ttmath.h> and friends.
        copy(self, "*.h", src=os.path.join(self.source_folder, "ttmath"),
             dst=os.path.join(self.package_folder, "include", "ttmath"))
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "ttmath"),
             dst=os.path.join(self.package_folder, "include", "ttmath"))
        copy(self, "*.asm", src=os.path.join(self.source_folder, "ttmath"),
             dst=os.path.join(self.package_folder, "include", "ttmath"))
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "ttmath")
        self.cpp_info.set_property("cmake_target_name", "ttmath::ttmath")
