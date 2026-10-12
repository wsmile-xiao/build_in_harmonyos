#!/usr/bin/env python3
"""Conan recipe for Jinx 1.3.10 (embeddable scripting language) on HarmonyOS PC."""
import glob
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Public API surface: Source/Jinx.h plus the headers it pulls in transitively.
PUBLIC_HEADERS = (
    "Jinx.h", "JxBuffer.h", "JxCollection.h", "JxCoroutine.h",
    "JxMemory.h", "JxTypes.h", "JxVariant.h",
)

# Declared upstream unit-test macro counts, taken from the pristine v1.3.10 tarball:
#   grep -cE '^TEST_CASE' Tests/UnitTests/*.cpp                   -> 14
#   grep -cE '^[[:space:]]*SECTION' Tests/UnitTests/*.cpp         -> 326
#   grep -cE '^[[:space:]]*REQUIRE\(' Tests/UnitTests/*.cpp       -> 1044
# The headline case count is the framework's own accounting: Catch2 reports one entry per
# executed REQUIRE, which the device run counts as 1045 assertions in 14 test cases.
DECLARED_TEST_CASES = 14
DECLARED_SECTIONS = 326
DECLARED_ASSERTIONS = 1044


class JinxConan(ConanFile):
    name = "jinx"
    version = "1.3.10"
    description = ("Embeddable scripting language for real-time applications, "
                   "with a C++ API, coroutines, collections and Unicode support")
    license = "MIT"
    homepage = "https://github.com/JamesBoer/Jinx"
    url = "https://github.com/JamesBoer/Jinx"
    topics = ("scripting", "interpreter", "game", "dsl", "coroutine")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The codeload URL ends with the tag name and carries no .tar.gz suffix, so the
        # archive type is given explicitly; otherwise conan probes it as a zip.
        get(self, filename="jinx-1.3.10.tar.gz", **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        if self.settings.os == "OHOS":
            # OHOS keeps pthread symbols in libc; CMake's cross probe would otherwise look
            # for the non-existent -lpthreads compatibility name.
            tc.cache_variables["CMAKE_HAVE_LIBC_PTHREAD"] = True
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.generate()

    def _locate_unit_tests(self):
        hits = []
        for path in glob.glob(os.path.join(self.build_folder, "**", "UnitTests"), recursive=True):
            if "CMakeFiles" in path or os.path.splitext(path)[1]:
                continue
            if os.path.isfile(path) and os.access(path, os.X_OK):
                hits.append(path)
        if not hits:
            raise ConanException(
                "upstream UnitTests executable was not produced by the build; the test "
                "suite would silently be skipped"
            )
        return sorted(hits, key=len)[0]

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # Building the upstream UnitTests target also builds the Jinx library it links to.
        cmake.build(target="UnitTests")

        if not can_run(self):
            self.output.info("HMOS_UPSTREAM_TEST_RESULT=cross-building, execution on device only")
            return

        exe = self._locate_unit_tests()
        log = os.path.join(self.build_folder, "hmos_unit_tests.log")
        self.run('"%s" > "%s" 2>&1' % (exe, log), env="conanbuild")
        summary = self._parse_catch2(log)
        if summary["failed"] or summary["cases"] < DECLARED_TEST_CASES \
                or summary["assertions"] < DECLARED_ASSERTIONS:
            raise ConanException(
                "upstream Catch2 suite did not fully run: %s (see %s)" % (
                    json.dumps(summary), log)
            )
        self.output.info("HMOS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "framework": "Catch2 (bundled Tests/UnitTests/catch.hpp)",
            "command": "./UnitTests",
            "declared_TEST_CASE_macros": DECLARED_TEST_CASES,
            "declared_SECTION_blocks": DECLARED_SECTIONS,
            "declared_REQUIRE_macros": DECLARED_ASSERTIONS,
            "test_cases_reported": summary["cases"],
            "assertions_reported": summary["assertions"],
            "assertions_failed": summary["failed"],
            "source": "Tests/UnitTests (16 .cpp: 14 Test*.cpp + Main.cpp + UnitTest.cpp)",
        }))

    @staticmethod
    def _parse_catch2(log):
        # Catch2 prints two different shapes and both must be read:
        #   all green -> "All tests passed (1045 assertions in 14 test cases)"
        #   otherwise -> a summary table, e.g.
        #       test cases:  14 |  13 passed | 1 failed
        #       assertions: 3142 | 3141 passed | 1 failed
        with open(log, encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        out = {"cases": 0, "assertions": 0, "failed": 0}
        m = re.search(r"All tests passed \((\d+) assertions in (\d+) test cases\)", text)
        if m:
            out["assertions"] = int(m.group(1))
            out["cases"] = int(m.group(2))
            return out
        m = re.search(r"(\d+) assertions? in (\d+) test cases? failed", text)
        if m:
            out["assertions"] = int(m.group(1))
            out["cases"] = int(m.group(2))
            out["failed"] = 1
            return out
        for line in text.splitlines():
            m = re.match(r"^\s*(test cases|assertions):\s*(\d+)\s*(?:\|\s*(.*))?$", line)
            if not m:
                continue
            total = int(m.group(2))
            passed = failed = 0
            for part in (m.group(3) or "").split("|"):
                pm = re.match(r"\s*(\d+)\s+(passed|failed)", part)
                if pm:
                    if pm.group(2) == "passed":
                        passed += int(pm.group(1))
                    else:
                        failed += int(pm.group(1))
            if m.group(1) == "test cases":
                out["cases"] = max(out["cases"], total)
            else:
                out["assertions"] = max(out["assertions"], total)
            out["failed"] += failed
        if not out["cases"] and not out["assertions"]:
            raise ConanException("no Catch2 summary found in " + log)
        return out

    def package(self):
        lib_copied = 0
        for pattern in ("libJinx.a", "libJinx.so*", "Jinx.lib", "libJinx.dylib", "Jinx.dll"):
            for found in glob.glob(os.path.join(self.build_folder, "**", pattern), recursive=True):
                if "CMakeFiles" in found:
                    continue
                copy(self, os.path.basename(found), src=os.path.dirname(found),
                     dst=os.path.join(self.package_folder, "lib"))
                lib_copied += 1
        if not lib_copied:
            raise ConanException("the Jinx library artifact was not produced")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        for header in PUBLIC_HEADERS:
            copy(self, header, src=os.path.join(self.source_folder, "Source"),
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Jinx")
        self.cpp_info.set_property("cmake_target_name", "Jinx::Jinx")
        self.cpp_info.libs = ["Jinx"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cxxstd", "17")
        if self.settings.os in ("Linux", "OHOS", "Android"):
            self.cpp_info.system_libs = ["m", "pthread"]
