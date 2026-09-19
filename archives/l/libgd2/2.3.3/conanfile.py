#!/usr/bin/env python3
"""Conan recipe for libgd2 2.3.3 (GD Graphics Library, core in-memory C API).

Path A first pass: CMake, static by default, zero external dependencies.
All optional codec/font stacks (PNG/JPEG/TIFF/WebP/AVIF/HEIF/XPM/Freetype/
Fontconfig/Raqm/LIQ/Iconv/C++ API) stay OFF, so the package needs no
requires and cannot break on a dependency chain.

Upstream tests are always configured (BUILD_TEST=ON) and executed on any
runnable host via `ctest --output-on-failure` at the end of build(). The
per-test result lines are parsed (not just the exit code) and re-emitted
as HMBS_UPSTREAM_TEST_RESULT machine evidence; the same JSON is persisted
to build_folder/hmbs_upstream.json and packaged under res/ so test_package
can re-emit it on cache hits.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, get

# Audit of the 2.3.3 release archive (see notes.md): 81 unconditional
# TESTS_FILES entries, of which 2 reference missing sources and are
# repaired in source(), leaving 79 runnable ctest cases. Anything far
# below that means the harness silently ran nothing (exit 0 is not proof).
EXPECTED_MIN_CTEST = 10

UPSTREAM_RESULT_FILENAME = "hmbs_upstream.json"


class Libgd2Conan(ConanFile):
    name = "libgd2"
    version = "2.3.3"
    description = "GD Graphics Library: dynamic image creation (core in-memory C API)"
    license = "BSD-like"
    homepage = "https://libgd.github.io/"
    url = "https://github.com/libgd/libgd"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        self._repair_stale_test_refs()
        self._redirect_static_test_target()
        self._trim_unneeded_subdirs()

    def generate(self):
        tc = CMakeToolchain(self)
        # Static by default (libraries colliding with system names and the
        # OHOS sandbox both favor static; shared stays available by option).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF" if self.options.shared else "ON"
        # Upstream tests always on: preflight runs them on-device, CI only
        # compiles them (ctest is gated on can_run in build()).
        tc.variables["BUILD_TEST"] = "ON"
        # First pass: optional image codec/font stacks OFF (no requires).
        for opt in ("ENABLE_AVIF", "ENABLE_CPP", "ENABLE_FONTCONFIG",
                    "ENABLE_FREETYPE", "ENABLE_GD_FORMATS", "ENABLE_HEIF",
                    "ENABLE_ICONV", "ENABLE_JPEG", "ENABLE_LIQ", "ENABLE_PNG",
                    "ENABLE_RAQM", "ENABLE_TIFF", "ENABLE_WEBP", "ENABLE_XPM"):
            tc.variables[opt] = "OFF"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            marker = self._run_upstream_ctest()
            self._persist_upstream_marker(marker)
        else:
            self.output.info(
                "libgd2: target tests not runnable from this host, "
                "skipping ctest (binaries still compile)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        res = os.path.join(self.package_folder, "res")
        try:
            os.makedirs(res, exist_ok=True)
        except OSError:
            pass
        cached = os.path.join(self.build_folder, UPSTREAM_RESULT_FILENAME)
        if os.path.isfile(cached):
            shutil.copy2(cached, os.path.join(res, UPSTREAM_RESULT_FILENAME))

    def package_info(self):
        # Upstream static target is gd_static; on Linux it carries
        # OUTPUT_NAME "gd" (libgd.a) but under the OHOS/HarmonyOS toolchain
        # the `if (UNIX)` guard does not fire, so the archive installs as
        # libgd_static.a. Collect the real artifact instead of hardcoding.
        # Same approach as the proven archives/g/gd/2.3.3.2 recipe.
        libs = collect_libs(self)
        self.cpp_info.libs = libs or ["gd"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libgd2")
        self.cpp_info.set_property("cmake_target_name", "libgd2::libgd2")
        self.cpp_info.set_property("pkg_config_name", "gdlib")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # -- upstream test repair (release-archive defects, documented) --------

    @staticmethod
    def _comment_out_line(content, statement):
        pattern = r"^(\s*)" + re.escape(statement) + r"\s*$"
        return re.sub(pattern, lambda m: "%s# disabled by libgd2 recipe: %s"
                      % (m.group(1), statement), content, flags=re.MULTILINE)

    def _read_source(self, *parts):
        path = os.path.join(self.source_folder, *parts)
        with open(path, encoding="utf-8") as handle:
            return path, handle.read()

    def _write_source(self, path, content):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _repair_stale_test_refs(self):
        # The 2.3.3 release archive ships three stale test references:
        # tests/CMakeLists.txt lists the nonexistent tests/gdmatrix
        # directory (breaks configure); tests/gdimagecopyrotated and
        # tests/gif list bug00320.c / bug00415.c which are absent from the
        # archive (break the test build). Only these three list lines are
        # commented out; no upstream test source is touched.
        stale = (("tests/CMakeLists.txt", "gdmatrix"),
                 (os.path.join("tests", "gdimagecopyrotated", "CMakeLists.txt"),
                  "bug00320"),
                 (os.path.join("tests", "gif", "CMakeLists.txt"), "bug00415"))
        for rel, entry in stale:
            parts = rel.split(os.sep) if os.sep in rel else rel.split("/")
            path, content = self._read_source(*parts)
            patched = self._comment_out_line(content, entry)
            if patched == content:
                raise ConanException(
                    "libgd2: stale test ref %r not found in %s "
                    "(upstream drift, re-audit required)" % (entry, rel))
            self._write_source(path, patched)

    def _redirect_static_test_target(self):
        # Static-only builds create the gd_static target while the gdTest
        # helper links the unset shared target name ${GD_LIB}. Redirect the
        # helper variable at the existing gd_static target so CMake keeps a
        # real dependency edge instead of a bare -lgd lookup.
        path, content = self._read_source("CMakeLists.txt")
        marker = 'SET(GD_LIB_STATIC "${GD_LIB}_static")'
        if marker not in content:
            raise ConanException(
                "libgd2: static test target marker not found "
                "(upstream drift, re-audit required)")
        redirect = ("\n\n# Static-only builds do not create the upstream gd "
                    "target: point test helpers at gd_static.\n"
                    "if (NOT BUILD_SHARED_LIBS AND BUILD_STATIC_LIBS)\n"
                    "    SET(GD_LIB ${GD_LIB_STATIC})\n"
                    "endif()")
        if "SET(GD_LIB ${GD_LIB_STATIC})" not in content:
            content = content.replace(marker, marker + redirect, 1)
            self._write_source(path, content)

    def _trim_unneeded_subdirs(self):
        # examples/ are sample programs, not ctest cases, and several need
        # the disabled codec/font stacks; docs/ needs doc tooling. Neither
        # is packaged in this first pass. tests/ is always kept.
        path, content = self._read_source("CMakeLists.txt")
        patched = self._comment_out_line(content, "add_subdirectory(examples)")
        patched = self._comment_out_line(patched, "add_subdirectory(docs)")
        if patched == content:
            raise ConanException(
                "libgd2: examples/docs subdir lines not found "
                "(upstream drift, re-audit required)")
        self._write_source(path, patched)
        # CLI helpers are unverified in this pass: ship the library only.
        src_path, src = self._read_source("src", "CMakeLists.txt")
        src, count = re.subn(r"^(\s*)set\(GD_PROGRAMS\s+gdcmpgif\)\s*$",
                             r"\1set(GD_PROGRAMS)", src, flags=re.MULTILINE)
        if count != 1:
            raise ConanException(
                "libgd2: GD_PROGRAMS line not found "
                "(upstream drift, re-audit required)")
        new_src = self._comment_out_line(
            src, "install(PROGRAMS bdftogd DESTINATION bin)")
        if new_src == src:
            raise ConanException(
                "libgd2: bdftogd install line not found "
                "(upstream drift, re-audit required)")
        self._write_source(src_path, new_src)

    # -- upstream ctest execution + machine evidence -----------------------

    def _ctest_executable(self):
        cmake_bin = os.environ.get("HMBS_CMAKE")
        if cmake_bin and os.path.isfile(cmake_bin):
            sibling = os.path.join(os.path.dirname(cmake_bin), "ctest")
            if os.path.isfile(sibling):
                return sibling
        found = shutil.which("ctest")
        if found:
            return found
        raise ConanException(
            "libgd2: ctest not found (HMBS_CMAKE sibling or PATH)")

    def _run_upstream_ctest(self):
        ctest = self._ctest_executable()
        self.output.info(
            "libgd2: running upstream suite: ctest --output-on-failure")
        try:
            proc = subprocess.run(
                [ctest, "--output-on-failure"],
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1500)
        except OSError as exc:
            raise ConanException("libgd2: ctest execution failed: %s" % exc)
        output = proc.stdout or ""
        tail = output[-4000:]
        if tail:
            self.output.info("libgd2 ctest output tail:\n%s" % tail)
        marker = self._parse_ctest_output(output)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, ensure_ascii=False))
        if marker["failed"] > 0 or proc.returncode != 0:
            raise ConanException(
                "libgd2: upstream ctest failed: passed=%d failed=%d "
                "skipped=%d (ctest exit %d)"
                % (marker["passed"], marker["failed"],
                   marker["skipped"], proc.returncode))
        return marker

    def _parse_ctest_output(self, output):
        passed = failed = skipped = 0
        for line in output.splitlines():
            if not re.search(r"Test\s+#\d+:", line):
                continue
            if "Failed" in line or "Timeout" in line:
                failed += 1
            elif "Skipped" in line:
                skipped += 1
            elif "Passed" in line:
                passed += 1
        discovered = passed + failed + skipped
        summary = re.search(
            r"(\d+)% tests passed,\s*(\d+) tests? failed out of (\d+)",
            output)
        if summary:
            self.output.info(
                "libgd2 ctest summary: %s" % summary.group(0))
            if int(summary.group(3)) != discovered:
                self.output.warning(
                    "libgd2: ctest summary total %s != parsed %d; "
                    "trusting parsed per-test lines"
                    % (summary.group(3), discovered))
        if "No tests were found" in output:
            raise ConanException(
                "libgd2: ctest found no tests (BUILD_TEST wiring broken)")
        if discovered < EXPECTED_MIN_CTEST:
            raise ConanException(
                "libgd2: ctest discovered only %d tests (audit expects ~79); "
                "refusing silent empty pass" % discovered)
        return {"status": "passed" if failed == 0 else "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": passed + failed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped}

    def _persist_upstream_marker(self, marker):
        cached = os.path.join(self.build_folder, UPSTREAM_RESULT_FILENAME)
        with open(cached, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(marker, ensure_ascii=False))
