#!/usr/bin/env python3
"""Conan recipe for chunkio 1.5.2.

chunkio (https://github.com/fluent/chunkio) is the chunk storage library used
by Fluent Bit.  It stores "chunks" either in memory (memfs backend) or as
memory mapped files on disk (fs backend) behind a small C API
(``cio_ctx`` / ``cio_stream`` / ``cio_chunk``).  Pure C, CMake build, zero
external dependencies: ``deps/crc32`` (static helper lib) and
``deps/monkey/include`` (mk_list.h, used by the public ``chunkio.h``) are
bundled inside the source archive and built from it.

Upstream carries no ``install()`` rules at all, so the package ships what the
conan-center-index recipe installs (patches 0001/0002 come from CCI verbatim).

OHOS adaptation (evidence and readings in notes.md):
  * patch 0001 — add the missing install() rules (CCI upstream) and stop
    building the ``cio`` CLI, so the package is a pure library (no bin/,
    no commands.json needed, R38/L0k).
  * patch 0002 — let ``CMAKE_POSITION_INDEPENDENT_CODE`` follow the conan
    ``fPIC`` option instead of being hardwired ON (CCI upstream).  The recipe
    additionally sets ``BUILD_SHARED_LIBS`` so shared builds still force PIC.
  * patch 0003 — ``src/cio_utils.c`` includes <fts.h>, which musl/HarmonyOS
    does not provide; select a POSIX nftw(3) recursive delete instead.
  * patch 0004 — ``src/cio_file_unix.c`` grows files with fallocate(2) and
    posix_fallocate(3); both are denied on this platform with EACCES, so the
    recipe falls back to ftruncate(2) (knowledge entry E523, same errno
    family).
  * patch 0005 — the acutest suite hardcodes /tmp/ as its scratch root while
    /tmp is a read-only erofs mount here, so the scratch tree moves into the
    (writable) build directory.

Tests: upstream ships an acutest suite built when ``CIO_TESTS=On`` —
4 programs registered with ctest (16 cases) plus 2 performance programs whose
``add_test()`` upstream comments out ("for dev purposes", 8 cases).  All 24
acutest cases are executed inside build() and reported through the
``HMBS_UPSTREAM_TEST_RESULT`` marker; counts are parsed from the real output,
never hardcoded.  The programs link ``chunkio-static``, so the suite can only
be built together with the static library.
"""

import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class ChunkioConan(ConanFile):
    name = "chunkio"
    version = "1.5.2"
    description = "Simple library to manage chunks of data in memory and file system"
    license = "Apache-2.0"
    homepage = "https://github.com/fluent/chunkio"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("chunk", "io", "memory", "file", "fluent-bit")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_filesystem": [True, False],
        "tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_filesystem": True,
        "tests": True,
    }

    # acutest programs shipped by upstream (tests/CMakeLists.txt); the first
    # four are registered with ctest, the last two are built but their
    # add_test() line is commented out upstream.
    _registered_programs = (
        "cio-test-context",
        "cio-test-memfs",
        "cio-test-stream",
        "cio-test-fs",
    )
    _perf_programs = ("cio-fs_perf", "cio-fs_fragmentation")

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Pure C project: no libc++/cppstd in the package id.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CIO_LIB_STATIC"] = not bool(self.options.shared)
        tc.variables["CIO_LIB_SHARED"] = bool(self.options.shared)
        # Upstream hardwires POSITION_INDEPENDENT_CODE ON; patch 0002 makes it
        # conditional on BUILD_SHARED_LIBS so that the conan fPIC option wins.
        # CMakeToolchain already publishes BUILD_SHARED_LIBS from options.shared
        # (SharedLibBock), so shared builds still force PIC for the bundled
        # static crc32 archive.
        tc.variables["CIO_BACKEND_FILESYSTEM"] = bool(self.options.with_filesystem)
        tc.variables["CIO_TESTS"] = self._tests_enabled()
        # CMake 4 dropped compatibility with cmake_minimum_required(3.0).
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self._tests_enabled():
            if cross_building(self):
                self.output.warning(
                    "cross build: acutest suite compiled but not executed"
                )
            else:
                self._run_upstream_tests()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["chunkio-shared"]
        else:
            # cio-crc32 is linked into chunkio-static but installed separately
            # (patch 0001), so both archives are needed by consumers.
            self.cpp_info.libs = ["chunkio-static", "cio-crc32"]
        self.cpp_info.set_property("cmake_file_name", "chunkio")
        self.cpp_info.set_property("cmake_target_name", "chunkio::chunkio")

    # ── helpers ────────────────────────────────────────────────────────
    def _tests_enabled(self):
        """The upstream test programs link ``chunkio-static``, so the suite
        can only be configured together with a static build."""
        if not bool(self.options.tests):
            return False
        if bool(self.options.shared):
            self.output.info(
                "tests option is ON but shared=True; upstream tests link "
                "chunkio-static, so CIO_TESTS stays OFF for this build"
            )
            return False
        return True

    @staticmethod
    def _read(path):
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()

    @staticmethod
    def _listed_cases(output):
        """Number of cases an acutest binary reports for ``--list``."""
        lines = output.splitlines()
        started = False
        count = 0
        for line in lines:
            if not started:
                if "Unit tests:" in line:
                    started = True
                continue
            if line.strip():
                count += 1
        return count

    def _run_upstream_tests(self):
        """Execute the whole upstream acutest suite and emit the
        ``HMBS_UPSTREAM_TEST_RESULT`` marker.

        Discovered/executed/passed/failed counts are parsed from the real
        tool output (``ctest -N``, per-program ``--list``, acutest ``[ OK ]``
        markers and the ``FAILED: N of M`` summary), never hardcoded.
        """
        tests_dir = os.path.join(self.build_folder, "tests")
        commands = []

        # ── discovered: ask the framework itself ───────────────────────
        discovered = 0
        programs = list(self._registered_programs) + list(self._perf_programs)
        for program in programs:
            exe = os.path.join(tests_dir, program)
            if not os.path.isfile(exe):
                continue
            list_log = os.path.join(self.build_folder, "list-%s.log" % program)
            self.run(
                '"%s" --list > "%s" 2>&1' % (exe, list_log),
                cwd=self.build_folder,
                ignore_errors=True,
            )
            cases = self._listed_cases(self._read(list_log))
            if cases:
                discovered += cases
            else:
                self.output.warning(
                    "%s: acutest --list reported no cases" % program
                )

        # ── run: ctest for the 4 registered programs ───────────────────
        ctest_log = os.path.join(self.build_folder, "upstream-ctest.log")
        ctest_cmd = 'ctest --output-on-failure -V > "%s" 2>&1' % ctest_log
        commands.append("ctest --output-on-failure -V")
        self.run(ctest_cmd, cwd=self.build_folder, ignore_errors=True)
        ctest_out = self._read(ctest_log)

        registered = re.search(
            r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", ctest_out
        )
        if registered:
            self.output.info(
                "ctest executables: %s passed, %s failed, %s total"
                % (registered.group(1) + "%", registered.group(2),
                   registered.group(3))
            )
        else:
            self.output.warning("ctest summary line not found in %s" % ctest_log)

        outputs = [ctest_out]

        # ── run: the 2 performance programs upstream does not register ──
        for program in self._perf_programs:
            exe = os.path.join(tests_dir, program)
            if not os.path.isfile(exe):
                continue
            perf_log = os.path.join(self.build_folder, "upstream-%s.log" % program)
            commands.append(program)
            self.run(
                '"%s" > "%s" 2>&1' % (exe, perf_log),
                cwd=self.build_folder,
                ignore_errors=True,
            )
            outputs.append(self._read(perf_log))

        # ── executed/passed/failed from acutest markers ────────────────
        passed = 0
        failed = 0
        for text in outputs:
            passed += len(re.findall(r"\[\s*OK\s*\]", text))
            for match in re.finditer(
                r"FAILED:\s+(\d+)\s+of\s+(\d+)\s+unit tests have failed", text
            ):
                failed += int(match.group(1))
        executed = passed + failed

        status = "passed" if (failed == 0 and executed > 0) else "failed"
        result = {
            "status": status,
            "framework": "acutest (ctest + direct program runs)",
            "command": " && ".join(commands),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "not_run": discovered - executed if discovered > executed else 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        if status != "passed":
            raise ConanException(
                "upstream acutest suite failed: discovered=%d executed=%d "
                "passed=%d failed=%d" % (discovered, executed, passed, failed)
            )
        if discovered and executed != discovered:
            raise ConanException(
                "upstream acutest case count mismatch: discovered=%d "
                "executed=%d (not every discovered case ran)"
                % (discovered, executed)
            )
